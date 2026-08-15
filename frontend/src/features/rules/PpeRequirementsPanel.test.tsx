import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {beforeEach, describe, expect, it, vi} from "vitest";
import {loadPpeRequirements, savePpeRequirements} from "../../api/ppe-requirements";
import {PpeRequirementsPanel} from "./PpeRequirementsPanel";

vi.mock("../../api/ppe-requirements", () => ({
  loadPpeRequirements: vi.fn(),
  savePpeRequirements: vi.fn()
}));

const loadMock = vi.mocked(loadPpeRequirements);
const saveMock = vi.mocked(savePpeRequirements);

const defaultRequirement = {
  camera_id: "uploaded_video",
  zone_id: "zone_01",
  profile: "hat_vest_v1" as const,
  hat_required: false,
  vest_required: false,
  is_configured: false,
  updated_at: null
};

describe("PpeRequirementsPanel", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    loadMock.mockResolvedValue(defaultRequirement);
    saveMock.mockResolvedValue({
      ...defaultRequirement,
      hat_required: true,
      is_configured: true,
      updated_at: "2026-08-06T10:00:00Z"
    });
  });

  it("loads two default-off requirements from the backend", async () => {
    render(<PpeRequirementsPanel cameraId="uploaded_video" zoneId="zone_01" />);

    expect(screen.getByRole("status")).toHaveTextContent("Đang tải cấu hình PPE");
    expect(await screen.findByRole("heading", {name: "Yêu cầu PPE"})).toBeInTheDocument();
    expect(screen.getByRole("checkbox", {name: "Yêu cầu mũ bảo hộ"})).not.toBeChecked();
    expect(screen.getByRole("checkbox", {name: "Yêu cầu áo phản quang"})).not.toBeChecked();
    expect(screen.getByRole("button", {name: "Lưu cấu hình"})).toBeDisabled();
  });

  it("keeps edits as draft and saves the versioned values explicitly", async () => {
    render(<PpeRequirementsPanel cameraId="uploaded_video" zoneId="zone_01" />);
    const hat = await screen.findByRole("checkbox", {name: "Yêu cầu mũ bảo hộ"});

    fireEvent.click(hat);
    expect(hat).toBeChecked();
    expect(saveMock).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", {name: "Lưu cấu hình"}));

    await waitFor(() => expect(saveMock).toHaveBeenCalledWith(
      "uploaded_video",
      "zone_01",
      {
        profile: "hat_vest_v1",
        hat_required: true,
        vest_required: false
      }
    ));
    expect(await screen.findByText("Đã lưu cấu hình")).toBeInTheDocument();
  });

  it("retains the draft and offers retry after a save error", async () => {
    saveMock.mockRejectedValue(new Error("Không thể lưu cấu hình PPE"));
    render(<PpeRequirementsPanel cameraId="uploaded_video" zoneId="zone_01" />);
    const vest = await screen.findByRole("checkbox", {name: "Yêu cầu áo phản quang"});

    fireEvent.click(vest);
    fireEvent.click(screen.getByRole("button", {name: "Lưu cấu hình"}));

    expect(await screen.findByRole("alert")).toHaveTextContent("Không thể lưu cấu hình PPE");
    expect(vest).toBeChecked();
    expect(screen.getByRole("button", {name: "Thử lưu lại"})).toBeEnabled();
  });

  it("shows a retry action when loading fails", async () => {
    loadMock.mockRejectedValueOnce(new Error("Không thể tải cấu hình PPE"));
    render(<PpeRequirementsPanel cameraId="uploaded_video" zoneId="zone_01" />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Không thể tải cấu hình PPE");
    fireEvent.click(screen.getByRole("button", {name: "Thử tải lại"}));
    expect(await screen.findByRole("heading", {name: "Yêu cầu PPE"})).toBeInTheDocument();
    expect(loadMock).toHaveBeenCalledTimes(2);
  });
});
