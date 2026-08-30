# Violation Events

Loads reviewed safety events from the REST API and renders separate confirmed-violation and false-alarm audit views. Event Detail presents the persisted AI observation → deterministic rule → human review chain and a source-labelled natural-language summary. Legacy events are shown as limited audit data rather than having missing facts inferred. This feature does not own inference or review decisions.

An open Event Detail dialog subscribes to the shared event-update signal and
reloads its backend audit when the same event is reviewed or changes status in
another screen or browser tab.
