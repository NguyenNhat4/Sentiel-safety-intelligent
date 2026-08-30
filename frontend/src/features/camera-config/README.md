# Camera Configuration

Safety Manager internal page for the exact Live Monitor slot selected, previewing
its READY image/video asset and editing revisioned zones plus rules owned by each
`(camera_id, zone_id)`. It has no sidebar entry; save or back returns to Live Monitor.
After an explicit save succeeds, the page refreshes its persisted draft and revision and
confirms success with an on-page `Đã lưu` toast. The user can then return to Live Monitor
without an incorrect unsaved-changes prompt.

The desktop detail surface fits one viewport: the left workspace stacks the camera preview above
a horizontal settings strip (source, combined operation/PPE, and zone), while the camera-scoped violation
control log occupies the right rail. The settings strip scrolls horizontally only when necessary,
and the event list scrolls inside its panel. Narrow screens retain Preview → Settings → Log and
normal page scrolling.

The camera-scoped violation log reads the same persisted `safety_events` source as Live Monitor.
It refreshes immediately when the camera-detection WebSocket announces persisted pending event IDs,
does not poll the events API, and reconnects automatically after socket failure. A successful initial
connection or reconnection performs one reconciliation fetch so events persisted during a connection
gap do not leave stale data on the detail screen.

Successful review/status mutations from Live Monitor, Camera Detail, or another
browser tab publish a shared event-update signal. The camera log reconciles only
when the changed event belongs to its camera, and an open event-detail dialog
reloads when its exact event ID changes. REST reconciliation requests bypass the
browser cache so persisted backend state remains authoritative in both directions.
