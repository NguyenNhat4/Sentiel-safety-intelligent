# Safety Alerts

Presents inference rule outcomes, backend-annotated snapshots, timer state, and Human-in-the-Loop review actions. Review displays the persisted snapshot as an image without adding a browser overlay; persistence is delegated through callbacks.

`PendingViolationList` presents the durable cross-camera review inbox and
`PpeAlertToast` provides the non-blocking PPE notification and closes after three
seconds without resolving its durable inbox item. `ReviewModal` is the
single shared HITL surface for alerts opened from a toast, the inbox, or the
automatic zone queue.
