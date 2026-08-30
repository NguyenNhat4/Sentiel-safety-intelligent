# Live Monitor

Owns Live Monitor, four fixed camera slots, explicit Run/Replay commands, server
session lifecycle, rolling inference FPS and source-coordinate detection overlays.

Safety Manager opens configuration only by selecting a slot; there is no
camera-configuration sidebar entry. Media is loaded from authenticated backend
asset content, not HLS/MJPEG or arbitrary URLs. WebSocket results must match the
latest server-owned session ID; stale output is discarded immediately.

Live Monitor also owns the cross-camera pending-alert coordinator. The backend
persists each new occurrence as an `unacknowledged` safety event before the
WebSocket notification is published. PPE alerts create a dismissible toast and
stay in the shared newest-first inbox; zone alerts use one automatic modal and
a FIFO queue. The toast closes automatically after three seconds. Closing either
surface never deletes the pending event. On desktop, the four-camera grid stays
on the left and the durable pending-alert inbox stays visible on the right.

Every successful event review or status mutation publishes a browser-local and
cross-tab reconciliation signal. Live Monitor reloads its pending inbox from the
backend after that signal, removes events no longer pending, and closes a stale
review surface if another screen already updated the same event.
