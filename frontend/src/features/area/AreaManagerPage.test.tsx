import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {beforeEach, describe, expect, it, vi} from "vitest";
import {loadAreaEvents, subscribeToSafetyEventUpdates} from "../../api/events";
import {loadStatisticsSummary} from "../../api/statistics";
import {listCameraConfigurations} from "../../api/camera-configurations";
import {listMediaAssets} from "../../api/media-assets";
import type {SafetyEvent} from "../../types";
import {AreaManagerPage} from "./AreaManagerPage";

vi.mock("../../api/events", () => ({
  loadAreaEvents: vi.fn(),
  subscribeToSafetyEventUpdates: vi.fn(() => vi.fn()),
  updateAreaEvent: vi.fn(),
}));
vi.mock("../../api/statistics", () => ({loadStatisticsSummary: vi.fn()}));
vi.mock("../../api/camera-configurations", () => ({listCameraConfigurations: vi.fn()}));
vi.mock("../../api/media-assets", () => ({listMediaAssets: vi.fn()}));
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
    vi.clearAllMocks();
    vi.mocked(subscribeToSafetyEventUpdates).mockImplementation(() => vi.fn());
    vi.mocked(loadStatisticsSummary).mockResolvedValue({
      total_events: 0,
      unacknowledged_events: 0,
      overall_compliance_rate: 100,
      violations_by_type: {},
      violations_by_severity: {},
      zone_stats: [],
    });
    vi.mocked(loadAreaEvents).mockResolvedValue([event]);
    vi.mocked(listCameraConfigurations).mockResolvedValue([
      {camera_id: "cam_1", revision: 1, asset_id: "asset-1", machine_state: "stopped", ppe_requirements: {profile: "hat_vest_v1", hat_required: false, vest_required: false}, zones: [], updated_at: null},
      {camera_id: "cam_2", revision: 1, asset_id: null, machine_state: "stopped", ppe_requirements: {profile: "hat_vest_v1", hat_required: false, vest_required: false}, zones: [], updated_at: null},
      {camera_id: "cam_3", revision: 1, asset_id: null, machine_state: "stopped", ppe_requirements: {profile: "hat_vest_v1", hat_required: false, vest_required: false}, zones: [], updated_at: null},
      {camera_id: "cam_4", revision: 1, asset_id: null, machine_state: "stopped", ppe_requirements: {profile: "hat_vest_v1", hat_required: false, vest_required: false}, zones: [], updated_at: null},
    ]);
    vi.mocked(listMediaAssets).mockResolvedValue([{id: "asset-1", display_name: "Ca sáng", media_type: "video", status: "READY", content_type: "video/mp4", size_bytes: 1, storage_backend: "s3", uploaded_at: "2026-08-23T00:00:00Z", assigned_camera_id: "cam_1"}]);
  });

  it("lets the area manager inspect false-alarm audit without changing official KPIs", async () => {
    render(<AreaManagerPage />);

    expect(await screen.findByText("Ca sáng")).toBeInTheDocument();
    expect(screen.getByText("Camera 2 · Chưa gán media")).toBeInTheDocument();
    expect(screen.getByText("Tuân thủ theo khu vực").closest("article")).toHaveTextContent("Ca sáng");
    expect(screen.getByText("VI PHẠM CHÍNH THỨC").closest("article")).toHaveTextContent("0");
    fireEvent.click(screen.getByRole("button", {name: /#7/}));
    expect(screen.getByText("AREA AUDIT 7")).toBeInTheDocument();
  });

  it("reloads the selected detail when Monitor changes the event", async () => {
    const acknowledged = {...event, status: "acknowledged" as const};
    vi.mocked(loadAreaEvents)
      .mockResolvedValueOnce([event])
      .mockResolvedValueOnce([acknowledged]);
    render(<AreaManagerPage />);
    await waitFor(() => expect(loadAreaEvents).toHaveBeenCalledOnce());

    const listener = vi.mocked(subscribeToSafetyEventUpdates).mock.calls[0][0];
    listener({eventIds: [event.id], cameraIds: [event.camera_id]});

    await waitFor(() => expect(loadAreaEvents).toHaveBeenCalledTimes(2));
  });
});
