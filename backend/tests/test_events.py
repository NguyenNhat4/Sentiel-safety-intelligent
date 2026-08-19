import time
from uuid import uuid4

from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.exc import OperationalError

from backend.app.models.event import EventOccurrence, SafetyEvent
from backend.app.models.user import User, UserRole
from backend.app.services.auth_service import AuthService, hash_password
from backend.app.services.event_service import EventService
from backend.app.services.frame_inference_service import frame_inference_service


def test_create_and_get_event(client):
    payload = {
        "zone_id": "zone_01",
        "camera_id": "cam_01",
        "event_type": "missing_ppe",
        "severity": "high",
        "privacy_blurred": True,
        "details": {"track_id": 1, "missing": ["hat"]},
    }
    response = client.post("/api/v1/events", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["zone_id"] == "zone_01"
    assert data["status"] == "unacknowledged"
    assert data["privacy_blurred"] is False
    event_id = data["id"]

    # Get event
    get_resp = client.get(f"/api/v1/events/{event_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == event_id


def test_update_event_status(client):
    payload = {
        "zone_id": "zone_02",
        "camera_id": "cam_02",
        "event_type": "zone_intrusion",
        "severity": "critical",
    }
    create_resp = client.post("/api/v1/events", json=payload)
    event_id = create_resp.json()["id"]

    patch_resp = client.patch(
        f"/api/v1/events/{event_id}",
        json={"status": "acknowledged", "acknowledged_by": "Safety Officer A"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "acknowledged"
    assert patch_resp.json()["acknowledged_by"] == "Safety Officer A"


def test_create_event_with_completed_review(client):
    response = client.post(
        "/api/v1/events",
        json={
            "zone_id": "zone_01",
            "event_type": "missing_ppe_and_intrusion",
            "status": "false_alarm",
            "acknowledged_by": "Safety Officer",
            "details": {"review_result": "normal"},
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "false_alarm"
    assert body["acknowledged_by"] == "Safety Test"
    assert body["acknowledged_at"] is not None


def test_repeated_occurrence_create_is_idempotent(client):
    occurrence_id = str(uuid4())
    payload = {
        "zone_id": "zone_01",
        "camera_id": "uploaded_video",
        "event_type": "zone_intrusion",
        "status": "acknowledged",
        "monitoring_session_id": str(uuid4()),
        "occurrence_ids": [occurrence_id],
    }

    first = client.post("/api/v1/events", json=payload)
    repeated = client.post("/api/v1/events", json=payload)

    assert first.status_code == 201
    assert repeated.status_code == 201
    assert repeated.json()["id"] == first.json()["id"]
    assert repeated.json()["occurrence_ids"] == [occurrence_id]


def test_occurrence_cannot_be_reused_for_a_conflicting_event(client):
    occurrence_id = str(uuid4())
    session_id = str(uuid4())
    original = {
        "zone_id": "zone_01",
        "event_type": "zone_intrusion",
        "monitoring_session_id": session_id,
        "occurrence_ids": [occurrence_id],
    }
    assert client.post("/api/v1/events", json=original).status_code == 201

    conflict = client.post(
        "/api/v1/events",
        json={**original, "event_type": "missing_ppe", "severity": "critical"},
    )
    assert conflict.status_code == 409


def test_same_track_in_one_session_merges_all_violations_into_one_event(client):
    session_id = str(uuid4())
    first_occurrence = str(uuid4())
    second_occurrence = str(uuid4())
    common = {
        "zone_id": "zone_01",
        "camera_id": "uploaded_video",
        "event_type": "person_safety_violation",
        "status": "acknowledged",
        "monitoring_session_id": session_id,
        "track_id": 7,
    }

    first = client.post(
        "/api/v1/events",
        json={
            **common,
            "occurrence_ids": [first_occurrence],
            "details": {"violations": ["missing_ppe:hat"]},
        },
    )
    second = client.post(
        "/api/v1/events",
        json={
            **common,
            "occurrence_ids": [second_occurrence],
            "details": {"violations": ["missing_ppe:vest", "zone_intrusion:zone_01"]},
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["track_id"] == 7
    assert set(second.json()["occurrence_ids"]) == {first_occurrence, second_occurrence}
    assert second.json()["details"]["violations"] == [
        "missing_ppe:hat",
        "missing_ppe:vest",
        "zone_intrusion:zone_01",
    ]


def test_event_batch_creates_one_event_per_zone_atomically_and_is_idempotent(client):
    session_id = str(uuid4())
    for frame in range(4):
        active = frame_inference_service._violation_tracker.evaluate(
            session_id,
            {1: {"zone_intrusion:left"}, 2: {"zone_intrusion:right"}},
            {1, 2},
            now=time.monotonic() + frame,
        )
    left_id = active[1][0].occurrence_id
    right_id = active[2][0].occurrence_id
    payload = {
        "monitoring_session_id": session_id,
        "camera_id": "uploaded_video",
        "status": "acknowledged",
        "acknowledged_by": "Safety Officer",
        "events": [
            {
                "zone_id": "left",
                "event_type": "zone_intrusion",
                "severity": "critical",
                "occurrence_ids": [left_id],
                "details": {"machine_state": "running"},
            },
            {
                "zone_id": "right",
                "event_type": "zone_intrusion",
                "severity": "critical",
                "occurrence_ids": [right_id],
                "details": {"machine_state": "running"},
            },
        ],
    }

    try:
        first = client.post("/api/v1/event-batches", json=payload)
        frame_inference_service._violation_tracker.end_session(session_id)
        retry = client.post("/api/v1/event-batches", json=payload)
    finally:
        frame_inference_service._violation_tracker.end_session(session_id)

    assert first.status_code == 201
    assert retry.status_code == 201
    assert retry.json()["batch_id"] == first.json()["batch_id"]
    assert [event["zone_id"] for event in first.json()["events"]] == ["left", "right"]
    assert len({event["batch_id"] for event in first.json()["events"]}) == 1


def test_event_batch_rejects_occurrence_assigned_to_the_wrong_zone(client):
    session_id = str(uuid4())
    for frame in range(4):
        active = frame_inference_service._violation_tracker.evaluate(
            session_id,
            {1: {"zone_intrusion:left"}},
            {1},
            now=time.monotonic() + frame,
        )
    occurrence_id = active[1][0].occurrence_id
    try:
        response = client.post(
            "/api/v1/event-batches",
            json={
                "monitoring_session_id": session_id,
                "camera_id": "uploaded_video",
                "status": "false_alarm",
                "events": [
                    {
                        "zone_id": "right",
                        "event_type": "zone_intrusion",
                        "occurrence_ids": [occurrence_id],
                    }
                ],
            },
        )
    finally:
        frame_inference_service._violation_tracker.end_session(session_id)

    assert response.status_code == 409
    assert response.json()["detail"] == "Occurrence does not belong to the requested session and zone"


def test_event_batch_returns_503_when_occurrence_lookup_loses_database_connection(
    client,
    db_session,
    monkeypatch,
):
    original_query = db_session.query
    query_calls = 0

    def disconnected_query(*args, **kwargs):
        nonlocal query_calls
        query_calls += 1
        if query_calls == 1:
            return original_query(*args, **kwargs)
        raise OperationalError("SELECT safety_events", {}, ConnectionError("connection closed"))

    monkeypatch.setattr(db_session, "query", disconnected_query)
    response = client.post(
        "/api/v1/event-batches",
        json={
            "monitoring_session_id": str(uuid4()),
            "camera_id": "uploaded_video",
            "status": "acknowledged",
            "acknowledged_by": "Safety Officer",
            "events": [
                {
                    "zone_id": "zone_2",
                    "event_type": "zone_intrusion",
                    "severity": "critical",
                    "occurrence_ids": [str(uuid4())],
                }
            ],
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Could not query event occurrences from the database"


def test_occurrence_lookup_avoids_distinct_over_postgresql_json_columns(db_session):
    occurrence_id = str(uuid4())
    event = SafetyEvent(
        zone_id="zone_2",
        event_type="zone_intrusion",
        details={"review_result": "actual_violation"},
        occurrences=[EventOccurrence(occurrence_id=occurrence_id)],
    )
    db_session.add(event)
    db_session.commit()

    statements: list[str] = []

    def capture_statement(_connection, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    engine = db_session.get_bind()
    sqlalchemy_event.listen(engine, "before_cursor_execute", capture_statement)
    try:
        assert EventService(db_session).has_persisted_occurrences([occurrence_id]) is True
    finally:
        sqlalchemy_event.remove(engine, "before_cursor_execute", capture_statement)

    assert not any(statement.lstrip().upper().startswith("SELECT DISTINCT") for statement in statements)


def test_area_manager_only_sees_confirmed_events_for_their_assigned_area(client, db_session):
    db_session.add(
        User(
            email="area.zone2@sentinel.local",
            full_name="Area Zone 2",
            role=UserRole.AREA_MANAGER.value,
            password_hash=hash_password("Sentinel123!"),
            managed_area_id="zone_2",
        )
    )
    db_session.commit()
    token, _, _ = AuthService(db_session).login("area.zone2@sentinel.local", "Sentinel123!")

    for zone_id in ("zone_2", "zone_3"):
        response = client.post(
            "/api/v1/events",
            json={
                "zone_id": zone_id,
                "event_type": "zone_intrusion",
                "status": "acknowledged",
            },
        )
        assert response.status_code == 201

    client.headers.update({"Authorization": f"Bearer {token}"})
    events = client.get("/api/v1/events?status=acknowledged")
    summary = client.get("/api/v1/statistics/summary")

    assert [event["zone_id"] for event in events.json()] == ["zone_2"]
    assert summary.json()["total_events"] == 1
    assert [zone["zone_id"] for zone in summary.json()["zone_stats"]] == ["zone_2"]

    event_id = events.json()[0]["id"]
    resolved = client.patch(f"/api/v1/events/{event_id}", json={"status": "resolved"})
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    other_event = db_session.query(SafetyEvent).filter(SafetyEvent.zone_id == "zone_3").first()
    denied = client.patch(f"/api/v1/events/{other_event.id}", json={"status": "resolved"})
    assert denied.status_code == 404
