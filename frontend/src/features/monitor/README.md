# Live Monitor

Owns the Live Monitor surface, the four-camera 2×2 HLS viewer with MJPEG rollback, the explicit
**Tạo vùng** workflow, revisioned multi-zone draft/applied state and normalized
four-point editing. Each display camera reads the persisted mapping selected by
`system_admin`; an unmapped camera remains empty. Local video upload is not part
of the app flow. `HlsVideo` uses native HLS where available and pinned Hls.js
elsewhere, with retry, bounded buffers, visibility pause and cleanup. Mapping is
polled every 15 seconds with jitter and only a changed source reconnects.
RTSP-to-inference remains a separate runtime gate from browser playback.
