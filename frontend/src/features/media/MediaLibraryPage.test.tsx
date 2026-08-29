import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {beforeEach, expect, it, vi} from "vitest";
import {deleteMediaAsset, listMediaAssets, uploadMediaAsset} from "../../api/media-assets";
import {MediaLibraryPage} from "./MediaLibraryPage";

vi.mock("../../api/media-assets", () => ({deleteMediaAsset: vi.fn(), listMediaAssets: vi.fn(), uploadMediaAsset: vi.fn()}));
const listMock = vi.mocked(listMediaAssets);
const uploadMock = vi.mocked(uploadMediaAsset);
const deleteMock = vi.mocked(deleteMediaAsset);
const assets = [
  {id: "video-1", display_name: "Ca sáng", media_type: "video" as const, status: "READY" as const, content_type: "video/mp4", size_bytes: 10, storage_backend: "s3" as const, uploaded_at: "2026-08-23T08:00:00Z", assigned_camera_id: "cam_1", can_delete: false},
  {id: "image-1", display_name: "Máy dập", media_type: "image" as const, status: "ERROR" as const, content_type: "image/png", size_bytes: 10, storage_backend: "filesystem" as const, uploaded_at: "2026-08-23T09:00:00Z", assigned_camera_id: null, can_delete: true},
];

beforeEach(() => { vi.resetAllMocks(); listMock.mockResolvedValue(assets); uploadMock.mockResolvedValue({...assets[0], id: "new", assigned_camera_id: null, can_delete: true}); deleteMock.mockResolvedValue(); vi.spyOn(window, "confirm").mockReturnValue(true); });

it("shows inventory metadata, server deletion permission, upload and delete", async () => {
  render(<MediaLibraryPage />);
  expect(await screen.findByText("Ca sáng")).toBeInTheDocument();
  expect(screen.getByText("Video")).toBeInTheDocument();
  expect(screen.getByText("Hình ảnh")).toBeInTheDocument();
  expect(screen.getByText("cam_1")).toBeInTheDocument();
  const deleteButtons = screen.getAllByRole("button", {name: "Xóa"});
  expect(deleteButtons[0]).toBeDisabled(); expect(deleteButtons[1]).toBeEnabled();
  fireEvent.click(deleteButtons[1]);
  await waitFor(() => expect(deleteMock).toHaveBeenCalledWith("image-1"));

  fireEvent.change(screen.getByLabelText("Tên hiển thị"), {target: {value: "Video mới"}});
  const file = new File(["media"], "demo.mp4", {type: "video/mp4"});
  fireEvent.change(screen.getByLabelText("Video hoặc hình ảnh"), {target: {files: [file]}});
  fireEvent.submit(screen.getByRole("button", {name: "Tải media lên"}).closest("form")!);
  await waitFor(() => expect(uploadMock).toHaveBeenCalledWith("Video mới", file));
});
