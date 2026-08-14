import time
from uuid import uuid4

from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Query

from backend.app.services.event_service import EventService
from backend.app.services.frame_inference_service import frame_inference_service


def test_create_and_get_event(client):
    payload = {
        "zone_id": "zone_01",
        "camera_id": "cam_01",
        "event_type": "missing_ppe",
        "severity": "high",
        "privacy_blurred": True,
        "details": {"track_id": 1, "missing": ["helmet"]},
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
    assert body["acknowledged_by"] == "Safety Officer"
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


def test_occurrence_lookup_avoids_postgresql_distinct_over_json(db_session, monkeypatch):
    compiled_statements: list[str] = []
    original_all = Query.all

    def record_postgresql_statement(query):
        compiled_statements.append(str(query.statement.compile(dialect=postgresql.dialect())))
        return original_all(query)

    monkeypatch.setattr(Query, "all", record_postgresql_statement)

    assert EventService(db_session)._events_for_occurrences([str(uuid4())]) == []
    assert len(compiled_statements) == 1
    assert "SELECT DISTINCT" not in compiled_statements[0].upper()


def test_event_batch_creates_one_event_per_zone_atomically_and_is_idempotent(client):
    session_id = str(uuid4())
    active = frame_inference_service._violation_tracker.evaluate(
        session_id,
        {1: {"zone_intrusion:left"}, 2: {"zone_intrusion:right"}},
        {1, 2},
        now=time.monotonic(),
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
    active = frame_inference_service._violation_tracker.evaluate(
        session_id,
        {1: {"zone_intrusion:left"}},
        {1},
        now=time.monotonic(),
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
