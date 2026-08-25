import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from hmac import compare_digest
from typing import Protocol
from uuid import UUID

import cv2
import numpy as np
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile

from backend.app.schemas.remote_vision import (
    CONTRACT_VERSION,
    RemoteCanonicalPerson,
    RemoteVisionHealth,
    RemoteVisionResponse,
)
from vision.api import PpeVisionFacade, SafetyVisionResult

MAX_IMAGE_BYTES = 8 * 1024 * 1024


class VisionAnalyzer(Protocol):
    def preload(self) -> None: ...

    def analyze(
        self,
        frame: np.ndarray,
        monitoring_session_id: str | None,
        now: float,
    ) -> SafetyVisionResult: ...


def create_app(
    *,
    analyzer: VisionAnalyzer | None = None,
    model_version: str | None = None,
    worker_api_key: str | None = None,
) -> FastAPI:
    configured_model_path = os.getenv("PPE_MODEL_PATH", "models/yolo11n_safety_kd_best.pt")
    configured_analyzer = analyzer or PpeVisionFacade(configured_model_path)
    configured_model_version = model_version or os.getenv("VISION_MODEL_VERSION", "yolo11n_safety_kd")
    configured_api_key = worker_api_key or os.getenv("VISION_WORKER_API_KEY", "")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
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

    return app


app = create_app()
