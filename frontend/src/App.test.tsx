import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";
import App from "./App";

describe("Sentinel React application", () => {
  beforeEach(() => {
    vi.spyOn(window, "fetch").mockImplementation(async input => {
      const url = String(input);
      if (url.includes("/ppe-requirements/")) return new Response(JSON.stringify({
        camera_id: "uploaded_video", zone_id: "zone_01",
        helmet_required: false, safety_glasses_required: false, gloves_required: false,
        is_configured: false, updated_at: null,
      }), {status: 200, headers: {"Content-Type": "application/json"}});
      if (url.includes("/monitoring-zones")) return new Response(JSON.stringify({
        camera_id: "uploaded_video", revision: 0, zones: [], updated_at: null,
      }), {status: 200, headers: {"Content-Type": "application/json"}});
      return new Response("[]", {status: 200, headers: {"Content-Type": "application/json"}});
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it("navigates between monitor and acknowledged event history", async () => {
    render(<App />);
    expect(screen.getByRole("heading", {name: "Live Monitor"})).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", {name: /Nhật ký vi phạm/}));
    await waitFor(() => expect(screen.getByText("Chưa có vi phạm nào được xác nhận.")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", {name: /Live monitor/}));
    expect(screen.getByText("Tải video demo")).toBeInTheDocument();
  });

  it("does not expose a camera-wide machine switch without a selected zone", () => {
    render(<App />);
    expect(screen.getByRole("button", {name: "Chuyển trạng thái máy của vùng đang chọn"})).toBeDisabled();
    expect(screen.getByText("Chưa chọn vùng")).toBeInTheDocument();
  });

  it("creates points only after the explicit Tạo vùng action", async () => {
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
    fireEvent.pointerDown(canvas, {clientX: 100, clientY: 100, pointerId: 1});
    expect(screen.getByText("0 vùng đã cấu hình")).toBeInTheDocument();

    await waitFor(() => expect(screen.getByRole("button", {name: /Tạo vùng/})).toBeEnabled());
    fireEvent.click(screen.getByRole("button", {name: /Tạo vùng/}));
    expect(screen.getByText("Vùng 1 · 0/4 · đang vẽ")).toBeInTheDocument();
    [[100, 100], [900, 100], [900, 400], [100, 400]].forEach(([clientX, clientY]) => {
      fireEvent.pointerDown(canvas, {clientX, clientY, pointerId: 1});
      fireEvent.pointerUp(canvas, {pointerId: 1});
    });
    await waitFor(() => expect(screen.getByText("Vùng 1 · 4/4 · kéo điểm để chỉnh")).toBeInTheDocument());
    expect(screen.getByText((_, node) => node?.textContent === "4/4 · BẬT · STOP")).toBeInTheDocument();
  });
});
