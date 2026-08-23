# Live Monitor

Owns Live Monitor, four fixed camera slots, explicit Run/Replay commands, server
session lifecycle, rolling inference FPS and source-coordinate detection overlays.

Safety Manager opens configuration only by selecting a slot; there is no
camera-configuration sidebar entry. Media is loaded from authenticated backend
asset content, not HLS/MJPEG or arbitrary URLs. WebSocket results must match the
latest server-owned session ID; stale output is discarded immediately.
