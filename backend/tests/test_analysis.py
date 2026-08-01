def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_start_analysis(client):
    payload = {
        "source_type": "demo",
        "source_path": "data/demo/test.mp4",
        "zone_ids": ["zone_01"],
        "enable_privacy_blur": True,
        "conf_threshold": 0.5,
    }
    response = client.post("/api/v1/analysis/start", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["status"] == "running"


def test_stop_analysis(client):
    start_resp = client.post(
        "/api/v1/analysis/start",
        json={"source_type": "demo", "source_path": "data/demo/test.mp4", "zone_ids": ["zone_01"]},
    )
    session_id = start_resp.json()["session_id"]

    stop_resp = client.post(f"/api/v1/analysis/stop/{session_id}")
    assert stop_resp.status_code == 200
    assert stop_resp.json()["status"] == "stopped"
