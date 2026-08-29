import {render, screen, waitFor} from "@testing-library/react";
import {beforeEach, expect, it, vi} from "vitest";
import {loadCameraEvents} from "../../api/events";
import {CameraViolationLog} from "./CameraViolationLog";

vi.mock("../../api/events", () => ({loadCameraEvents: vi.fn()}));
vi.mock("../events/EventDetailDialog", () => ({
  EventDetailDialog: ({eventId}: {eventId: number | null}) => eventId === null ? null : <div>EVENT DETAIL {eventId}</div>,
}));

const loadMock = vi.mocked(loadCameraEvents);

beforeEach(() => {
  vi.resetAllMocks();
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
