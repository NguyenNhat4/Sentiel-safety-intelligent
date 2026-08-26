import json
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from hmac import compare_digest
from typing import Protocol
from uuid import UUID

import cv2
import numpy as np
import torch
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from pydantic import ValidationError

from backend.app.schemas.remote_vision import (
    CONTRACT_VERSION,
    CONTRACT_VERSION_V2,
    RemoteCanonicalPerson,
    RemoteTrackingState,
    RemoteVisionHealth,
    RemoteVisionResponse,
    RemoteVisionV2Health,
    RemoteVisionV2Response,
)
from vision.api import PpeVisionFacade, SafetyVisionResult

MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_TRACKING_STATE_BYTES = 512 * 1024


class VisionAnalyzer(Protocol):
    def preload(self) -> None: ...

    def analyze(
        self,
        frame: np.ndarray,
        monitoring_session_id: str | None,
        now: float,
    ) -> SafetyVisionResult: ...

    def analyze_with_state(
        self,
        frame: np.ndarray,
        state: dict | None,
    ) -> tuple[SafetyVisionResult, dict]: ...


def create_app(
    *,
    analyzer: VisionAnalyzer | None = None,
    model_version: str | None = None,
    worker_api_key: str | None = None,
    compute_device: str | None = None,
) -> FastAPI:
    configured_model_path = os.getenv("PPE_MODEL_PATH", "models/yolo11m_safety.pt")
    configured_device_value = compute_device if compute_device is not None else os.getenv("VISION_DEVICE", "")
    configured_device = configured_device_value.strip() or None
    configured_analyzer = analyzer or PpeVisionFacade(
        configured_model_path,
        device=configured_device,
    )
    configured_model_version = model_version or os.getenv("VISION_MODEL_VERSION", "yolo11m_safety")
    configured_api_key = worker_api_key or os.getenv("VISION_WORKER_API_KEY", "")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        _ensure_compute_device_available(configured_device)
        configured_analyzer.preload()
        app.state.ready = True
        yield
        app.state.ready = False

    app = FastAPI(
        title="P-047 Safety Vision Worker",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.get("/ping", response_model=RemoteVisionHealth)
    def ping() -> RemoteVisionHealth:
        return RemoteVisionHealth(
            status="healthy",
            contract_version=CONTRACT_VERSION,
            model_version=configured_model_version,
        )

    @app.get("/v2/ping", response_model=RemoteVisionV2Health)
    def ping_v2() -> RemoteVisionV2Health:
        return RemoteVisionV2Health(
            status="healthy",
            contract_version=CONTRACT_VERSION_V2,
            model_version=configured_model_version,
        )

    def require_api_key(authorization: str | None = Header(default=None)) -> None:
        if not configured_api_key:
            return
        expected = f"Bearer {configured_api_key}"
        if authorization is None or not compare_digest(authorization, expected):
            raise HTTPException(status_code=401, detail="Unauthorized")

    @app.post(
        "/v1/infer",
        response_model=RemoteVisionResponse,
        dependencies=[Depends(require_api_key)],
    )
    def infer(
        request_id: UUID = Form(...),
        monitoring_session_id: str | None = Form(default=None),
        image: UploadFile = File(...),
    ) -> RemoteVisionResponse:
        raw_image = image.file.read(MAX_IMAGE_BYTES + 1)
        if len(raw_image) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="JPEG image exceeds 8 MiB limit")
        frame = cv2.imdecode(np.frombuffer(raw_image, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise HTTPException(status_code=400, detail="Invalid JPEG image")

        result = configured_analyzer.analyze(frame, monitoring_session_id, time.monotonic())
        return RemoteVisionResponse(
            contract_version=CONTRACT_VERSION,
            request_id=request_id,
            model_version=configured_model_version,
            canonical_people=[
                RemoteCanonicalPerson(
                    bbox=[person[0], person[1], person[2], person[3]],
                    confidence=person[4],
                    track_id=person[5],
                )
                for person in result["canonical_people"]
            ],
            people=result["people"],
            detections=result["detections"],
        )

    @app.post(
        "/v2/infer",
        response_model=RemoteVisionV2Response,
        dependencies=[Depends(require_api_key)],
    )
    def infer_v2(
        request_id: UUID = Form(...),
        monitoring_session_id: UUID = Form(...),
        frame_id: int = Form(..., ge=0),
        state_revision: int = Form(..., ge=0),
        tracking_state: str | None = Form(default=None),
        image: UploadFile = File(...),
    ) -> RemoteVisionV2Response:
        if tracking_state is not None and len(tracking_state.encode("utf-8")) > MAX_TRACKING_STATE_BYTES:
            raise HTTPException(status_code=413, detail="Tracking state exceeds 512 KiB limit")
        if (state_revision == 0) != (tracking_state is None):
            raise HTTPException(status_code=422, detail="Tracking state does not match state_revision")
        parsed_state = None
        if tracking_state is not None:
            try:
                parsed_state = RemoteTrackingState.model_validate(json.loads(tracking_state))
            except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
                raise HTTPException(status_code=422, detail="Invalid tracking state") from exc

        frame = _decode_image(image)
        result, next_state_raw = configured_analyzer.analyze_with_state(
            frame,
            None if parsed_state is None else parsed_state.model_dump(mode="python"),
        )
        try:
            next_state = RemoteTrackingState.model_validate(next_state_raw)
        except ValidationError as exc:
            raise HTTPException(status_code=502, detail="Vision analyzer returned invalid tracking state") from exc
        if len(next_state.model_dump_json().encode("utf-8")) > MAX_TRACKING_STATE_BYTES:
            raise HTTPException(status_code=502, detail="Vision analyzer returned oversized tracking state")
        return RemoteVisionV2Response(
            contract_version=CONTRACT_VERSION_V2,
            request_id=request_id,
            monitoring_session_id=monitoring_session_id,
            frame_id=frame_id,
            base_state_revision=state_revision,
            model_version=configured_model_version,
            canonical_people=[
                RemoteCanonicalPerson(
                    bbox=[person[0], person[1], person[2], person[3]],
                    confidence=person[4],
                    track_id=person[5],
                )
                for person in result["canonical_people"]
            ],
            people=result["people"],
            detections=result["detections"],
            tracking_state=next_state,
        )

    return app


def _decode_image(image: UploadFile) -> np.ndarray:
    raw_image = image.file.read(MAX_IMAGE_BYTES + 1)
    if len(raw_image) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="JPEG image exceeds 8 MiB limit")
    frame = cv2.imdecode(np.frombuffer(raw_image, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid JPEG image")
    return frame


def _ensure_compute_device_available(device: str | None) -> None:
    if device is None or not device.lower().startswith("cuda"):
        return
    if not torch.cuda.is_available():
        raise RuntimeError(f"VISION_DEVICE={device} requires an NVIDIA GPU with a working CUDA runtime")


app = create_app()
