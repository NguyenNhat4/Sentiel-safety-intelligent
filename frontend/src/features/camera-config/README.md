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
