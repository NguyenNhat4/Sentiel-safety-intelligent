import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {beforeEach, expect, it, vi} from "vitest";
import {loadCameraConfiguration, saveCameraConfiguration} from "../../api/camera-configurations";
import {listMediaAssets} from "../../api/media-assets";
import {CameraConfigurationPage} from "./CameraConfigurationPage";

vi.mock("../../api/camera-configurations", () => ({loadCameraConfiguration: vi.fn(), saveCameraConfiguration: vi.fn()}));
vi.mock("../../api/media-assets", () => ({listMediaAssets: vi.fn()}));
vi.mock("../media/AuthenticatedMedia", () => ({AuthenticatedMedia: ({label}: {label: string}) => <video aria-label={label} />}));

const loadMock = vi.mocked(loadCameraConfiguration);
const saveMock = vi.mocked(saveCameraConfiguration);
const assetsMock = vi.mocked(listMediaAssets);
const zone = {
  zone_id: "press", display_name: "Máy dập", points: [{x: .1, y: .1}, {x: .4, y: .1}, {x: .4, y: .5}, {x: .1, y: .5}], enabled: true, order: 0,
  ppe_requirements: {profile: "hat_vest_v1" as const, hat_required: false, vest_required: false, restricted_area_detection_enabled: false, zone_intrusion_enabled: true},
};
const configuration = {camera_id: "cam_3", revision: 7, asset_id: "asset-1", machine_state: "stopped" as const, zones: [zone], updated_at: null};
const emptyConfiguration = {...configuration, zones: []};

beforeEach(() => {
  vi.resetAllMocks();
  loadMock.mockResolvedValue(configuration);
  saveMock.mockResolvedValue({...configuration, revision: 8});
  assetsMock.mockResolvedValue([
    {id: "asset-1", display_name: "Ca sáng", media_type: "video", status: "READY", content_type: "video/mp4", size_bytes: 10, uploaded_at: "2026-08-23T08:00:00Z", assigned_camera_id: "cam_3", can_delete: false},
    {id: "asset-2", display_name: "Ảnh máy dập", media_type: "image", status: "READY", content_type: "image/png", size_bytes: 10, uploaded_at: "2026-08-23T08:00:00Z", assigned_camera_id: null, can_delete: true},
    {id: "asset-3", display_name: "Đang xử lý", media_type: "video", status: "UPLOADING", content_type: "video/mp4", size_bytes: 10, uploaded_at: "2026-08-23T08:00:00Z", assigned_camera_id: null, can_delete: false},
  ]);
});

it("loads the exact camera prop with READY media and no camera selector", async () => {
  render(<CameraConfigurationPage cameraId="cam_3" onBack={vi.fn()} onSaved={vi.fn()} />);
  expect(await screen.findByRole("heading", {name: "Cấu hình Camera 3"})).toBeInTheDocument();
  expect(loadMock).toHaveBeenCalledWith("cam_3", expect.any(AbortSignal));
  expect(screen.queryByRole("combobox", {name: "Chọn camera"})).not.toBeInTheDocument();
  expect(screen.getByRole("option", {name: "Ca sáng · Video"})).toBeInTheDocument();
  expect(screen.getByRole("option", {name: "Ảnh máy dập · Hình ảnh"})).toBeInTheDocument();
  expect(screen.queryByText("Đang xử lý")).not.toBeInTheDocument();
  expect(screen.getByLabelText("Preview Camera 3")).toBeInTheDocument();
});

it("saves asset, machine, zones and PPE once then returns without starting inference", async () => {
  const onSaved = vi.fn();
  render(<CameraConfigurationPage cameraId="cam_3" onBack={vi.fn()} onSaved={onSaved} />);
  fireEvent.click(await screen.findByRole("checkbox", {name: "Yêu cầu mũ bảo hộ"}));
  fireEvent.click(screen.getByRole("checkbox", {name: "Yêu cầu áo phản quang"}));
  const save = screen.getByRole("button", {name: "Lưu cấu hình"});
  fireEvent.click(save); fireEvent.click(save);
  await waitFor(() => expect(saveMock).toHaveBeenCalledTimes(1));
  expect(saveMock).toHaveBeenCalledWith("cam_3", expect.objectContaining({
    expected_revision: 7, asset_id: "asset-1", machine_state: "stopped",
    zones: [expect.objectContaining({zone_id: "press", ppe_requirements: expect.objectContaining({hat_required: true, vest_required: true, zone_intrusion_enabled: true})})],
  }));
  expect(onSaved).toHaveBeenCalledOnce();
});

it("loads persisted hat and vest requirements as enabled", async () => {
  loadMock.mockResolvedValue({
    ...configuration,
    zones: [{...zone, ppe_requirements: {...zone.ppe_requirements, hat_required: true, vest_required: true}}],
  });
  render(<CameraConfigurationPage cameraId="cam_3" onBack={vi.fn()} onSaved={vi.fn()} />);

  expect(await screen.findByRole("checkbox", {name: "Yêu cầu mũ bảo hộ"})).toBeChecked();
  expect(screen.getByRole("checkbox", {name: "Yêu cầu áo phản quang"})).toBeChecked();
});

it("keeps the controlled draft and reports a revision conflict", async () => {
  saveMock.mockRejectedValue(new Error("Cấu hình đã thay đổi ở nơi khác."));
  render(<CameraConfigurationPage cameraId="cam_3" onBack={vi.fn()} onSaved={vi.fn()} />);
  const vest = await screen.findByRole("checkbox", {name: "Yêu cầu áo phản quang"});
  fireEvent.click(vest); fireEvent.click(screen.getByRole("button", {name: "Lưu cấu hình"}));
  expect(await screen.findByRole("alert")).toHaveTextContent("Cấu hình đã thay đổi ở nơi khác.");
  expect(vest).toBeChecked();
});

it("does not offer unsaveable PPE switches without a zone", async () => {
  loadMock.mockResolvedValue(emptyConfiguration);
  saveMock.mockResolvedValue({...emptyConfiguration, revision: 8});
  render(<CameraConfigurationPage cameraId="cam_3" onBack={vi.fn()} onSaved={vi.fn()} />);

  expect(await screen.findByText("Hãy tạo một vùng để cấu hình yêu cầu PPE.")).toBeInTheDocument();
  expect(screen.queryByRole("checkbox", {name: "Yêu cầu mũ bảo hộ"})).not.toBeInTheDocument();
  expect(screen.queryByRole("checkbox", {name: "Yêu cầu áo phản quang"})).not.toBeInTheDocument();
  expect(screen.queryByRole("checkbox", {name: "Detect vùng cấm"})).not.toBeInTheDocument();
  expect(screen.queryByRole("checkbox", {name: "Cảnh báo xâm nhập zone"})).not.toBeInTheDocument();
  expect(screen.getByRole("button", {name: "Lưu cấu hình"})).toBeDisabled();
});

it("allows disconnecting camera source and saves asset_id as null", async () => {
  const onSaved = vi.fn();
  render(<CameraConfigurationPage cameraId="cam_3" onBack={vi.fn()} onSaved={onSaved} />);
  const disconnectBtn = await screen.findByRole("button", {name: "Ngắt kết nối nguồn media"});
  expect(disconnectBtn).toBeInTheDocument();
  fireEvent.click(disconnectBtn);

  expect(screen.queryByRole("button", {name: "Ngắt kết nối nguồn media"})).not.toBeInTheDocument();
  expect(screen.getByText("Chọn media để xem preview và vẽ vùng.")).toBeInTheDocument();

  const saveBtn = screen.getByRole("button", {name: "Lưu cấu hình"});
  expect(saveBtn).toBeEnabled();
  fireEvent.click(saveBtn);
  await waitFor(() => expect(saveMock).toHaveBeenCalledWith("cam_3", expect.objectContaining({
    asset_id: null,
  })));
});
