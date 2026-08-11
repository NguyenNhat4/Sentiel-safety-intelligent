"""Bounded aggregation of the dedicated operational JSONL stream."""

import json
import math
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from backend.app.core.config import Settings
from backend.app.schemas.operational_metrics import (
    LatencySummary,
    OperationalMetricsSummaryResponse,
    RequestMetricsGroup,
)


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(percentile * len(ordered)) - 1]


class OperationalMetricsService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def summary(self, window_minutes: int) -> OperationalMetricsSummaryResponse:
        now = datetime.now(UTC)
        start = now - timedelta(minutes=window_minutes)
        log_path = Path(self.settings.operational_metrics_log_path)
        paths = [
            log_path.with_name(f"{log_path.name}.{index}")
            for index in range(self.settings.operational_metrics_log_backup_count, 0, -1)
        ]
        paths.append(log_path)
        records_scanned = malformed = scanned_bytes = scanned_lines = 0
        partial_reasons: set[str] = set()
        groups: dict[tuple[str, str, str], list[float]] = defaultdict(list)
        counts: Counter[tuple[str, str, str]] = Counter()
        inference_outcomes: Counter[str] = Counter()
        errors_by_kind: Counter[str] = Counter()

        for path in paths:
            try:
                handle = path.open("rb")
            except FileNotFoundError:
                continue
            except OSError:
                partial_reasons.add("unreadable_log_file")
                continue
            with handle:
                for raw_line in handle:
                    if scanned_lines >= self.settings.operational_metrics_max_scan_lines:
                        partial_reasons.add("scan_line_limit")
                        break
                    if scanned_bytes + len(raw_line) > self.settings.operational_metrics_max_scan_bytes:
                        partial_reasons.add("scan_byte_limit")
                        break
                    scanned_lines += 1
                    scanned_bytes += len(raw_line)
                    if not raw_line.endswith(b"\n"):
                        malformed += 1
                        continue
                    try:
                        event = json.loads(raw_line)
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        malformed += 1
                        continue
                    timestamp = _parse_timestamp(event.get("timestamp")) if isinstance(event, dict) else None
                    if timestamp is None:
                        malformed += 1
                        continue
                    records_scanned += 1
                    if not start <= timestamp <= now:
                        continue
                    event_type = event.get("event_type")
                    if event_type == "http_request_completed":
                        method, route, status_class = event.get("method"), event.get("route"), event.get("status_class")
                        if not all(isinstance(value, str) for value in (method, route, status_class)):
                            malformed += 1
                            continue
                        key = (method, route, status_class)
                        counts[key] += 1
                        if isinstance(event.get("duration_ms"), (int, float)):
                            groups[key].append(float(event["duration_ms"]))
                    if event_type in {"inference_completed", "inference_failed"}:
                        inference_outcomes[str(event.get("outcome", event_type))] += 1
                    if isinstance(event.get("error_kind"), str):
                        errors_by_kind[event["error_kind"]] += 1
                if partial_reasons:
                    break

        requests = []
        for (method, route, status_class), count in sorted(counts.items()):
            values = groups[(method, route, status_class)]
            requests.append(
                RequestMetricsGroup(
                    method=method,
                    route=route,
                    status_class=status_class,
                    count=count,
                    latency=LatencySummary(
                        count=len(values),
                        min_ms=min(values) if values else None,
                        mean_ms=sum(values) / len(values) if values else None,
                        p50_ms=_percentile(values, 0.5),
                        p95_ms=_percentile(values, 0.95),
                        max_ms=max(values) if values else None,
                    ),
                )
            )
        return OperationalMetricsSummaryResponse(
            generated_at=now,
            window_start=start,
            window_end=now,
            records_scanned=records_scanned,
            skipped_malformed_records=malformed,
            partial=bool(partial_reasons),
            partial_reasons=sorted(partial_reasons),
            requests=requests,
            inference_outcomes=dict(inference_outcomes),
            errors_by_kind=dict(errors_by_kind),
        )
