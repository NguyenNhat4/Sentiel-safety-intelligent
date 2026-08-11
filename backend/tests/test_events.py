from uuid import uuid4


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
