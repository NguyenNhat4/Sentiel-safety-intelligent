from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class ActiveViolation:
    occurrence_id: str
    rule_key: str
    is_new: bool


@dataclass
class _Occurrence:
    occurrence_id: str
    active: bool = True
    absent_frames: int = 0
    lost_frames: int = 0
    cooldown_until: float = 0.0


class ViolationTrackingService:
    """Owns session-local violation occurrences independently of transport and CV."""

    def __init__(
        self,
        *,
        lost_grace_frames: int = 3,
        exit_confirm_frames: int = 2,
        cooldown_seconds: float = 2.0,
        session_ttl_seconds: float = 300.0,
    ) -> None:
        self._lost_grace_frames = lost_grace_frames
        self._exit_confirm_frames = exit_confirm_frames
        self._cooldown_seconds = cooldown_seconds
        self._session_ttl_seconds = session_ttl_seconds
        self._occurrences: dict[tuple[str, int, str], _Occurrence] = {}
        self._last_seen: dict[str, float] = {}
        self._last_frame: dict[str, int] = {}

    def accept_frame(self, session_id: str, frame_id: int, *, now: float) -> bool:
        self._expire(now)
        last_frame = self._last_frame.get(session_id, -1)
        if frame_id <= last_frame:
            return False
        self._last_frame[session_id] = frame_id
        self._last_seen[session_id] = now
        return True

    def evaluate(
        self,
        session_id: str,
        observed_rules: dict[int, set[str]],
        present_tracks: set[int],
        *,
        now: float,
    ) -> dict[int, list[ActiveViolation]]:
        self._expire(now)
        self._last_seen[session_id] = now
        output: dict[int, list[ActiveViolation]] = {track_id: [] for track_id in present_tracks}
        observed_keys = {
            (session_id, track_id, rule_key) for track_id, rules in observed_rules.items() for rule_key in rules
        }

        for key in observed_keys:
            _, track_id, rule_key = key
            occurrence = self._occurrences.get(key)
            is_new = occurrence is None or (not occurrence.active and now >= occurrence.cooldown_until)
            if is_new:
                occurrence = _Occurrence(occurrence_id=str(uuid4()))
                self._occurrences[key] = occurrence
            else:
                occurrence.active = True
            occurrence.absent_frames = 0
            occurrence.lost_frames = 0
            output.setdefault(track_id, []).append(ActiveViolation(occurrence.occurrence_id, rule_key, is_new))

        for key, occurrence in list(self._occurrences.items()):
            existing_session, track_id, _ = key
            if existing_session != session_id or key in observed_keys or not occurrence.active:
                continue
            if track_id not in present_tracks:
                occurrence.lost_frames += 1
                if occurrence.lost_frames <= self._lost_grace_frames:
                    continue
                self._clear(occurrence, now)
                continue
            occurrence.lost_frames = 0
            occurrence.absent_frames += 1
            if occurrence.absent_frames >= self._exit_confirm_frames:
                self._clear(occurrence, now)

        for violations in output.values():
            violations.sort(key=lambda item: item.rule_key)
        return output

    def end_session(self, session_id: str) -> None:
        self._occurrences = {key: value for key, value in self._occurrences.items() if key[0] != session_id}
        self._last_seen.pop(session_id, None)
        self._last_frame.pop(session_id, None)

    def _clear(self, occurrence: _Occurrence, now: float) -> None:
        occurrence.active = False
        occurrence.absent_frames = 0
        occurrence.lost_frames = 0
        occurrence.cooldown_until = now + self._cooldown_seconds

    def _expire(self, now: float) -> None:
        expired = [
            session_id
            for session_id, last_seen in self._last_seen.items()
            if now - last_seen >= self._session_ttl_seconds
        ]
        for session_id in expired:
            self.end_session(session_id)
