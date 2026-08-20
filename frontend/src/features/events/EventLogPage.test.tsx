import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {beforeEach, describe, expect, it, vi} from "vitest";
import {loadReviewedEvents} from "../../api/events";
import type {SafetyEvent} from "../../types";
import {EventLogPage} from "./EventLogPage";

vi.mock("../../api/events", () => ({loadReviewedEvents: vi.fn()}));
vi.mock("./EventDetailDialog", () => ({
  EventDetailDialog: ({eventId}: {eventId: number | null}) => eventId === null ? null : <div>AUDIT EVENT {eventId}</div>,
}));

const acknowledged: SafetyEvent = {
  id: 1,
  timestamp: "2026-08-15T03:05:32Z",
  zone_id: "zone_01",
  camera_id: "uploaded_video",
  event_type: "zone_intrusion",
  severity: "critical",
  status: "acknowledged",
};
const falseAlarm: SafetyEvent = {...acknowledged, id: 2, status: "false_alarm"};

describe("EventLogPage audit filters", () => {
  beforeEach(() => {
    vi.mocked(loadReviewedEvents).mockImplementation(async status => status === "acknowledged" ? [acknowledged] : [falseAlarm]);
  });

  it("opens the decision audit from an acknowledged event", async () => {
    render(<EventLogPage active />);

    fireEvent.click(await screen.findByRole("button", {name: "Xem audit sự kiện #1"}));

    expect(screen.getByText("AUDIT EVENT 1")).toBeInTheDocument();
  });

  it("keeps false alarms in a separate audit filter", async () => {
    render(<EventLogPage active />);

    fireEvent.click(await screen.findByRole("tab", {name: "Báo sai"}));

    await waitFor(() => expect(loadReviewedEvents).toHaveBeenLastCalledWith("false_alarm"));
    expect(await screen.findByText("BÁO SAI")).toBeInTheDocument();
  });
});
