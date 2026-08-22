import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {beforeEach, expect, it, vi} from "vitest";
import {getStreamConfiguration, updateStreamConfiguration} from "../../api/stream-config";
import {loadMonitoringZones, saveMonitoringZones} from "../../api/monitoring-zones";
import {getHlsAccessToken} from "../../api/auth";
import {CameraConfigurationPage} from "./CameraConfigurationPage";

vi.mock("../../api/stream-config", async () => ({
  getStreamConfiguration: vi.fn(),
  updateStreamConfiguration: vi.fn(),
}));
vi.mock("../../api/monitoring-zones", () => ({loadMonitoringZones: vi.fn(), saveMonitoringZones: vi.fn()}));
vi.mock("../../api/auth", () => ({getHlsAccessToken: vi.fn().mockResolvedValue({access_token: "hls", expires_in: 900})}));
vi.mock("../monitor/HlsVideo", () => ({HlsVideo: ({label}: {label: string}) => <video aria-label={label} />}));
vi.mock("../rules/PpeRequirementsPanel", () => ({PpeRequirementsPanel: ({cameraId, zoneId}: {cameraId: string; zoneId: string}) => <div>{cameraId}:{zoneId}<span>Yêu cầu mũ bảo hộ</span><span>Yêu cầu áo phản quang</span></div>}));

const getConfigMock = vi.mocked(getStreamConfiguration);
const updateConfigMock = vi.mocked(updateStreamConfiguration);
const loadZonesMock = vi.mocked(loadMonitoringZones);
const hlsTokenMock = vi.mocked(getHlsAccessToken);
const saveZonesMock = vi.mocked(saveMonitoringZones);

beforeEach(() => {
  vi.resetAllMocks();
  hlsTokenMock.mockResolvedValue({access_token: "hls", token_type: "bearer", expires_in: 900});
  updateConfigMock.mockImplementation(async mappings => ({mappings, updated_at: null}));
  getConfigMock.mockResolvedValue({
    mappings: [
      {camera_id: "cam_1", stream_camera_id: "xuong1"},
      {camera_id: "cam_2", stream_camera_id: "xuong2"},
    ],
    updated_at: null,
  });
  loadZonesMock.mockImplementation(async cameraId => ({
    camera_id: cameraId,
    revision: 1,
    zones: cameraId === "cam_1" ? [{
      zone_id: "press",
      display_name: "Máy dập",
      points: [{x: 0.1, y: 0.1}, {x: 0.4, y: 0.1}, {x: 0.4, y: 0.5}, {x: 0.1, y: 0.5}],
      machine_state: "stopped",
      enabled: true,
      order: 0,
    }] : [],
    updated_at: null,
  }));
  saveZonesMock.mockImplementation(async (cameraId, revision, zones) => ({camera_id: cameraId, revision: revision + 1, zones, updated_at: null}));
});

it("draws four points and persists the selected camera zone", async () => {
  loadZonesMock.mockResolvedValue({camera_id: "cam_1", revision: 0, zones: [], updated_at: null});
  const {container} = render(<CameraConfigurationPage />);
  await screen.findByRole("combobox", {name: "Chọn camera"});
  await screen.findByRole("option", {name: "Vùng 1"});
  expect(screen.getByRole("switch", {name: "Trạng thái máy"})).toBeInTheDocument();
  expect(screen.getByText("cam_1:zone_1")).toBeInTheDocument();
  expect(screen.getByText("Yêu cầu mũ bảo hộ")).toBeInTheDocument();
  expect(screen.getByText("Yêu cầu áo phản quang")).toBeInTheDocument();
  const overlay = container.querySelector(".zone-config-overlay") as SVGSVGElement;
  vi.spyOn(overlay, "getBoundingClientRect").mockReturnValue({left: 0, top: 0, width: 100, height: 100} as DOMRect);
  for (const [clientX, clientY] of [[10, 10], [40, 10], [40, 50], [10, 50]]) {
    const event = new Event("pointerdown", {bubbles: true});
    Object.defineProperties(event, {clientX: {value: clientX}, clientY: {value: clientY}});
    fireEvent(overlay, event);
  }

  expect(screen.getByText("cam_1:zone_1")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {name: "Lưu vùng"}));
  await waitFor(() => expect(saveZonesMock).toHaveBeenCalledWith(
    "cam_1",
    0,
    [expect.objectContaining({zone_id: "zone_1", points: expect.any(Array)})],
  ));
});

it("selects a mapped camera and shows its video, zones and rules", async () => {
  render(<CameraConfigurationPage />);

  expect(await screen.findByRole("combobox", {name: "Chọn camera"})).toHaveValue("cam_1");
  expect(screen.getByLabelText("Cấu hình Camera 1")).toBeInTheDocument();
  expect(await screen.findByRole("option", {name: "Máy dập"})).toBeInTheDocument();
  expect(screen.getByText("cam_1:press")).toBeInTheDocument();

  fireEvent.change(screen.getByRole("combobox", {name: "Chọn camera"}), {target: {value: "cam_2"}});
  await waitFor(() => expect(loadZonesMock).toHaveBeenLastCalledWith("cam_2"));
  expect(screen.getByLabelText("Cấu hình Camera 2")).toBeInTheDocument();
  expect(screen.getByRole("option", {name: "Vùng 1"})).toBeInTheDocument();
});

it("removes a zone locally and persists the deletion only when saved", async () => {
  render(<CameraConfigurationPage />);

  expect(await screen.findByRole("option", {name: "Máy dập"})).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {name: "Xóa vùng"}));

  expect(screen.getByRole("option", {name: "Chưa có vùng nào"})).toBeInTheDocument();
  expect(saveZonesMock).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", {name: "Lưu vùng"}));
  await waitFor(() => expect(saveZonesMock).toHaveBeenCalledWith("cam_1", 1, []));
});
