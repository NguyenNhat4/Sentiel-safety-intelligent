# System Diagrams

## Components

```mermaid
flowchart LR
    Browser[React Frontend] -->|REST and WebSocket| Backend[FastAPI Backend]
    Admin[System Admin] -->|Upload image or video| Backend
    Backend --> Postgres[(PostgreSQL)]
    Volume[(Persistent Media Volume)] --> Backend
    Backend -->|Frame observation| Vision[Local or Remote Safety Vision]
    Vision -->|Person, hat, vest, tracking| Backend
    Backend -->|Reviewed redacted evidence| Storage[(Snapshot Storage)]
```

## Camera Session

```mermaid
flowchart TD
    Slot[cam_1 through cam_4] --> Config[Atomic asset, zone and PPE configuration]
    Config --> Save[Save without inference]
    Save --> Run[Run Simulation or per-camera Replay]
    Run --> Session[Fresh server-owned session]
    Session --> Source[Direct image/video file]
    Source --> Infer[FrameInferenceService]
    Infer --> Rules[Deterministic safety rules]
    Rules --> WS[Session status, detections and rolling FPS]
    Rules --> HITL[Human review]
    HITL --> Events[(Reviewed events)]
    Source --> EOF[Video EOF]
    EOF --> Replay[Replay one camera]
```

The browser never supplies a source URL or filesystem path. Images infer exactly
once without frame debounce. Videos stop at EOF. Streamer, MediaMTX, HLS and RTSP
are not part of this topology.
