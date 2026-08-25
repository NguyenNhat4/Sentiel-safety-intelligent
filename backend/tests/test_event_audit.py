from copy import deepcopy
from uuid import uuid4

from backend.app.models.user import UserRole
from backend.app.services.auth_service import AuthService
from backend.app.services.llm_service import SafetyAgentService


def decision_context_payload() -> dict:
    return {
        "rule": {
            "triggered_rule_keys": ["zone_intrusion:zone_01", "missing_ppe:hat"],
            "ppe_profile": "hat_vest_v1",
            "ppe_requirements": {
                "profile": "hat_vest_v1",
                "hat_required": True,
                "vest_required": False,
            },
        },
        "scene": {
            "frame_id": 12,
            "video_timestamp_seconds": 6.0,
            "machine_state": "running",
            "zone_name": "Máy dập A",
            "zone_revision": 3,
            "zone_points": [
                {"x": 0.1, "y": 0.1},
                {"x": 0.9, "y": 0.1},
                {"x": 0.9, "y": 0.9},
                {"x": 0.1, "y": 0.9},
            ],
            "people": [
                {
                    "track_id": 7,
                    "bbox": [40, 10, 80, 100],
                    "confidence": 0.91,
                    "foot_point": [60, 100],
                    "inside_zone": True,
                    "zone_memberships": [{"zone_id": "zone_01", "inside": True}],
                    "ppe": {
                        "hat": {"status": "missing", "confidence": None},
                        "vest": {"status": "present", "confidence": 0.88},
                    },
                    "missing_required_ppe": ["hat"],
                    "active_violations": [],
                }
            ],
            "detections": [],
        },
        "system_decision": {
            "result": "violate",
            "reason_codes": ["zone_intrusion", "missing_required_ppe:hat"],
        },
    }


def authenticated_headers(db_session) -> tuple[dict[str, str], str, str]:
    service = AuthService(db_session)
    user = service.create_user(
        full_name="Nguyễn Anh Tuấn",
        email="audit-officer@example.com",
        password="Sentinel123!",
        role=UserRole.SAFETY_MANAGER,
    )
    user.must_change_password = False
    db_session.commit()
    token, _, _ = service.login(user.email, "Sentinel123!")
    return {"Authorization": f"Bearer {token}"}, user.id, user.full_name


def test_reviewed_event_persists_server_owned_decision_context_and_summary(client, db_session):
    headers, actor_id, actor_name = authenticated_headers(db_session)
    response = client.post(
        "/api/v1/events",
        headers=headers,
        json={
            "zone_id": "zone_01",
            "camera_id": "uploaded_video",
            "event_type": "missing_ppe_and_intrusion",
            "severity": "high",
            "status": "acknowledged",
            "acknowledged_by": "Spoofed client name",
            "decision_context": decision_context_payload(),
        },
    )

    assert response.status_code == 201
    created = response.json()
    assert created["acknowledged_by"] == actor_name
    assert created["decision_context"]["schema_version"] == "decision_context_v1"
    assert created["decision_context"]["rule"]["rule_version"] == "safety_rule_v1"
    assert created["decision_context"]["rule"]["violation_frame_count"] == 7
    assert created["decision_context"]["scene"]["camera_id"] == "uploaded_video"
    assert created["decision_context"]["scene"]["zone_id"] == "zone_01"
    assert created["decision_context"]["system_decision"]["severity"] == "high"
    assert created["decision_context"]["human_review"]["outcome"] == "actual_violation"
    assert created["decision_context"]["human_review"]["actor_user_id"] == actor_id
    assert created["decision_context"]["human_review"]["actor_name"] == actor_name
    assert created["audit_retention_until"] is not None
    assert created["snapshot_retention_until"] is None

    detail_response = client.get(f"/api/v1/events/{created['id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["summary"]["source"] == "deterministic"
    assert "Máy dập A" in detail["summary"]["text"]
    assert "Nguyễn Anh Tuấn" in detail["summary"]["text"]
    assert detail["summary"]["text"] == (
        "Tại Máy dập A, hệ thống phát hiện một người khi máy đang chạy "
        "và đánh dấu là vi phạm do xâm nhập vùng và không đội mũ. "
        "Nguyễn Anh Tuấn xác nhận đây là vi phạm thực tế."
    )
    assert detail["summary"]["context_schema_version"] == "decision_context_v1"


def test_patch_cannot_replace_immutable_decision_context(client):
    original_context = decision_context_payload()
    created = client.post(
        "/api/v1/events",
        json={
            "zone_id": "zone_01",
            "event_type": "zone_intrusion",
            "status": "acknowledged",
            "acknowledged_by": "Safety Officer",
            "decision_context": original_context,
        },
    ).json()
    stored_context = deepcopy(created["decision_context"])

    patched = client.patch(
        f"/api/v1/events/{created['id']}",
        json={
            "status": "false_alarm",
            "acknowledged_by": "Changed display name",
            "decision_context": {"schema_version": "tampered"},
        },
    )

    assert patched.status_code == 422
    unchanged = client.get(f"/api/v1/events/{created['id']}").json()
    assert unchanged["status"] == "acknowledged"
    assert unchanged["acknowledged_by"] == "Safety Test"
    assert unchanged["decision_context"] == stored_context


def test_false_alarm_is_retrievable_without_entering_official_violation_results(client):
    false_alarm = client.post(
        "/api/v1/events",
        json={
            "zone_id": "zone_01",
            "event_type": "zone_intrusion",
            "status": "false_alarm",
            "acknowledged_by": "Safety Officer",
            "decision_context": decision_context_payload(),
        },
    )
    assert false_alarm.status_code == 201

    audited = client.get("/api/v1/events?status=false_alarm")
    official = client.get("/api/v1/events?status=acknowledged")

    assert [event["id"] for event in audited.json()] == [false_alarm.json()["id"]]
    assert official.json() == []
    assert false_alarm.json()["decision_context"]["human_review"]["outcome"] == "false_alarm"

    statistics = client.get("/api/v1/statistics/summary")
    assert statistics.status_code == 200
    assert statistics.json()["total_events"] == 0
    assert statistics.json()["violations_by_type"] == {}
    assert statistics.json()["violations_by_severity"] == {}
    assert all(zone["total_violations"] == 0 for zone in statistics.json()["zone_stats"])


def test_resolved_confirmed_event_remains_in_official_statistics(client):
    created = client.post(
        "/api/v1/events",
        json={
            "zone_id": "zone_01",
            "event_type": "zone_intrusion",
            "status": "acknowledged",
            "decision_context": decision_context_payload(),
        },
    )
    assert created.status_code == 201
    resolved = client.patch(f"/api/v1/events/{created.json()['id']}", json={"status": "resolved"})
    assert resolved.status_code == 200

    statistics = client.get("/api/v1/statistics/summary").json()
    assert statistics["total_events"] == 1
    assert statistics["violations_by_type"] == {"zone_intrusion": 1}


def test_legacy_event_detail_reports_limited_audit_without_fabricating_context(client):
    created = client.post(
        "/api/v1/events",
        json={
            "zone_id": "legacy_zone",
            "event_type": "zone_intrusion",
            "status": "acknowledged",
        },
    ).json()

    detail = client.get(f"/api/v1/events/{created['id']}").json()

    assert detail["decision_context"] is None
    assert detail["summary"]["source"] == "deterministic"
    assert detail["summary"]["context_schema_version"] is None
    assert "không có decision context đầy đủ" in detail["summary"]["text"].lower()


def test_incident_summary_falls_back_when_optional_llm_fails(client):
    created = client.post(
        "/api/v1/events",
        json={
            "zone_id": "zone_01",
            "event_type": "zone_intrusion",
            "status": "acknowledged",
            "acknowledged_by": "Safety Officer",
            "decision_context": decision_context_payload(),
        },
    ).json()

    prompts: list[str] = []

    class FailingLlm:
        @staticmethod
        def invoke(prompt: str):
            prompts.append(prompt)
            raise RuntimeError("provider unavailable")

    service = SafetyAgentService()
    service.llm = FailingLlm()
    summary = service.generate_incident_summary(
        decision_context=created["decision_context"],
        event_type=created["event_type"],
        zone_id=created["zone_id"],
    )

    assert summary.source == "deterministic"
    assert "Máy dập A" in summary.text
    assert "actor_user_id" not in prompts[0]
    assert "Safety Test" not in prompts[0]
    assert "bbox" not in prompts[0]


def test_decision_audit_rejects_a_non_alert_system_result(client):
    context = decision_context_payload()
    context["system_decision"]["result"] = "normal"

    response = client.post(
        "/api/v1/events",
        json={
            "zone_id": "zone_01",
            "event_type": "zone_intrusion",
            "status": "false_alarm",
            "decision_context": context,
        },
    )

    assert response.status_code == 422


def test_occurrence_retry_rejects_changed_decision_evidence(client):
    occurrence_id = str(uuid4())
    original = decision_context_payload()
    payload = {
        "zone_id": "zone_01",
        "event_type": "zone_intrusion",
        "status": "acknowledged",
        "acknowledged_by": "Safety Officer",
        "occurrence_ids": [occurrence_id],
        "decision_context": original,
    }
    created = client.post("/api/v1/events", json=payload)
    identical_retry = client.post("/api/v1/events", json=payload)
    changed = deepcopy(payload)
    changed["decision_context"]["scene"]["zone_name"] = "Một vùng khác"

    retry = client.post("/api/v1/events", json=changed)

    assert created.status_code == 201
    assert identical_retry.status_code == 201
    assert identical_retry.json()["id"] == created.json()["id"]
    assert retry.status_code == 409


def test_later_review_adds_audit_to_legacy_person_event_without_trusting_client_actor(client):
    session_id = str(uuid4())
    first = client.post(
        "/api/v1/events",
        json={
            "zone_id": "zone_01",
            "event_type": "person_safety_violation",
            "status": "acknowledged",
            "monitoring_session_id": session_id,
            "track_id": 9,
            "occurrence_ids": [str(uuid4())],
        },
    )
    assert first.status_code == 201
    assert first.json()["decision_context"] is None

    merged = client.post(
        "/api/v1/events",
        json={
            "zone_id": "zone_01",
            "event_type": "person_safety_violation",
            "status": "acknowledged",
            "acknowledged_by": "Spoofed client name",
            "monitoring_session_id": session_id,
            "track_id": 9,
            "occurrence_ids": [str(uuid4())],
            "decision_context": decision_context_payload(),
        },
    )

    assert merged.status_code == 201
    assert merged.json()["id"] == first.json()["id"]
    assert merged.json()["acknowledged_by"] == "Safety Test"
    assert merged.json()["decision_context"]["human_review"]["actor_name"] == "Safety Test"
