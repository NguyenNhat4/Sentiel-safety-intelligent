import {fireEvent, render, screen, waitFor, within} from "@testing-library/react";
import {beforeEach, describe, expect, it, vi} from "vitest";

import {checkVisionWorker, inferVisionWorker} from "../../api/vision-worker-compare";
import {VisionWorkerComparePage} from "./VisionWorkerComparePage";

vi.mock("../../api/vision-worker-compare", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/vision-worker-compare")>();
  return {
    ...actual,
    checkVisionWorker: vi.fn(),
    inferVisionWorker: vi.fn()
  };
});

const mockedHealth = vi.mocked(checkVisionWorker);
const mockedInfer = vi.mocked(inferVisionWorker);

const result = {
  contract_version: "safety_vision_v1" as const,
  request_id: "2aa6bc1d-59b2-4fef-91e0-761e8bb954d4",
  model_version: "test-model",
  canonical_people: [{bbox: [10, 20, 30, 40] as [number, number, number, number], confidence: 0.95, track_id: 7}],
  people: [{hat: {status: "present" as const, confidence: 0.91}, vest: {status: "unknown" as const, confidence: null}}],
  detections: [{class_id: 3 as const, class_name: "person" as const, bbox: [10, 20, 40, 60] as [number, number, number, number], confidence: 0.95, person_index: 0}]
};

describe("VisionWorkerComparePage", () => {
  beforeEach(() => {
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:test-media"),
      revokeObjectURL: vi.fn()
    });
    mockedHealth.mockReset();
    mockedInfer.mockReset();
  });

  it("checks CPU and GPU workers independently", async () => {
    mockedHealth.mockImplementation(async (target) => ({
      status: "healthy",
      contract_version: "safety_vision_v1",
      model_version: target === "cpu" ? "cpu-model" : "gpu-model"
    }));
    render(<VisionWorkerComparePage />);

    fireEvent.click(screen.getByRole("button", {name: "Kiểm tra cả hai worker"}));

    await waitFor(() => expect(mockedHealth).toHaveBeenCalledTimes(2));
    expect(mockedHealth).toHaveBeenCalledWith("cpu");
    expect(mockedHealth).toHaveBeenCalledWith("gpu");
    expect(await screen.findByText("cpu-model")).toBeInTheDocument();
    expect(screen.getByText("gpu-model")).toBeInTheDocument();
  });

  it("submits one selected JPEG to both workers", async () => {
    mockedInfer.mockResolvedValue(result);
    render(<VisionWorkerComparePage />);
    const image = new File(["jpeg"], "factory.jpg", {type: "image/jpeg"});

    fireEvent.change(screen.getByLabelText("Chọn ảnh hoặc video"), {target: {files: [image]}});
    fireEvent.click(screen.getByRole("button", {name: "So sánh 1 frame"}));

    await waitFor(() => expect(mockedInfer).toHaveBeenCalledTimes(2));
    expect(mockedInfer).toHaveBeenCalledWith("cpu", expect.objectContaining({image}));
    expect(mockedInfer).toHaveBeenCalledWith("gpu", expect.objectContaining({image}));
    expect(within(screen.getByRole("article", {name: "Kết quả CPU"})).getByText(/người/)).toHaveTextContent("1 người");
    expect(within(screen.getByRole("article", {name: "Kết quả CUDA GPU"})).getByText(/người/)).toHaveTextContent("1 người");
  });

  it("accepts a local video and exposes bounded sampling controls", () => {
    render(<VisionWorkerComparePage />);
    const video = new File(["video"], "factory.mp4", {type: "video/mp4"});

    fireEvent.change(screen.getByLabelText("Chọn ảnh hoặc video"), {target: {files: [video]}});

    expect(screen.getByText("factory.mp4")).toBeInTheDocument();
    expect(screen.getByRole("button", {name: "Bắt đầu đo video"})).toBeEnabled();
    expect(screen.getByLabelText("Tần suất lấy mẫu")).toHaveValue("2");
  });
});
