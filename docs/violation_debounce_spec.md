# Violation Pop-up Debounce & Alert Management Specification

## Overview

This specification details the violation tracking, pop-up debounce logic, and multi-violation notification aggregation for the Live Camera Monitoring system.

---

## Technical Objectives

1. **Configurable Debounce Window**:
   - Setting `violation_cooldown_seconds` (default: `20.0` seconds) in `backend/app/core/config.py`.
   - Prevents duplicate review pop-ups for the same tracked person when they temporarily exit and re-enter a restricted zone or momentarily fix PPE within the 20-second debounce window.
   - When 20 seconds elapse after an initial alert, any subsequent violation by the same person re-triggers a new pop-up review (`is_new = True`).

2. **Multi-Violation Aggregation**:
   - If a person triggers multiple violation types simultaneously (e.g. Zone Intrusion + Missing PPE Hat/Vest + Restricted Area), the violations are combined into a single pop-up review notification.
   - The pop-up title dynamically summarizes all active violations (e.g., *"Phát hiện người trong phạm vi hạn chế & Phát hiện xâm nhập vùng nguy hiểm & Phát hiện thiếu PPE"*).

---

## Debounce State Machine Flow

```mermaid
stateDiagram-v2
    [*] --> Normal: Tracked Person enters frame
    Normal --> ViolationDetected: Violation Observed

    state ViolationDetected {
        [*] --> FrameConfirmation
        FrameConfirmation --> AlertClaimed: Reaches confirm frames (4 zone / 6 PPE)
        AlertClaimed --> PopupTriggered: is_new = True (Pop-up Displayed)
    }

    PopupTriggered --> ActiveViolation: Record last_alert_time = T_now

    state ActiveViolation {
        [*] --> InViolation
        InViolation --> InViolation: Violation continues (is_new = False)
        InViolation --> ViolationCleared: Person exits zone / wears PPE
    }

    ViolationCleared --> ReEntry: Person re-enters or violates again

    state ReEntry <<choice>>
    ReEntry --> SuppressedAlert: T_now - T_alert < 20s (is_new = False)
    ReEntry --> NewAlert: T_now - T_alert >= 20s (is_new = True, Pop-up Displayed)

    SuppressedAlert --> ActiveViolation
    NewAlert --> ActiveViolation: Update last_alert_time = T_now
```

---

## Sequence Diagram: Re-entry within vs after Debounce Window

```mermaid
sequenceDiagram
    autonumber
    actor Person as Tracked Person (ID: 4)
    participant Tracker as ViolationTrackingService
    participant Inference as FrameInferenceService
    participant UI as Live Monitor (Frontend)

    Note over Person, UI: Lần 1: Đi vào vùng cấm (T = 0s)
    Person->>Inference: Frame at T = 0s (Zone Intrusion)
    Inference->>Tracker: evaluate(track_id=4, rules=['zone_intrusion'], T=0s)
    Tracker-->>Inference: ActiveViolation(is_new=True) [last_alert_time = 0s]
    Inference-->>UI: review_required=True
    UI->>UI: Kích hoạt Pop-up Cảnh Báo Lần 1

    Note over Person, UI: T = 2s: Rời khỏi vùng cấm
    Person->>Inference: Frame at T = 2s (Normal)
    Inference->>Tracker: evaluate(track_id=4, rules=[], T=2s)
    Tracker-->>Inference: Cleared (reentry_cooldown_until = 4s)

    Note over Person, UI: Lần 2: Tái xâm nhập lúc T = 5s (< 20s Debounce)
    Person->>Inference: Frame at T = 5s (Zone Intrusion)
    Inference->>Tracker: evaluate(track_id=4, rules=['zone_intrusion'], T=5s)
    Tracker-->>Inference: ActiveViolation(is_new=False) [5s - 0s < 20s]
    Inference-->>UI: review_required=False
    Note over UI: Pop-up KHÔNG hiển thị lại (Debounced)

    Note over Person, UI: T = 7s: Rời khỏi vùng cấm
    Person->>Inference: Frame at T = 7s (Normal)
    Inference->>Tracker: evaluate(track_id=4, rules=[], T=7s)

    Note over Person, UI: Lần 3: Tái xâm nhập lúc T = 25s (>= 20s Debounce)
    Person->>Inference: Frame at T = 25s (Zone Intrusion)
    Inference->>Tracker: evaluate(track_id=4, rules=['zone_intrusion'], T=25s)
    Tracker-->>Inference: ActiveViolation(is_new=True) [25s - 0s >= 20s, last_alert_time = 25s]
    Inference-->>UI: review_required=True
    UI->>UI: Kích hoạt Pop-up Cảnh Báo Lần 2 (Sau 20s)
```

---

## Configuration Settings

In `backend/app/core/config.py`:

```python
violation_cooldown_seconds: float = Field(default=20.0, ge=0.0, le=300.0)
```

Can be overridden via environment variables:
`VIOLATION_COOLDOWN_SECONDS=20.0`
