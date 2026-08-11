import json
from datetime import UTC, datetime

from backend.app.core.config import Settings
from backend.app.core.operational_metrics import (
    configure_operational_metrics_logger,
    record_operational_event,
)
from backend.app.services.operational_metrics_service import OperationalMetricsService


def test_operational_metrics_writer_emits_allowlisted_jsonl(tmp_path):
    log_path = tmp_path / "operational-metrics.jsonl"
    configure_operational_metrics_logger(log_path, max_bytes=1024, backup_count=1)

    record_operational_event(
        "http_request_completed",
        method="GET",
        route="/api/v1/events/{event_id}",
        status_class="2xx",
        duration_ms=12.5,
        ignored_secret="must-not-appear",
    )

    line = log_path.read_text(encoding="utf-8")
    assert line.endswith("\n")
    event = json.loads(line)
    assert event["event_type"] == "http_request_completed"
    assert event["route"] == "/api/v1/events/{event_id}"
    assert "ignored_secret" not in event


def test_operational_metrics_summary_skips_malformed_records_and_uses_nearest_rank(tmp_path):
    log_path = tmp_path / "operational-metrics.jsonl"
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    records = [
        {
            "timestamp": timestamp,
            "event_type": "http_request_completed",
            "method": "GET",
            "route": "/health",
            "status_class": "2xx",
            "duration_ms": value,
        }
        for value in (10, 20, 30, 40)
    ]
    log_path.write_text("\n".join(json.dumps(record) for record in records) + "\nnot-json\n", encoding="utf-8")
    settings = Settings(operational_metrics_log_path=str(log_path))

    summary = OperationalMetricsService(settings).summary(window_minutes=5)

    assert summary.skipped_malformed_records == 1
    assert summary.requests[0].latency.p50_ms == 20
    assert summary.requests[0].latency.p95_ms == 40


def test_operational_metrics_endpoint_validates_window_and_excludes_itself(client):
    assert client.get("/api/v1/operational-metrics?window_minutes=0").status_code == 422

    response = client.get("/api/v1/operational-metrics?window_minutes=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload["partial"] is False
    assert all(group["route"] != "/api/v1/operational-metrics" for group in payload["requests"])
