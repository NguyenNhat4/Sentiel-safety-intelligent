"""Portable, JSON-safe continuation state for the pinned ByteTrack runtime."""

from __future__ import annotations

from typing import Any

import numpy as np
from ultralytics.trackers.basetrack import BaseTrack, TrackState
from ultralytics.trackers.byte_tracker import BYTETracker, STrack
from ultralytics.utils import YAML, IterableSimpleNamespace
from ultralytics.utils.checks import check_yaml

TRACKING_STATE_SCHEMA_VERSION = "bytetrack_ppe_state_v1"


def create_bytetrack() -> BYTETracker:
    """Create the repository's pinned ByteTrack configuration."""
    config = IterableSimpleNamespace(**YAML.load(check_yaml("bytetrack.yaml")))
    return BYTETracker(config)


def export_bytetrack_state(tracker: BYTETracker) -> dict[str, Any]:
    """Export only state that can affect a future ByteTrack update."""
    return {
        "frame_id": int(tracker.frame_id),
        "last_track_id": int(BaseTrack._count),
        "tracked": [_export_track(track) for track in tracker.tracked_stracks],
        "lost": [_export_track(track) for track in tracker.lost_stracks if track.state != TrackState.Removed],
    }


def restore_bytetrack_state(state: dict[str, Any]) -> BYTETracker:
    """Restore a fresh ByteTrack instance from validated JSON-compatible data."""
    tracker = create_bytetrack()
    tracker.frame_id = int(state["frame_id"])
    tracker.tracked_stracks = [_restore_track(item, tracker) for item in state["tracked"]]
    tracker.lost_stracks = [_restore_track(item, tracker) for item in state["lost"]]
    tracker.removed_stracks = []
    BaseTrack._count = int(state["last_track_id"])
    return tracker


def _export_track(track: STrack) -> dict[str, Any]:
    return {
        "track_id": int(track.track_id),
        "tlwh": [float(value) for value in track._tlwh],
        "mean": [float(value) for value in track.mean],
        "covariance": [[float(value) for value in row] for row in track.covariance],
        "is_activated": bool(track.is_activated),
        "state": int(track.state),
        "score": float(track.score),
        "start_frame": int(track.start_frame),
        "frame_id": int(track.frame_id),
        "tracklet_len": int(track.tracklet_len),
        "class_id": int(track.cls),
        "detection_index": int(track.idx),
        "angle": None if track.angle is None else float(track.angle),
    }


def _restore_track(state: dict[str, Any], tracker: BYTETracker) -> STrack:
    tlwh = np.asarray(state["tlwh"], dtype=np.float32)
    center_xywh = np.asarray(
        [
            tlwh[0] + tlwh[2] / 2,
            tlwh[1] + tlwh[3] / 2,
            tlwh[2],
            tlwh[3],
            state["detection_index"],
        ],
        dtype=np.float32,
    )
    track = STrack(center_xywh, float(state["score"]), int(state["class_id"]))
    track._tlwh = tlwh
    track.mean = np.asarray(state["mean"], dtype=np.float64)
    track.covariance = np.asarray(state["covariance"], dtype=np.float64)
    track.kalman_filter = tracker.kalman_filter
    track.track_id = int(state["track_id"])
    track.is_activated = bool(state["is_activated"])
    track.state = int(state["state"])
    track.start_frame = int(state["start_frame"])
    track.frame_id = int(state["frame_id"])
    track.tracklet_len = int(state["tracklet_len"])
    track.idx = int(state["detection_index"])
    track.angle = None if state["angle"] is None else float(state["angle"])
    return track
