import base64
import math
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import cv2
import numpy as np
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.database import SessionLocal
from backend.app.core.operational_metrics import record_operational_event
from backend.app.models.camera_configuration import CameraSession
from backend.app.schemas.analysis import FrameInferenceRequest
from backend.app.schemas.camera_configuration import CameraConfigurationResponse
from backend.app.schemas.camera_session import CameraSessionResponse
from backend.app.schemas.ppe_requirement import PpeRequirementResponse
from backend.app.services.camera_configuration_service import CameraConfigurationService
from backend.app.services.camera_detection_hub import camera_detection_hub
from backend.app.services.frame_inference_service import frame_inference_service
from backend.app.services.media_asset_service import MediaAssetService

settings = get_settings()


class CameraSessionStartError(RuntimeError):
    pass


@dataclass(frozen=True)
class SessionContext:
    camera_id: str
    session_id: str
    asset_id: str
    media_type: str
    path: Path
    config_revision: int
    configuration: CameraConfigurationResponse | None = None


@dataclass
class _Worker:
    context: SessionContext
    stop: threading.Event
    thread: threading.Thread


ProcessFrame = Callable[[SessionContext, np.ndarray, int, float, bool], dict]


class CameraSessionRuntime:
    """Runs explicit, finite direct-file inference sessions for fixed cameras."""

    def __init__(
        self,
        *,
        session_factory=SessionLocal,
        process_frame: ProcessFrame | None = None,
        publish: Callable[[dict], None] = camera_detection_hub.publish,
        max_fps: float | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._process_frame = process_frame or self._infer_frame
        self._publish = publish
        self._max_fps = max_fps or settings.media_inference_max_fps
        self._workers: dict[str, _Worker] = {}
        self._current_sessions: dict[str, str] = {}
        self._status_persisted_at: dict[str, float] = {}
        self._lock = threading.RLock()
        self._start_lock = threading.Lock()

    def start(self, db: Session, camera_id: str) -> CameraSessionResponse:
        configuration = CameraConfigurationService(db).get(camera_id)
        if configuration.asset_id is None:
            raise CameraSessionStartError("camera_not_configured")
        asset, path = MediaAssetService(db).get_ready_path(str(configuration.asset_id))
        session_id = str(uuid4())
        context = SessionContext(
            camera_id=camera_id,
            session_id=session_id,
            asset_id=asset.id,
            media_type=asset.media_type,
            path=path,
            config_revision=configuration.revision,
            configuration=configuration,
        )
        with self._start_lock:
            with self._lock:
                previous_session_id = self._current_sessions.get(camera_id)
                self._current_sessions[camera_id] = session_id
            now = datetime.now(UTC)
            old_sessions = list(
                db.scalars(
                    select(CameraSession).where(
                        CameraSession.camera_id == camera_id,
                        CameraSession.status.in_(("STARTING", "RUNNING")),
                    )
                )
            )
            for old in old_sessions:
                old.status = "STOPPED"
                old.completed_at = now
            session = CameraSession(
                id=session_id,
                camera_id=camera_id,
                asset_id=asset.id,
                media_type=asset.media_type,
                status="STARTING",
                config_revision=configuration.revision,
                started_at=now,
            )
            db.add(session)
            try:
                db.commit()
            except IntegrityError as exc:
                db.rollback()
                self._restore_claim(camera_id, session_id, previous_session_id)
                raise CameraSessionStartError("session_already_starting") from exc
            except SQLAlchemyError:
                db.rollback()
                self._restore_claim(camera_id, session_id, previous_session_id)
                raise
            self._replace(context)
        return self._response(session)

    def start_in_memory(
        self,
        *,
        camera_id: str,
        session_id: str,
        asset_id: str,
        media_type: str,
        path: Path,
        config_revision: int,
    ) -> None:
        self._replace(SessionContext(camera_id, session_id, asset_id, media_type, path, config_revision))

    def list(self, db: Session) -> list[CameraSessionResponse]:
        sessions = db.scalars(select(CameraSession).order_by(CameraSession.started_at.desc(), CameraSession.id)).all()
        return [self._response(session) for session in sessions]

    def stop_all(self) -> None:
        with self._lock:
            workers = list(self._workers.values())
        for worker in workers:
            worker.stop.set()
            worker.thread.join(timeout=2.0)
            self._stop_if_active(worker.context)

    @staticmethod
    def mark_interrupted_stopped(db: Session) -> None:
        sessions = db.scalars(select(CameraSession).where(CameraSession.status.in_(("STARTING", "RUNNING")))).all()
        now = datetime.now(UTC)
        for session in sessions:
            session.status = "STOPPED"
            session.completed_at = now
        if sessions:
            db.commit()

    def _replace(self, context: SessionContext) -> None:
        stop = threading.Event()
        thread = threading.Thread(
            target=self._run,
            args=(context, stop),
            name=f"media-inference-{context.camera_id}",
            daemon=True,
        )
        worker = _Worker(context, stop, thread)
        with self._lock:
            old = self._workers.get(context.camera_id)
            self._current_sessions[context.camera_id] = context.session_id
            self._workers[context.camera_id] = worker
        if old is not None:
            old.stop.set()
            old.thread.join(timeout=2.0)
            frame_inference_service.release_vision_session(old.context.session_id)
        self._publish_lifecycle(context, "STARTING", 0.0)
        thread.start()

    def _run(self, context: SessionContext, stop: threading.Event) -> None:
        try:
            if context.media_type == "image":
                frame = cv2.imread(str(context.path), cv2.IMREAD_COLOR)
                if frame is None:
                    self._fail(context, "SOURCE_OPEN_FAILED")
                    return
                self._process_and_publish(context, frame, 1, 0.0, True, deque(), time.monotonic())
                self._complete(context, video_time=0.0)
                return
            self._run_video(context, stop)
        except Exception:
            self._fail(context, "INFERENCE_FAILED")
        finally:
            # Keep lightweight occurrence context through its TTL so a queued
            # human review can still validate after video EOF.
            frame_inference_service.release_vision_session(context.session_id)
            with self._lock:
                worker = self._workers.get(context.camera_id)
                if worker is not None and worker.context.session_id == context.session_id:
                    self._workers.pop(context.camera_id, None)

    def _run_video(self, context: SessionContext, stop: threading.Event) -> None:
        capture = cv2.VideoCapture(str(context.path))
        try:
            if not capture.isOpened():
                self._fail(context, "SOURCE_OPEN_FAILED")
                return
            source_fps = capture.get(cv2.CAP_PROP_FPS)
            if not math.isfinite(source_fps) or source_fps <= 0:
                source_fps = self._max_fps
            frame_index = 0
            frame_id = 0
            read_any_frame = False
            last_video_time = 0.0
            next_sample = 0.0
            started = time.monotonic()
            completions: deque[float] = deque()
            while not stop.is_set():
                read, frame = capture.read()
                if not read:
                    if read_any_frame:
                        self._complete(context, video_time=last_video_time)
                    else:
                        self._fail(context, "SOURCE_READ_FAILED")
                    return
                video_time = frame_index / source_fps
                last_video_time = video_time
                read_any_frame = True
                frame_index += 1
                if video_time + 1e-9 < next_sample:
                    continue
                while next_sample <= video_time + 1e-9:
                    next_sample += 1.0 / self._max_fps
                if time.monotonic() - (started + video_time) > 1.0 / self._max_fps:
                    record_operational_event(
                        "inference_dropped",
                        route="/camera-inference",
                        outcome="stale_frame",
                    )
                    continue
                if stop.wait(max(0.0, started + video_time - time.monotonic())):
                    return
                frame_id += 1
                self._process_and_publish(context, frame, frame_id, video_time, False, completions, started)
        finally:
            capture.release()

    def _process_and_publish(
        self,
        context: SessionContext,
        frame: np.ndarray,
        frame_id: int,
        video_time: float,
        bypass_confirmation: bool,
        completions: deque[float],
        started: float,
    ) -> None:
        inference_started = time.perf_counter()
        result = self._process_frame(context, frame, frame_id, video_time, bypass_confirmation)
        duration_ms = round((time.perf_counter() - inference_started) * 1000, 3)
        completed = time.monotonic()
        completions.append(completed)
        while completions and completed - completions[0] > 5.0:
            completions.popleft()
        fps = len(completions) / max(0.001, min(5.0, completed - started))
        if not self._is_current(context):
            return
        self._set_status(context, "RUNNING", fps)
        payload = {
            **result,
            "camera_id": context.camera_id,
            "session_id": context.session_id,
            "monitoring_session_id": context.session_id,
            "asset_id": context.asset_id,
            "media_type": context.media_type,
            "video_time": round(video_time, 3),
            "session_status": "RUNNING",
            "inference_fps": round(fps, 3),
            "frame_id": frame_id,
            "frame_width": int(frame.shape[1]),
            "frame_height": int(frame.shape[0]),
        }
        self._publish_if_current(context, payload)
        record_operational_event(
            "inference_completed",
            route="/camera-inference",
            outcome=result.get("result", "completed"),
            duration_ms=duration_ms,
        )

    def _infer_frame(
        self,
        context: SessionContext,
        frame: np.ndarray,
        frame_id: int,
        video_time: float,
        bypass_confirmation: bool,
    ) -> dict:
        configuration = context.configuration
        if configuration is None:
            raise RuntimeError("Persisted configuration is required")
        requirements_by_zone = {
            zone.zone_id: PpeRequirementResponse(
                camera_id=context.camera_id,
                zone_id=zone.zone_id,
                is_configured=True,
                updated_at=None,
                **zone.ppe_requirements.model_dump(),
            )
            for zone in configuration.zones
        }
        default_requirement = next(
            iter(requirements_by_zone.values()),
            PpeRequirementResponse(
                camera_id=context.camera_id,
                zone_id="zone_01",
                profile="hat_vest_v1",
                hat_required=False,
                vest_required=False,
                is_configured=False,
                updated_at=None,
            ),
        )
        request = FrameInferenceRequest(
            image_data="",
            camera_id=context.camera_id,
            zones=[
                {
                    "zone_id": zone.zone_id,
                    "display_name": zone.display_name,
                    "points": zone.points,
                    "machine_state": configuration.machine_state,
                    "enabled": zone.enabled,
                    "order": zone.order,
                }
                for zone in configuration.zones
            ],
            zone_revision=configuration.revision,
            monitoring_session_id=UUID(context.session_id),
            frame_id=frame_id,
            machine_state=configuration.machine_state,
        )
        response = frame_inference_service.infer_decoded_frame(
            request,
            frame,
            requirements=default_requirement,
            requirements_by_zone=requirements_by_zone,
            bypass_confirmation=bypass_confirmation,
        )
        payload = response.model_dump(mode="json")
        if response.review_required:
            encoded, buffer = cv2.imencode(".jpg", frame)
            if not encoded:
                raise RuntimeError("Could not encode review snapshot")
            payload["snapshot_data"] = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('ascii')}"
        else:
            payload.pop("snapshot_data", None)
        return {"type": "camera_inference_result", **payload}

    def _complete(self, context: SessionContext, *, video_time: float) -> None:
        if self._is_current(context):
            self._set_status(context, "COMPLETED", None)
            self._publish_lifecycle(context, "COMPLETED", self._stored_fps(context), video_time=video_time)

    def _fail(self, context: SessionContext, error_code: str) -> None:
        if self._is_current(context):
            self._set_status(context, "ERROR", None, error_code=error_code)
            self._publish_lifecycle(context, "ERROR", self._stored_fps(context), error_code=error_code)
            record_operational_event(
                "inference_failed",
                route="/camera-inference",
                outcome="error",
                error_kind=error_code.lower(),
            )

    def _set_status(
        self,
        context: SessionContext,
        status: str,
        fps: float | None,
        *,
        error_code: str | None = None,
    ) -> None:
        with self._lock:
            if self._current_sessions.get(context.camera_id) != context.session_id or self._session_factory is None:
                return
            monotonic_now = time.monotonic()
            last_persisted = self._status_persisted_at.get(context.session_id)
            if status == "RUNNING" and last_persisted is not None and monotonic_now - last_persisted < 5.0:
                return
            with self._session_factory() as db:
                session = db.get(CameraSession, context.session_id)
                if session is None:
                    return
                now = datetime.now(UTC)
                session.status = status
                if fps is not None:
                    session.inference_fps = fps
                if status == "RUNNING" and session.running_at is None:
                    session.running_at = now
                if status in {"COMPLETED", "ERROR", "STOPPED"}:
                    session.completed_at = now
                session.error_code = error_code
                db.commit()
                if status == "RUNNING":
                    self._status_persisted_at[context.session_id] = monotonic_now
                else:
                    self._status_persisted_at.pop(context.session_id, None)

    def _stop_if_active(self, context: SessionContext) -> None:
        if self._session_factory is None:
            return
        with self._session_factory() as db:
            session = db.get(CameraSession, context.session_id)
            if session is None or session.status not in {"STARTING", "RUNNING"}:
                return
            session.status = "STOPPED"
            session.completed_at = datetime.now(UTC)
            db.commit()
        self._publish_lifecycle(context, "STOPPED", self._stored_fps(context))

    def _stored_fps(self, context: SessionContext) -> float:
        if self._session_factory is None:
            return 0.0
        with self._session_factory() as db:
            session = db.get(CameraSession, context.session_id)
            return session.inference_fps if session else 0.0

    def _publish_lifecycle(
        self,
        context: SessionContext,
        status: str,
        fps: float,
        *,
        error_code: str | None = None,
        video_time: float = 0.0,
    ) -> None:
        self._publish_if_current(
            context,
            {
                "type": "camera_session_status",
                "camera_id": context.camera_id,
                "session_id": context.session_id,
                "asset_id": context.asset_id,
                "media_type": context.media_type,
                "video_time": round(video_time, 3),
                "session_status": status,
                "inference_fps": round(fps, 3),
                "error_code": error_code,
            },
        )

    def _is_current(self, context: SessionContext) -> bool:
        with self._lock:
            return self._current_sessions.get(context.camera_id) == context.session_id

    def _publish_if_current(self, context: SessionContext, payload: dict) -> None:
        with self._lock:
            if self._current_sessions.get(context.camera_id) == context.session_id:
                self._publish(payload)

    def _restore_claim(self, camera_id: str, session_id: str, previous_session_id: str | None) -> None:
        with self._lock:
            if self._current_sessions.get(camera_id) != session_id:
                return
            if previous_session_id is None:
                self._current_sessions.pop(camera_id, None)
            else:
                self._current_sessions[camera_id] = previous_session_id

    @staticmethod
    def _response(session: CameraSession) -> CameraSessionResponse:
        return CameraSessionResponse(
            id=session.id,
            camera_id=session.camera_id,
            asset_id=session.asset_id,
            media_type=session.media_type,
            status=session.status,
            config_revision=session.config_revision,
            inference_fps=session.inference_fps,
            started_at=session.started_at,
            running_at=session.running_at,
            completed_at=session.completed_at,
            error_code=session.error_code,
        )


camera_session_runtime = CameraSessionRuntime()
