import {act, render, screen, waitFor} from "@testing-library/react";
import {beforeEach, expect, it, vi} from "vitest";
import {loadCameraEvents} from "../../api/events";
import type {SafetyEventUpdate} from "../../api/events";
import type {CameraInferenceResult} from "../../types";
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
vi.mock("../events/EventDetailDialog", () => ({
  EventDetailDialog: ({eventId}: {eventId: number | null}) => eventId === null ? null : <div>EVENT DETAIL {eventId}</div>,
}));

const loadMock = vi.mocked(loadCameraEvents);

beforeEach(() => {
  vi.resetAllMocks();
  detectionClient.options = undefined;
  eventUpdates.listener = undefined;
  detectionClient.connect.mockResolvedValue(undefined);
});

it("loads and renders only the selected camera violation log", async () => {
  loadMock.mockResolvedValue([{
    id: 12,
    camera_id: "cam_3",
    zone_id: "press",
    event_type: "zone_intrusion",
    severity: "high",
    status: "acknowledged",
    timestamp: "2026-08-27T10:20:00Z",
  }]);

  render(<CameraViolationLog cameraId="cam_3" />);

  expect(await screen.findByText("#12 · Xâm nhập vùng")).toBeInTheDocument();
  expect(screen.getByText("Đã xác nhận")).toBeInTheDocument();
  expect(loadMock).toHaveBeenCalledWith("cam_3");
});

it("shows a clear empty state when the camera has no violations", async () => {
  loadMock.mockResolvedValue([]);

  render(<CameraViolationLog cameraId="cam_3" />);

  expect(await screen.findByText("Camera này chưa có log vi phạm.")).toBeInTheDocument();
});

it("opens the event detail for a camera log row", async () => {
  loadMock.mockResolvedValue([{
    id: 8,
    camera_id: "cam_3",
    zone_id: "press",
    event_type: "missing_ppe",
    severity: "medium",
    status: "false_alarm",
    timestamp: "2026-08-27T10:20:00Z",
  }]);

  render(<CameraViolationLog cameraId="cam_3" />);
  const button = await screen.findByRole("button", {name: "Xem chi tiết vi phạm #8"});
  button.click();

  await waitFor(() => expect(screen.getByText("EVENT DETAIL 8")).toBeInTheDocument());
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

  render(<CameraViolationLog cameraId="cam_3" />);
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
    .mockResolvedValueOnce([{...pending, status: "acknowledged"}]);

  render(<CameraViolationLog cameraId="cam_3" />);
  expect(await screen.findByText("Chưa xác nhận")).toBeInTheDocument();
  await waitFor(() => expect(loadMock).toHaveBeenCalledTimes(2));

  act(() => eventUpdates.listener?.({eventIds: [31], cameraIds: ["cam_3"]}));

  expect(await screen.findByText("Đã xác nhận")).toBeInTheDocument();
  expect(loadMock).toHaveBeenCalledTimes(3);
});

it("ignores review updates for another camera", async () => {
  loadMock.mockResolvedValue([]);
  render(<CameraViolationLog cameraId="cam_3" />);
  await waitFor(() => expect(loadMock).toHaveBeenCalledTimes(2));

  act(() => eventUpdates.listener?.({eventIds: [41], cameraIds: ["cam_2"]}));

  expect(loadMock).toHaveBeenCalledTimes(2);
});
