def test_agent_chat_endpoint(client):
    payload = {
        "message": "What should I do if a worker enters Zone 01 without a helmet?",
        "context": {
            "event_type": "missing_ppe",
            "zone_id": "zone_01",
            "severity": "high",
        },
    }
    response = client.post("/api/v1/agent/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "recommendation" in data
