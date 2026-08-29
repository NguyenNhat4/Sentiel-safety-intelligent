import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {beforeEach, expect, it, vi} from "vitest";
import {loadCameraConfiguration, saveCameraConfiguration} from "../../api/camera-configurations";
import {listMediaAssets} from "../../api/media-assets";
import {CameraConfigurationPage} from "./CameraConfigurationPage";

it("orders the camera workspace, settings inspector, and violation control log", async () => {
  render(<CameraConfigurationPage cameraId="cam_3" onBack={vi.fn()} onSaved={vi.fn()} />);

  const camera = await screen.findByRole("region", {name: "Màn hình Camera 3"});
  const settings = screen.getByRole("complementary", {name: "Thiết lập Camera 3"});
  const violations = screen.getByRole("region", {name: "Nhật ký vi phạm Camera 3"});
  const layout = camera.closest(".camera-detail-layout");

  expect(layout).not.toBeNull();
  expect(layout).toContainElement(settings);
  expect(layout).toContainElement(violations);
  expect(camera.compareDocumentPosition(settings) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(settings.compareDocumentPosition(violations) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(settings).toContainElement(screen.getByRole("combobox", {name: "Nguồn media"}));
  expect(settings).toContainElement(screen.getByRole("button", {name: "Lưu cấu hình"}));
});

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
const cameraPpe = {profile: "hat_vest_v1" as const, hat_required: false, vest_required: false};
const configuration = {camera_id: "cam_3", revision: 7, asset_id: "asset-1", machine_state: "stopped" as const, ppe_requirements: cameraPpe, zones: [zone], updated_at: null};
const emptyConfiguration = {...configuration, zones: []};

beforeEach(() => {
  vi.resetAllMocks();
  loadMock.mockResolvedValue(configuration);
  saveMock.mockResolvedValue({...configuration, revision: 8});
  assetsMock.mockResolvedValue([
    {id: "asset-1", display_name: "Ca sáng", media_type: "video", status: "READY", content_type: "video/mp4", size_bytes: 10, storage_backend: "s3", uploaded_at: "2026-08-23T08:00:00Z", assigned_camera_id: "cam_3", can_delete: false},
    {id: "asset-2", display_name: "Ảnh máy dập", media_type: "image", status: "READY", content_type: "image/png", size_bytes: 10, storage_backend: "filesystem", uploaded_at: "2026-08-23T08:00:00Z", assigned_camera_id: null, can_delete: true},
    {id: "asset-3", display_name: "Đang xử lý", media_type: "video", status: "UPLOADING", content_type: "video/mp4", size_bytes: 10, storage_backend: "s3", uploaded_at: "2026-08-23T08:00:00Z", assigned_camera_id: null, can_delete: false},
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
  expect(screen.getByText("Camera đã kết nối")).toBeInTheDocument();
});

it("saves asset, machine, zones and PPE once and clears the dirty draft", async () => {
  const onSaved = vi.fn();
  const onBack = vi.fn();
  render(<CameraConfigurationPage cameraId="cam_3" onBack={onBack} onSaved={onSaved} />);
  fireEvent.click(await screen.findByRole("checkbox", {name: "Yêu cầu mũ bảo hộ"}));
  fireEvent.click(screen.getByRole("checkbox", {name: "Yêu cầu áo phản quang"}));
  const save = screen.getByRole("button", {name: "Lưu cấu hình"});
  fireEvent.click(save); fireEvent.click(save);
  await waitFor(() => expect(saveMock).toHaveBeenCalledTimes(1));
  expect(saveMock).toHaveBeenCalledWith("cam_3", expect.objectContaining({
    expected_revision: 7, asset_id: "asset-1", machine_state: "stopped",
    ppe_requirements: expect.objectContaining({hat_required: true, vest_required: true}),
    zones: [expect.objectContaining({zone_id: "press", ppe_requirements: expect.objectContaining({hat_required: true, vest_required: true, zone_intrusion_enabled: true})})],
  }));
  expect(await screen.findByRole("status")).toHaveTextContent("Đã lưu");
  expect(screen.getByRole("button", {name: "Lưu cấu hình"})).toBeDisabled();
  expect(onSaved).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", {name: "Quay lại Live Monitor"}));
  expect(onBack).toHaveBeenCalledOnce();
});

it("loads persisted hat and vest requirements as enabled", async () => {
  loadMock.mockResolvedValue({
    ...configuration,
    ppe_requirements: {...cameraPpe, hat_required: true, vest_required: true},
    zones: [{...zone, ppe_requirements: {...zone.ppe_requirements, hat_required: true, vest_required: true}}],
  });
  render(<CameraConfigurationPage cameraId="cam_3" onBack={vi.fn()} onSaved={vi.fn()} />);

  expect(await screen.findByRole("checkbox", {name: "Yêu cầu mũ bảo hộ"})).toBeChecked();
  expect(screen.getByRole("checkbox", {name: "Yêu cầu áo phản quang"})).toBeChecked();
});

it("shows explicit machine-state choices and updates the draft accessibly", async () => {
  render(<CameraConfigurationPage cameraId="cam_3" onBack={vi.fn()} onSaved={vi.fn()} />);

  const offButton = await screen.findByRole("button", {name: "TẮT"});
  const onButton = screen.getByRole("button", {name: "BẬT"});
  expect(offButton).toHaveAttribute("aria-pressed", "true");
  expect(onButton).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByText("Máy đã dừng, quy tắc PPE tạm thời không được kiểm tra.")).toBeInTheDocument();

  fireEvent.click(onButton);
  expect(onButton).toHaveAttribute("aria-pressed", "true");
  expect(offButton).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByText("Hệ thống tự động kiểm tra mũ bảo hiểm và áo phản quang.")).toBeInTheDocument();
});

it("shows zone drawing progress and explains why save is blocked", async () => {
  render(<CameraConfigurationPage cameraId="cam_3" onBack={vi.fn()} onSaved={vi.fn()} />);

  expect(await screen.findByText("4/4 điểm")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {name: "Tạo vùng"}));
  expect(screen.getByText("0/4 điểm")).toBeInTheDocument();
  expect(screen.getByText("Bấm lần lượt 4 điểm trên khung camera để khép vùng.")).toBeInTheDocument();
  expect(screen.getByText("Vùng đang chọn cần đủ 4 điểm (0/4).")).toBeInTheDocument();
  expect(screen.getByRole("button", {name: "Lưu cấu hình"})).toBeDisabled();
});

it("reports a dirty draft before delegating navigation to the application", async () => {
  const onBack = vi.fn();
  const onDirtyChange = vi.fn();
  render(<CameraConfigurationPage cameraId="cam_3" onBack={onBack} onSaved={vi.fn()} onDirtyChange={onDirtyChange} />);

  fireEvent.click(await screen.findByRole("checkbox", {name: "Yêu cầu mũ bảo hộ"}));
  await waitFor(() => expect(onDirtyChange).toHaveBeenLastCalledWith(true));
  const back = screen.getByRole("button", {name: "Quay lại Live Monitor"});
  fireEvent.click(back);
  expect(onBack).toHaveBeenCalledOnce();
});

it("keeps the controlled draft and reports a revision conflict", async () => {
  saveMock.mockRejectedValue(new Error("Cấu hình đã thay đổi ở nơi khác."));
  render(<CameraConfigurationPage cameraId="cam_3" onBack={vi.fn()} onSaved={vi.fn()} />);
  const vest = await screen.findByRole("checkbox", {name: "Yêu cầu áo phản quang"});
  fireEvent.click(vest); fireEvent.click(screen.getByRole("button", {name: "Lưu cấu hình"}));
  expect(await screen.findByRole("alert")).toHaveTextContent("Cấu hình đã thay đổi ở nơi khác.");
  expect(vest).toBeChecked();
});

it("lets users set PPE switches before creating a zone and carries them into the new zone", async () => {
  loadMock.mockResolvedValue(emptyConfiguration);
  saveMock.mockResolvedValue({...emptyConfiguration, revision: 8});
  render(<CameraConfigurationPage cameraId="cam_3" onBack={vi.fn()} onSaved={vi.fn()} />);

  expect(await screen.findByText("PPE áp dụng toàn bộ khung hình; không cần tạo vùng.")).toBeInTheDocument();
  const hat = screen.getByRole("checkbox", {name: "Yêu cầu mũ bảo hộ"});
  const vest = screen.getByRole("checkbox", {name: "Yêu cầu áo phản quang"});
  expect(hat).not.toBeChecked();
  expect(vest).not.toBeChecked();
  fireEvent.click(hat);
  fireEvent.click(vest);
  fireEvent.click(screen.getByRole("button", {name: "Tạo vùng"}));
  expect(hat).toBeChecked();
  expect(vest).toBeChecked();
  expect(screen.queryByRole("checkbox", {name: "Detect vùng cấm"})).not.toBeInTheDocument();
  expect(screen.queryByRole("checkbox", {name: "Cảnh báo xâm nhập zone"})).not.toBeInTheDocument();
  expect(screen.getByRole("button", {name: "Lưu cấu hình"})).toBeDisabled();
});

it("saves camera-wide PPE without requiring a zone", async () => {
  const onSaved = vi.fn();
  loadMock.mockResolvedValue(emptyConfiguration);
  saveMock.mockResolvedValue({...emptyConfiguration, revision: 8, ppe_requirements: {...cameraPpe, hat_required: true}});
  render(<CameraConfigurationPage cameraId="cam_3" onBack={vi.fn()} onSaved={onSaved} />);

  fireEvent.click(await screen.findByRole("checkbox", {name: "Yêu cầu mũ bảo hộ"}));
  const save = screen.getByRole("button", {name: "Lưu cấu hình"});
  expect(save).toBeEnabled();
  fireEvent.click(save);

  await waitFor(() => expect(saveMock).toHaveBeenCalledWith("cam_3", expect.objectContaining({
    ppe_requirements: expect.objectContaining({hat_required: true, vest_required: false}),
    zones: [],
  })));
  expect(await screen.findByRole("status")).toHaveTextContent("Đã lưu");
  expect(onSaved).not.toHaveBeenCalled();
});

it("allows disconnecting camera source and saves asset_id as null", async () => {
  const onBack = vi.fn();
  saveMock.mockResolvedValue({...configuration, revision: 8, asset_id: null});
  render(<CameraConfigurationPage cameraId="cam_3" onBack={onBack} onSaved={vi.fn()} />);
  const disconnectBtn = await screen.findByRole("button", {name: "Ngắt kết nối nguồn media"});
  expect(disconnectBtn).toBeInTheDocument();
  fireEvent.click(disconnectBtn);

  expect(screen.queryByRole("button", {name: "Ngắt kết nối nguồn media"})).not.toBeInTheDocument();
  expect(screen.getByText("Chọn media để xem preview và vẽ vùng.")).toBeInTheDocument();
  const saveButton = screen.getByRole("button", {name: "Lưu cấu hình"});
  expect(saveButton).toBeEnabled();
  fireEvent.click(saveButton);

  await waitFor(() => expect(saveMock).toHaveBeenCalledWith("cam_3", expect.objectContaining({asset_id: null})));
  expect(await screen.findByRole("status")).toHaveTextContent("Đã lưu");
  fireEvent.click(screen.getByRole("button", {name: "Quay lại Live Monitor"}));
  expect(onBack).toHaveBeenCalledOnce();
});
