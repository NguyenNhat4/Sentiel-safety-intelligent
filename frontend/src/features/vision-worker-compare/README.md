# Vision Worker Compare Lab

Developer-only browser workflow for comparing the standalone Safety Vision worker on CPU and
CUDA. The same local JPEG or sampled video frame is sent through two Vite development proxies;
the page renders the versioned detections and rolling browser-to-worker latency statistics.

The video sampler allows at most one comparison cycle in flight and counts skipped frames instead
of building a stale queue. This module does not apply safety rules, persist events, store API keys,
or participate in the production camera path.
