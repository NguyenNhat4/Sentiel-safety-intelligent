"""Backend-owned persistence and ordering for portable Vision tracking state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import TypeVar

from pydantic import ValidationError
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from backend.app.core.config import get_settings
from backend.app.core.database import SessionLocal
from backend.app.core.operational_metrics import record_operational_event
from backend.app.models.vision_tracking_state import VisionTrackingState
from backend.app.schemas.remote_vision import (
    CONTRACT_VERSION_V2,
    TRACKING_STATE_SCHEMA_VERSION,
    RemoteTrackingState,
)

ResultT = TypeVar("ResultT")
RemoteInference = Callable[[int, dict | None], tuple[ResultT, dict]]


class VisionTrackingStateError(RuntimeError):
    pass


class InvalidVisionTrackingStateError(VisionTrackingStateError):
    pass


class StaleVisionFrameError(VisionTrackingStateError):
    pass


class ExpiredVisionTrackingStateError(VisionTrackingStateError):
    pass


class VisionTrackingStateConflictError(VisionTrackingStateError):
    pass


@dataclass(frozen=True)
class _Snapshot:
    revision: int
    last_frame_id: int
    state: dict


class VisionTrackingStateService:
    """Advance one session row without holding a DB transaction during inference."""

    def __init__(
        self,
        *,
        session_factory=SessionLocal,
        ttl_seconds: int | None = None,
        max_state_bytes: int | None = None,
    ) -> None:
        settings = get_settings()
        self._session_factory = session_factory
        self._ttl_seconds = ttl_seconds or settings.vision_tracking_state_ttl_seconds
        self._max_state_bytes = max_state_bytes or settings.vision_tracking_state_max_bytes

    def process_frame(
        self,
        monitoring_session_id: str,
        frame_id: int,
        infer: RemoteInference[ResultT],
    ) -> ResultT:
        for _attempt in range(2):
            snapshot = self._load(monitoring_session_id)
            revision = 0 if snapshot is None else snapshot.revision
            last_frame_id = -1 if snapshot is None else snapshot.last_frame_id
            if frame_id <= last_frame_id:
                raise StaleVisionFrameError("frame_id must increase within a monitoring session")

            result, raw_state = infer(revision, None if snapshot is None else snapshot.state)
            state = self._validate_state(raw_state)
            persist_started = perf_counter()
            if self._compare_and_swap(
                monitoring_session_id=monitoring_session_id,
                expected_revision=revision,
                frame_id=frame_id,
                state=state,
            ):
                record_operational_event(
                    "vision_tracking_state_persisted",
                    route="/v2/infer-state",
                    outcome="created" if revision == 0 else "advanced",
                    duration_ms=round((perf_counter() - persist_started) * 1000, 3),
                    payload_bytes=len(state.model_dump_json().encode("utf-8")),
                )
                return result
        raise VisionTrackingStateConflictError("tracking state changed during both inference attempts")

    def end_session(self, monitoring_session_id: str) -> None:
        with self._session_factory.begin() as db:
            db.execute(
                delete(VisionTrackingState).where(VisionTrackingState.monitoring_session_id == monitoring_session_id)
            )

    def cleanup_expired(self, *, limit: int = 100) -> int:
        if limit < 1:
            raise ValueError("limit must be positive")
        now = datetime.now(UTC)
        with self._session_factory.begin() as db:
            session_ids = list(
                db.scalars(
                    select(VisionTrackingState.monitoring_session_id)
                    .where(VisionTrackingState.expires_at <= now)
                    .order_by(VisionTrackingState.expires_at)
                    .limit(limit)
                )
            )
            if session_ids:
                db.execute(
                    delete(VisionTrackingState).where(VisionTrackingState.monitoring_session_id.in_(session_ids))
                )
        return len(session_ids)

    def _load(self, monitoring_session_id: str) -> _Snapshot | None:
        with self._session_factory() as db:
            row = db.get(VisionTrackingState, monitoring_session_id)
            if row is None:
                return None
            if row.contract_version != CONTRACT_VERSION_V2 or row.state_schema_version != TRACKING_STATE_SCHEMA_VERSION:
                raise InvalidVisionTrackingStateError("stored tracking state uses an unsupported version")
            expires_at = row.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at <= datetime.now(UTC):
                db.delete(row)
                db.commit()
                raise ExpiredVisionTrackingStateError("tracking state expired before the next frame")
            state = self._validate_state(row.state_payload)
            return _Snapshot(int(row.revision), int(row.last_frame_id), state.model_dump(mode="python"))

    def _validate_state(self, raw_state: dict) -> RemoteTrackingState:
        try:
            state = RemoteTrackingState.model_validate(raw_state)
        except (TypeError, ValueError, ValidationError) as exc:
            raise InvalidVisionTrackingStateError("tracking state failed schema validation") from exc
        if len(state.model_dump_json().encode("utf-8")) > self._max_state_bytes:
            raise InvalidVisionTrackingStateError("tracking state exceeds the configured size limit")
        return state

    def _compare_and_swap(
        self,
        *,
        monitoring_session_id: str,
        expected_revision: int,
        frame_id: int,
        state: RemoteTrackingState,
    ) -> bool:
        now = datetime.now(UTC)
        expires_at = now + timedelta(seconds=self._ttl_seconds)
        payload = state.model_dump(mode="json")
        if expected_revision == 0:
            with self._session_factory() as db:
                db.add(
                    VisionTrackingState(
                        monitoring_session_id=monitoring_session_id,
                        contract_version=CONTRACT_VERSION_V2,
                        state_schema_version=TRACKING_STATE_SCHEMA_VERSION,
                        revision=1,
                        last_frame_id=frame_id,
                        state_payload=payload,
                        updated_at=now,
                        expires_at=expires_at,
                    )
                )
                try:
                    db.commit()
                except IntegrityError:
                    db.rollback()
                    return False
                return True

        with self._session_factory.begin() as db:
            outcome = db.execute(
                update(VisionTrackingState)
                .where(
                    VisionTrackingState.monitoring_session_id == monitoring_session_id,
                    VisionTrackingState.revision == expected_revision,
                    VisionTrackingState.last_frame_id < frame_id,
                )
                .values(
                    revision=expected_revision + 1,
                    last_frame_id=frame_id,
                    state_payload=payload,
                    state_schema_version=TRACKING_STATE_SCHEMA_VERSION,
                    contract_version=CONTRACT_VERSION_V2,
                    updated_at=now,
                    expires_at=expires_at,
                )
            )
            return outcome.rowcount == 1
