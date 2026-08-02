# Frontend Modules

These native ES modules split the baseline monitor by responsibility without adding a build step.

- `config.js`: sampling constants and backend URL selection.
- `dom.js`: cached DOM references only.
- `state.js`: the single mutable monitoring-session state.
- `video-controller.js`: file, preview, playback, capture, and inference scheduling.
- `video-preview.js`: preview-frame selection and paused-frame snapshots.
- `zone-controller.js`: four-point selection, dragging, deletion, and reset.
- `inference-client.js`: WebSocket control/binary protocol and connection fallback.
- `frame-sampler.js`: 0.5-second sampling gate and Canvas-to-JPEG delivery.
- `overlay-renderer.js`: zone, bounding-box, and foot-point Canvas rendering.
- `review-controller.js`: inference presentation, human review, and event persistence.
- `event-log-controller.js`: acknowledged-event loading, navigation, and snapshot cards.
- `ui.js`: shared labels, rules, toast, timer, and formatting helpers.

`app.js` is the composition root. Transport code must not manipulate the DOM, renderers must not call the network, and controllers share mutable session data only through `state.js`.
