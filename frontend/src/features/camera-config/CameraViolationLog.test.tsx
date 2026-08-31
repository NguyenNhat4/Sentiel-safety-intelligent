import {act, fireEvent, render, screen, waitFor} from "@testing-library/react";
import {beforeEach, expect, it, vi} from "vitest";
import {loadCameraEvents, saveReviewedEvent} from "../../api/events";
import type {SafetyEventUpdate} from "../../api/events";
import type {CameraConfiguration, CameraInferenceResult, SafetyEvent} from "../../types";
import {CameraViolationLog} from "./CameraViolationLog";

const detectionClient = vi.hoisted(() => ({
  options: undefined as {onResult: (result: CameraInferenceResult) => void} | undefined,
  close: vi.fn(),
  connect: vi.fn().mockResolvedValue(undefined),
}));
const eventUpdates = vi.hoisted(() => ({
  listener: undefined as ((update: SafetyEventUpdate) => void) | undefined,
}));

vi.mock("../../api/events", () => ({
  loadCameraEvents: vi.fn(),
  saveReviewedEvent: vi.fn(),
  subscribeToSafetyEventUpdates: (listener: (update: SafetyEventUpdate) => void) => {
    eventUpdates.listener = listener;
    return vi.fn();
  },
}));
vi.mock("../../api/auth", () => ({getAccessToken: () => "test-token"}));
vi.mock("../../api/camera-detection-client", () => ({
  CameraDetectionClient: class {
    constructor(options: {onResult: (result: CameraInferenceResult) => void}) {
      detectionClient.options = options;
    }
    connect = detectionClient.connect;
    close = detectionClient.close;
  },
}));
const loadMock = vi.mocked(loadCameraEvents);
const saveMock = vi.mocked(saveReviewedEvent);
const configuration: CameraConfiguration = {
  camera_id: "cam_3",
  revision: 1,
  asset_id: "asset-3",
  machine_state: "running",
  ppe_requirements: {profile: "hat_vest_v1", hat_required: true, vest_required: true},
  zones: [{
    zone_id: "press",
    display_name: "Vùng máy dập",
    enabled: true,
    order: 0,
    points: [{x: 0.1, y: 0.1}, {x: 0.9, y: 0.1}, {x: 0.9, y: 0.9}, {x: 0.1, y: 0.9}],
    ppe_requirements: {profile: "hat_vest_v1", hat_required: true, vest_required: true},
  }],
  updated_at: null,
};

function pendingEvent(id: number, eventType = "zone_intrusion"): SafetyEvent {
  const ruleKey = eventType === "missing_ppe" ? "missing_ppe:hat" : "zone_intrusion:press";
  const zoneId = eventType === "missing_ppe" ? "camera_wide" : "press";
  const inference: CameraInferenceResult = {
    type: "camera_inference_result",
    camera_id: "cam_3",
    session_id: "session-3",
    asset_id: "asset-3",
    media_type: "image",
    video_time: 1.5,
    session_status: "RUNNING",
    inference_fps: 2,
    frame_width: 1280,
    frame_height: 720,
    frame_id: 9,
    result: "violate",
    review_required: true,
    monitoring_session_id: "session-3",
    people: [{
      track_id: 7,
      bbox: [10, 20, 100, 200],
      confidence: 0.91,
      inside_zone: eventType !== "missing_ppe",
      ppe: {hat: {status: "missing", confidence: null}, vest: {status: "present", confidence: 0.88}},
      missing_required_ppe: eventType === "missing_ppe" ? ["hat"] : [],
      active_violations: [{occurrence_id: `occ-${id}`, rule_key: ruleKey, zone_id: zoneId, is_new: true}],
    }],
    detections: [],
    rule: {
      person_inside_zone: eventType !== "missing_ppe",
      machine_state: "running",
      ppe_profile: "hat_vest_v1",
      camera_id: "cam_3",
      zone_id: zoneId,
      ppe_requirements: configuration.ppe_requirements,
      ppe_alert: eventType === "missing_ppe",
    },
  };
  return {
    id,
    camera_id: "cam_3",
    zone_id: zoneId,
    event_type: eventType,
    severity: eventType === "missing_ppe" ? "high" : "critical",
    status: "unacknowledged",
    timestamp: "2026-08-27T10:20:00Z",
    snapshot_path: "/snapshots/pending.jpg",
    occurrence_ids: [`occ-${id}`],
    details: {violations: [ruleKey], video_timestamp_seconds: 1.5, pending_review: inference},
  };
}

function renderLog() {
  return render(<CameraViolationLog cameraId="cam_3" configuration={configuration} />);
}

beforeEach(() => {
  vi.resetAllMocks();
  detectionClient.options = undefined;
  eventUpdates.listener = undefined;
  detectionClient.connect.mockResolvedValue(undefined);
  saveMock.mockResolvedValue({id: 1} as SafetyEvent);
});

it("loads and renders only the selected camera violation log", async () => {
  loadMock.mockResolvedValue([pendingEvent(12)]);

  renderLog();

  expect(await screen.findByText("#12 · Xâm nhập vùng")).toBeInTheDocument();
  expect(screen.getByText("Chưa xác nhận")).toBeInTheDocument();
  expect(loadMock).toHaveBeenCalledWith("cam_3");
});

it("shows a clear empty state when the camera has no violations", async () => {
  loadMock.mockResolvedValue([]);

  renderLog();

  expect(await screen.findByText("Camera này chưa có log vi phạm.")).toBeInTheDocument();
});

it("opens the HITL review popup and saves the camera log decision", async () => {
  loadMock.mockResolvedValue([pendingEvent(8, "missing_ppe")]);

  renderLog();
  const button = await screen.findByRole("button", {name: "Xem chi tiết vi phạm #8"});
  fireEvent.click(button);

  expect(await screen.findByRole("dialog", {name: /Phát hiện thiếu mũ bảo hộ/i})).toBeInTheDocument();
  expect(screen.getByRole("img", {name: "Khung hình vi phạm cần xác minh"})).toHaveAttribute("src", "http://localhost:3000/snapshots/pending.jpg");
  fireEvent.click(screen.getByRole("button", {name: /Vi phạm thực tế/}));

  await waitFor(() => expect(saveMock).toHaveBeenCalledOnce());
  expect(saveMock.mock.calls[0][0]).toMatchObject({
    camera_id: "cam_3",
    zone_id: "camera_wide",
    status: "acknowledged",
    occurrence_ids: ["occ-8"],
  });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

it("refreshes the selected camera log when its WebSocket announces a persisted event", async () => {
  loadMock
    .mockResolvedValueOnce([])
    .mockResolvedValueOnce([])
    .mockResolvedValueOnce([{
      id: 21,
      camera_id: "cam_3",
      zone_id: "press",
      event_type: "zone_intrusion",
      severity: "high",
      status: "unacknowledged",
      timestamp: "2026-08-30T10:20:00Z",
    }]);

  renderLog();
  expect(await screen.findByText("Camera này chưa có log vi phạm.")).toBeInTheDocument();
  await waitFor(() => expect(loadMock).toHaveBeenCalledTimes(2));

  act(() => detectionClient.options?.onResult({pending_event_ids: [21]} as CameraInferenceResult));

  expect(await screen.findByText("#21 · Xâm nhập vùng")).toBeInTheDocument();
  expect(loadMock).toHaveBeenCalledTimes(3);
});

it("refreshes after a review status changes on Live Monitor", async () => {
  const pending = {
    id: 31,
    camera_id: "cam_3",
    zone_id: "press",
    event_type: "zone_intrusion",
    severity: "high",
    status: "unacknowledged" as const,
    timestamp: "2026-08-30T10:20:00Z",
  };
  loadMock
    .mockResolvedValueOnce([pending])
    .mockResolvedValueOnce([pending])
    .mockResolvedValueOnce([]);

  renderLog();
  expect(await screen.findByText("Chưa xác nhận")).toBeInTheDocument();
  await waitFor(() => expect(loadMock).toHaveBeenCalledTimes(2));

  act(() => eventUpdates.listener?.({eventIds: [31], cameraIds: ["cam_3"]}));

  expect(await screen.findByText("Camera này chưa có log vi phạm.")).toBeInTheDocument();
  expect(screen.queryByText("Chưa xác nhận")).not.toBeInTheDocument();
  expect(loadMock).toHaveBeenCalledTimes(3);
});

it("ignores review updates for another camera", async () => {
  loadMock.mockResolvedValue([]);
  renderLog();
  await waitFor(() => expect(loadMock).toHaveBeenCalledTimes(2));

  act(() => eventUpdates.listener?.({eventIds: [41], cameraIds: ["cam_2"]}));

  expect(loadMock).toHaveBeenCalledTimes(2);
});
