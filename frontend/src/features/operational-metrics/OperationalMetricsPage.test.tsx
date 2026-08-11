import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {afterEach, describe, expect, it, vi} from "vitest";
import {OperationalMetricsPage} from "./OperationalMetricsPage";

const metrics = {
  generated_at: "2026-08-11T10:00:00Z",
  window_start: "2026-08-11T09:55:00Z",
  window_end: "2026-08-11T10:00:00Z",
  records_scanned: 3,
  skipped_malformed_records: 0,
  partial: false,
  partial_reasons: [],
  requests: [{
    method: "GET", route: "/health", status_class: "2xx", count: 3,
    latency: {count: 3, min_ms: 2, mean_ms: 4, p50_ms: 4, p95_ms: 6, max_ms: 6}
  }],
  websocket_connections: [{route: "/api/v1/ws/inference", opened: 1, closed: 1, inference_latency: {count: 1, min_ms: 8, mean_ms: 8, p50_ms: 8, p95_ms: 8, max_ms: 8}}],
  inference_latency_samples: [
    {timestamp: "2026-08-11T09:59:00Z", route: "/api/v1/ws/inference", duration_ms: 8, outcome: "normal"},
    {timestamp: "2026-08-11T10:00:00Z", route: "/api/v1/ws/inference", duration_ms: 20, outcome: "violate"}
  ],
  inference_outcomes: {normal: 2},
  errors_by_kind: {}
};

describe("OperationalMetricsPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("renders operational aggregates and refreshes the selected window", async () => {
    const fetchSpy = vi.spyOn(window, "fetch").mockResolvedValue(
      new Response(JSON.stringify(metrics), {status: 200})
    );
    render(<OperationalMetricsPage active />);

    await waitFor(() => expect(screen.getByText("3 requests")).toBeInTheDocument());
    expect(screen.getByText("/health")).toBeInTheDocument();
    expect(screen.getAllByText("/api/v1/ws/inference")).toHaveLength(1);
    expect(screen.getByRole("img", {name: /Biểu đồ inference latency theo frame/})).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", {name: /Làm mới/}));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(2));
  });
});
