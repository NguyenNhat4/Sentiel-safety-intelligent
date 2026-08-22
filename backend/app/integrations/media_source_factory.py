from typing import Literal

from backend.app.integrations.hls_frame_source import HlsFrameSource, build_hls_camera_url
from backend.app.integrations.media_frame_source import MediaFrameSource
from backend.app.integrations.rtsp_frame_source import RtspFrameSource, build_rtsp_camera_url


def create_media_frame_source(
    protocol: Literal["hls", "rtsp"], origin: str, camera_id: str, *, max_fps: float = 2.0
) -> MediaFrameSource:
    if protocol == "hls":
        return HlsFrameSource(build_hls_camera_url(origin, camera_id), max_fps=max_fps)
    if protocol == "rtsp":
        return RtspFrameSource(build_rtsp_camera_url(origin, camera_id), max_fps=max_fps)
    raise ValueError(f"Unsupported media protocol: {protocol}")
