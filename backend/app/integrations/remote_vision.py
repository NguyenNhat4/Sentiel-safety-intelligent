from functools import cache
from uuid import uuid4

import cv2
import httpx
import numpy as np
from pydantic import ValidationError

from backend.app.schemas.remote_vision import RemoteVisionHealth, RemoteVisionResponse
from vision.api import SafetyVisionResult


class RemoteVisionError(RuntimeError):
    """The remote inference service could not produce a trusted result."""


class RemoteVisionAdapter:
    """Translate the backend vision facade call into the versioned HTTP contract."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float,
        client: httpx.Client | None = None,
    ) -> None:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = client or httpx.Client(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout_seconds,
        )
        self._headers = headers if client is not None else None

    def preload(self) -> None:
        try:
            response = self._client.get("/ping", headers=self._headers)
            response.raise_for_status()
            RemoteVisionHealth.model_validate(response.json())
        except (httpx.HTTPError, ValueError, ValidationError) as exc:
            raise RemoteVisionError("Remote vision health check failed") from exc

    def analyze(
        self,
        frame: np.ndarray,
        monitoring_session_id: str | None,
        now: float,
    ) -> SafetyVisionResult:
        del now
        encoded, buffer = cv2.imencode(".jpg", frame)
        if not encoded:
            raise RemoteVisionError("Could not encode frame as JPEG")

        request_id = uuid4()
        data = {"request_id": str(request_id)}
        if monitoring_session_id is not None:
            data["monitoring_session_id"] = monitoring_session_id

        try:
            response = self._client.post(
                "/v1/infer",
                data=data,
                files={"image": ("frame.jpg", buffer.tobytes(), "image/jpeg")},
                headers=self._headers,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RemoteVisionError("Remote vision request failed") from exc

        try:
            payload = RemoteVisionResponse.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise RemoteVisionError("Remote vision returned an invalid response contract") from exc
        if payload.request_id != request_id:
            raise RemoteVisionError("Remote vision returned a mismatched request_id")

        return {
            "canonical_people": [
                (
                    *person.bbox,
                    person.confidence,
                    person.track_id,
                )
                for person in payload.canonical_people
            ],
            "people": [person.model_dump(mode="python") for person in payload.people],
            "detections": [detection.model_dump(mode="python") for detection in payload.detections],
        }


@cache
def get_remote_vision_adapter(*, base_url: str, api_key: str, timeout_seconds: float) -> RemoteVisionAdapter:
    return RemoteVisionAdapter(
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )
