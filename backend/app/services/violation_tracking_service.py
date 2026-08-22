from dataclasses import dataclass
from math import hypot
from uuid import uuid4


@dataclass(frozen=True)
class ActiveViolation:
    occurrence_id: str
    rule_key: str
    is_new: bool


@dataclass
class _Occurrence:
    occurrence_id: str
    active: bool = False
    absent_frames: int = 0
    lost_frames: int = 0
    cooldown_until: float = 0.0
    consecutive_frames: int = 0


class ViolationTrackingService:
    """Owns session-local violation occurrences independently of transport and CV."""

    def __init__(
        self,
        *,
        activation_frames: int = 1,
        activation_frames_by_rule_prefix: dict[str, int] | None = None,
        lost_grace_frames: int = 3,
        exit_confirm_frames: int = 2,
        cooldown_seconds: float = 2.0,
        session_ttl_seconds: float = 300.0,
        track_handoff_max_distance: float = 0.12,
    ) -> None:
        if activation_frames < 1:
            raise ValueError("activation_frames must be at least 1")
        activation_overrides = activation_frames_by_rule_prefix or {}
        if any(not prefix or frames < 1 for prefix, frames in activation_overrides.items()):
            raise ValueError("rule activation prefixes must be non-empty and frame counts must be at least 1")
        self._activation_frames = activation_frames
        self._activation_frames_by_rule_prefix = dict(activation_overrides)
        self._lost_grace_frames = lost_grace_frames
        self._exit_confirm_frames = exit_confirm_frames
        self._cooldown_seconds = cooldown_seconds
        self._session_ttl_seconds = session_ttl_seconds
        self._track_handoff_max_distance = track_handoff_max_distance
        self._occurrences: dict[tuple[str, int, str], _Occurrence] = {}
        self._track_positions: dict[tuple[str, int], tuple[float, float]] = {}
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
        track_positions: dict[int, tuple[float, float]] | None = None,
        now: float,
    ) -> dict[int, list[ActiveViolation]]:
        self._expire(now)
        self._last_seen[session_id] = now
        output: dict[int, list[ActiveViolation]] = {track_id: [] for track_id in present_tracks}
        observed_keys = {
            (session_id, track_id, rule_key) for track_id, rules in observed_rules.items() for rule_key in rules
        }
        positions = track_positions or {}
        self._handoff_nearby_tracks(session_id, observed_keys, present_tracks, positions)

        for key in observed_keys:
            _, track_id, rule_key = key
            occurrence = self._occurrences.get(key)
            if occurrence is None:
                occurrence = _Occurrence(occurrence_id=str(uuid4()))
                self._occurrences[key] = occurrence
            if occurrence.active:
                is_new = False
            elif now < occurrence.cooldown_until:
                occurrence.active = True
                is_new = False
            else:
                if occurrence.cooldown_until > 0:
                    occurrence = _Occurrence(occurrence_id=str(uuid4()))
                    self._occurrences[key] = occurrence
                occurrence.consecutive_frames += 1
                is_new = occurrence.consecutive_frames >= self._activation_frames_for(rule_key)
                if is_new:
                    occurrence.active = True
                else:
                    continue
            occurrence.absent_frames = 0
            occurrence.lost_frames = 0
            output.setdefault(track_id, []).append(ActiveViolation(occurrence.occurrence_id, rule_key, is_new))

        for key, occurrence in list(self._occurrences.items()):
            existing_session, track_id, _ = key
            if existing_session != session_id or key in observed_keys:
                continue
            if not occurrence.active:
                occurrence.consecutive_frames = 0
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
        for track_id, position in positions.items():
            self._track_positions[(session_id, track_id)] = position
        return output

    def end_session(self, session_id: str) -> None:
        self._occurrences = {key: value for key, value in self._occurrences.items() if key[0] != session_id}
        self._track_positions = {key: value for key, value in self._track_positions.items() if key[0] != session_id}
        self._last_seen.pop(session_id, None)
        self._last_frame.pop(session_id, None)

    def occurrence_context(self, occurrence_id: str) -> tuple[str, str] | None:
        for (session_id, _track_id, rule_key), occurrence in self._occurrences.items():
            if occurrence.occurrence_id == occurrence_id:
                return session_id, rule_key
        return None

    def _clear(self, occurrence: _Occurrence, now: float) -> None:
        occurrence.active = False
        occurrence.absent_frames = 0
        occurrence.lost_frames = 0
        occurrence.cooldown_until = now + self._cooldown_seconds
        occurrence.consecutive_frames = 0

    def _activation_frames_for(self, rule_key: str) -> int:
        matches = [
            (len(prefix), frames)
            for prefix, frames in self._activation_frames_by_rule_prefix.items()
            if rule_key.startswith(prefix)
        ]
        return max(matches)[1] if matches else self._activation_frames

    def _handoff_nearby_tracks(
        self,
        session_id: str,
        observed_keys: set[tuple[str, int, str]],
        present_tracks: set[int],
        positions: dict[int, tuple[float, float]],
    ) -> None:
        for new_key in sorted(observed_keys):
            if new_key in self._occurrences:
                continue
            _, new_track_id, rule_key = new_key
            new_position = positions.get(new_track_id)
            if new_position is None:
                continue
            candidates: list[tuple[float, tuple[str, int, str]]] = []
            for old_key, occurrence in self._occurrences.items():
                old_session_id, old_track_id, old_rule_key = old_key
                old_position = self._track_positions.get((session_id, old_track_id))
                if (
                    old_session_id != session_id
                    or old_rule_key != rule_key
                    or old_track_id in present_tracks
                    or not occurrence.active
                    or occurrence.lost_frames >= self._lost_grace_frames
                    or old_position is None
                ):
                    continue
                distance = hypot(new_position[0] - old_position[0], new_position[1] - old_position[1])
                if distance <= self._track_handoff_max_distance:
                    candidates.append((distance, old_key))
            if not candidates:
                continue
            _, old_key = min(candidates)
            self._occurrences[new_key] = self._occurrences.pop(old_key)

    def _expire(self, now: float) -> None:
        expired = [
            session_id
            for session_id, last_seen in self._last_seen.items()
            if now - last_seen >= self._session_ttl_seconds
        ]
        for session_id in expired:
            self.end_session(session_id)
