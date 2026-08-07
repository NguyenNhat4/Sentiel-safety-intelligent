import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {afterEach, describe, expect, it, vi} from "vitest";
import App from "./App";

describe("Sentinel React application", () => {
  afterEach(() => vi.restoreAllMocks());

  it("navigates between monitor and acknowledged event history", async () => {
    vi.spyOn(window, "fetch").mockImplementation(async input => {
      const url = String(input);
      const body = url.includes("/ppe-requirements/")
        ? JSON.stringify({
          camera_id: "uploaded_video", zone_id: "zone_01",
          helmet_required: false, safety_glasses_required: false, gloves_required: false,
          is_configured: false, updated_at: null
        })
        : "[]";
      return new Response(body, {status: 200, headers: {"Content-Type": "application/json"}});
    });
    render(<App />);
    expect(screen.getByRole("heading", {name: "Live Monitor"})).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", {name: /Nhật ký vi phạm/}));
    await waitFor(() => expect(screen.getByText("Chưa có vi phạm nào được xác nhận.")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", {name: /Live monitor/}));
    expect(screen.getByText("Tải video demo")).toBeInTheDocument();
  });

  it("updates the machine rule through React state", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", {name: "Chuyển trạng thái máy"}));
    expect(screen.getByText("Machine A đã dừng")).toBeInTheDocument();
    expect(screen.getByText("OFF")).toBeInTheDocument();
  });

  it("marks the monitor ready after exactly four zone points", () => {
    const {container} = render(<App />);
    const video = container.querySelector("video") as HTMLVideoElement;
    Object.defineProperties(video, {
      videoWidth: {value: 1280}, videoHeight: {value: 720}, duration: {value: 20}
    });
    fireEvent.loadedMetadata(video);
    const canvas = container.querySelector(".camera-scene canvas") as HTMLCanvasElement;
    vi.spyOn(canvas, "getBoundingClientRect").mockReturnValue({
      left: 0, top: 0, width: 1000, height: 500, right: 1000, bottom: 500, x: 0, y: 0, toJSON: () => ({})
    });
    [[100, 100], [900, 100], [900, 400], [100, 400]].forEach(([clientX, clientY]) => {
      fireEvent.pointerDown(canvas, {clientX, clientY, pointerId: 1});
      fireEvent.pointerUp(canvas, {pointerId: 1});
    });
    expect(screen.getByText("Vùng đã sẵn sàng · Kéo điểm để điều chỉnh")).toBeInTheDocument();
    expect(screen.getByText("Zone sẵn sàng · inference realtime")).toBeInTheDocument();
  });
});
