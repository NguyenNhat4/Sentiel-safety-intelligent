import {fireEvent, render, screen} from "@testing-library/react";
import {beforeEach, describe, expect, it, vi} from "vitest";
import {loadAreaEvents} from "../../api/events";
import {loadStatisticsSummary} from "../../api/statistics";
import type {SafetyEvent} from "../../types";
import {AreaManagerPage} from "./AreaManagerPage";

vi.mock("../../api/events", () => ({loadAreaEvents: vi.fn(), updateAreaEvent: vi.fn()}));
vi.mock("../../api/statistics", () => ({loadStatisticsSummary: vi.fn()}));
vi.mock("../events/EventDetailDialog", () => ({
  EventDetailDialog: ({eventId}: {eventId: number | null}) => eventId === null ? null : <div>AREA AUDIT {eventId}</div>,
}));

const event: SafetyEvent = {
  id: 7,
  timestamp: "2026-08-15T03:05:32Z",
  zone_id: "zone_01",
  camera_id: "uploaded_video",
  event_type: "zone_intrusion",
  severity: "critical",
  status: "false_alarm",
};

describe("AreaManagerPage event audit", () => {
  beforeEach(() => {
    vi.mocked(loadStatisticsSummary).mockResolvedValue({
      total_events: 0,
      unacknowledged_events: 0,
      overall_compliance_rate: 100,
      violations_by_type: {},
      violations_by_severity: {},
      zone_stats: [],
    });
    vi.mocked(loadAreaEvents).mockResolvedValue([event]);
  });

  it("lets the area manager inspect false-alarm audit without changing official KPIs", async () => {
    render(<AreaManagerPage />);

    expect(await screen.findAllByText("Không phải vi phạm")).not.toHaveLength(0);
    expect(screen.getByText("VI PHẠM CHÍNH THỨC").closest("article")).toHaveTextContent("0");
    fireEvent.click(screen.getByRole("button", {name: "Xem audit sự kiện #7"}));
    expect(screen.getByText("AREA AUDIT 7")).toBeInTheDocument();
  });
});
