def test_get_statistics_summary(client):
    response = client.get("/api/v1/statistics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_events" in data
    assert "overall_compliance_rate" in data
    assert "zone_stats" in data
