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
    fireEvent.click(screen.getByRole("button", {name: /Làm mới/}));
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(2));
  });
});
