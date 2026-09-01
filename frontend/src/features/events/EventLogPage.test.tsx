import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {beforeEach, describe, expect, it, vi} from "vitest";
import {loadReviewedEvents, subscribeToSafetyEventUpdates} from "../../api/events";
import type {SafetyEvent} from "../../types";
import {EventLogPage} from "./EventLogPage";

vi.mock("../../api/events", () => ({
  getCachedReviewedEvents: vi.fn(() => undefined),
  loadReviewedEvents: vi.fn(),
  subscribeToSafetyEventUpdates: vi.fn(() => vi.fn()),
}));
vi.mock("./EventDetailDialog", () => ({
  EventDetailDialog: ({eventId}: {eventId: number | null}) => eventId === null ? null : <div>AUDIT EVENT {eventId}</div>,
}));

const acknowledged: SafetyEvent = {
  id: 1,
  timestamp: "2026-08-15T03:05:32Z",
  zone_id: "zone_01",
  camera_id: "uploaded_video",
  camera_name: "Cổng kho phía Đông",
  event_type: "zone_intrusion",
  severity: "critical",
  status: "acknowledged",
};
const falseAlarm: SafetyEvent = {...acknowledged, id: 2, status: "false_alarm"};
const missingHat: SafetyEvent = {
  ...acknowledged,
  id: 3,
  event_type: "person_safety_violation",
  decision_context: {
    schema_version: "decision_context_v1",
    rule: {rule_version: "safety_rule_v1", violation_frame_count: 6, triggered_rule_keys: ["missing_ppe:hat"], ppe_profile: "hat_vest_v1", ppe_requirements: {profile: "hat_vest_v1", hat_required: true, vest_required: false}},
    scene: {camera_id: "cam_1", zone_id: "camera_wide", zone_name: "Camera 1", frame_id: 1, video_timestamp_seconds: 1, machine_state: "running", zone_points: [], people: [], detections: []},
    system_decision: {result: "violate", reason_codes: ["missing_required_ppe:hat"], severity: "high"},
    human_review: {outcome: "actual_violation", actor_name: "Safety Officer", reviewed_at: "2026-08-15T03:05:40Z"},
  },
};

describe("EventLogPage audit filters", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(subscribeToSafetyEventUpdates).mockImplementation(() => vi.fn());
    vi.mocked(loadReviewedEvents).mockImplementation(async status => status === "acknowledged" ? [acknowledged] : [falseAlarm]);
  });

  it("opens the decision audit from an acknowledged event", async () => {
    render(<EventLogPage active />);

    fireEvent.click(await screen.findByRole("button", {name: "Xem audit sự kiện #1"}));

    expect(screen.getByText("Camera: Cổng kho phía Đông")).toBeInTheDocument();
    expect(screen.getByText("Vùng: zone_01")).toBeInTheDocument();
    expect(screen.getByText("AUDIT EVENT 1")).toBeInTheDocument();
  });

  it("keeps false alarms in a separate audit filter", async () => {
    render(<EventLogPage active />);

    fireEvent.click(await screen.findByRole("tab", {name: "Báo sai"}));

    await waitFor(() => expect(loadReviewedEvents).toHaveBeenLastCalledWith("false_alarm", {forceRefresh: false}));
    expect(await screen.findByText("BÁO SAI")).toBeInTheDocument();
  });

  it("names the missing equipment in the audit log card", async () => {
    vi.mocked(loadReviewedEvents).mockResolvedValue([missingHat]);
    render(<EventLogPage active />);

    expect(await screen.findByRole("heading", {name: "Thiếu mũ bảo hộ"})).toBeInTheDocument();
    expect(screen.queryByText("Thiếu PPE")).not.toBeInTheDocument();
  });
  it("reloads the open event list when Monitor confirms a violation", async () => {
    const confirmed = {...acknowledged, id: 8};
    vi.mocked(loadReviewedEvents)
      .mockResolvedValueOnce([acknowledged])
      .mockResolvedValueOnce([acknowledged, confirmed]);
    render(<EventLogPage active />);
    await screen.findByText("EVENT #1");

    const listener = vi.mocked(subscribeToSafetyEventUpdates).mock.calls[0][0];
    listener({eventIds: [8], cameraIds: [confirmed.camera_id]});

    expect(await screen.findByRole("button", {name: /#8/})).toBeInTheDocument();
    expect(loadReviewedEvents).toHaveBeenCalledTimes(2);
  });
});
