import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {afterEach, describe, expect, it, vi} from "vitest";
import App from "./App";

const user = {
  id: "user-1",
  full_name: "Safety Manager",
  email: "antoan@sentinel.local",
  role: "safety_manager" as const,
  role_label: "Safety Manager",
  must_change_password: false
};

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {status, headers: {"Content-Type": "application/json"}});
}

function mockAuthenticatedSession(): void {
  window.sessionStorage.setItem("sentinel.auth.access_token", "token-1");
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/auth/me")) return jsonResponse({user, expires_at: "2026-08-11T00:00:00Z"});
    if (url.includes("/ppe-requirements/")) return jsonResponse({
      camera_id: "uploaded_video",
      zone_id: "zone_01",
      profile: "hat_vest_v1",
      hat_required: false,
      vest_required: false,
      is_configured: false,
      updated_at: null
    });
    if (url.includes("/monitoring-zones")) return jsonResponse({
      camera_id: "uploaded_video",
      revision: 0,
      zones: [],
      updated_at: null
    });
    return jsonResponse([]);
  }));
}

afterEach(() => {
  window.sessionStorage.clear();
  vi.restoreAllMocks();
});

describe("Sentinel authentication", () => {
  it("shows the login page when there is no saved session", async () => {
    vi.stubGlobal("fetch", vi.fn());
    render(<App />);
    await waitFor(() => expect(screen.getByRole("button", {name: /Đăng nhập/})).toBeInTheDocument());
  });

  it("opens the application after the API accepts credentials", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/auth/login")) {
        return jsonResponse({access_token: "token-1", token_type: "bearer", user});
      }
      if (url.includes("/monitoring-zones")) {
        return jsonResponse({camera_id: "uploaded_video", revision: 0, zones: [], updated_at: null});
      }
      if (url.includes("/ppe-requirements/")) {
        return jsonResponse({
          camera_id: "uploaded_video",
          zone_id: "zone_01",
          profile: "hat_vest_v1",
          hat_required: false,
          vest_required: false,
          is_configured: false,
          updated_at: null
        });
      }
      return jsonResponse([]);
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    await screen.findByRole("button", {name: /Đăng nhập/});
    fireEvent.change(screen.getByLabelText(/Email/), {target: {value: user.email}});
    fireEvent.change(screen.getByLabelText(/Mật khẩu/), {target: {value: "Sentinel123!"}});
    fireEvent.click(screen.getByRole("button", {name: /Đăng nhập/}));
    await waitFor(() => expect(screen.getByRole("heading", {name: "Live Monitor"})).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/auth/login", expect.objectContaining({method: "POST"}));
  });

  it("opens the tabbed system administration page for a system admin", async () => {
    const admin = {
      ...user,
      id: "admin-1",
      email: "admin@sentinel.local",
      role: "system_admin" as const,
      role_label: "Quản trị hệ thống"
    };
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/auth/login")) {
        return jsonResponse({access_token: "admin-token", token_type: "bearer", user: admin});
      }
      if (url.includes("/auth/users")) {
        return jsonResponse([{...admin, is_active: true, created_at: "2026-08-11T00:00:00Z"}]);
      }
      if (url.includes("/monitoring-zones")) {
        return jsonResponse({camera_id: "uploaded_video", revision: 0, zones: [], updated_at: null});
      }
      return jsonResponse([]);
    }));
    render(<App />);
    await screen.findByRole("button", {name: /Đăng nhập/});
    fireEvent.change(screen.getByLabelText(/Email/), {target: {value: admin.email}});
    fireEvent.change(screen.getByLabelText(/Mật khẩu/), {target: {value: "Sentinel123!"}});
    fireEvent.click(screen.getByRole("button", {name: /Đăng nhập/}));

    await screen.findByRole("heading", {name: "Live Monitor"});
    fireEvent.click(screen.getByRole("button", {name: /Quản trị hệ thống/}));
    expect(await screen.findByRole("tab", {name: "Tài khoản"})).toBeInTheDocument();
    expect(screen.getByRole("tab", {name: "Vai trò & quyền"})).toBeInTheDocument();
    expect(screen.getByRole("tab", {name: "Bảo mật"})).toBeInTheDocument();
    expect(screen.getByRole("button", {name: /Quản trị hệ thống/})).toBeInTheDocument();
  });

  it("forces a temporary-password user to change password before opening the app", async () => {
    const firstLoginUser = {...user, must_change_password: true};
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({
      access_token: "first-login-token",
      token_type: "bearer",
      user: firstLoginUser
    })));
    render(<App />);
    await screen.findByRole("button", {name: /Đăng nhập/});
    fireEvent.change(screen.getByLabelText(/Email/), {target: {value: firstLoginUser.email}});
    fireEvent.change(screen.getByLabelText(/^Mật khẩu$/), {target: {value: "Temporary123!"}});
    fireEvent.click(screen.getByRole("button", {name: /Đăng nhập/}));

    expect(await screen.findByRole("heading", {name: "Lần đăng nhập đầu tiên"})).toBeInTheDocument();
    expect(screen.queryByRole("heading", {name: "Live Monitor"})).not.toBeInTheDocument();
  });
});

describe("Sentinel React application", () => {
  it("navigates between monitor and acknowledged event history", async () => {
    mockAuthenticatedSession();
    render(<App />);
    await screen.findByRole("heading", {name: "Live Monitor"});
    fireEvent.click(screen.getByRole("button", {name: /Nhật ký vi phạm/}));
    await waitFor(() => expect(screen.getByText("Chưa có vi phạm nào được xác nhận.")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", {name: /Live monitor/}));
    expect(screen.getByText("Tải video demo")).toBeInTheDocument();
  });

  it("keeps the camera-wide machine switch available without a selected zone", async () => {
    mockAuthenticatedSession();
    render(<App />);
    await screen.findByRole("heading", {name: "Live Monitor"});
    const machineToggle = screen.getByRole("button", {name: "Chuyển trạng thái máy"});
    expect(machineToggle).toBeEnabled();
    fireEvent.click(machineToggle);
    expect(screen.getAllByText("Máy đã dừng")).toHaveLength(2);
  });

  it("rewinds an uploaded video so the same file can be replayed after it ends", async () => {
    mockAuthenticatedSession();
    vi.stubGlobal("URL", {
      createObjectURL: vi.fn(() => "blob:uploaded-video"),
      revokeObjectURL: vi.fn(),
    });
    const {container} = render(<App />);
    await screen.findByRole("heading", {name: "Live Monitor"});

    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    const video = container.querySelector("video") as HTMLVideoElement;
    Object.defineProperties(video, {
      videoWidth: {value: 1280},
      videoHeight: {value: 720},
      duration: {value: 20},
      currentTime: {value: 20, writable: true},
    });
    vi.spyOn(video, "load").mockImplementation(() => undefined);
    fireEvent.change(input, {target: {files: [new File(["video"], "shift.mp4", {type: "video/mp4"})]}});
    fireEvent.loadedMetadata(video);
    fireEvent.ended(video);

    expect(video.currentTime).toBe(0);
    expect(screen.getByRole("button", {name: "↻ Phát lại"})).toBeEnabled();
  });

  it("creates points only after the explicit Tạo vùng action", async () => {
    mockAuthenticatedSession();
    const {container} = render(<App />);
    await screen.findByRole("heading", {name: "Live Monitor"});
    const video = container.querySelector("video") as HTMLVideoElement;
    Object.defineProperties(video, {
      videoWidth: {value: 1280},
      videoHeight: {value: 720},
      duration: {value: 20}
    });
    fireEvent.loadedMetadata(video);
    const canvas = container.querySelector(".camera-scene canvas") as HTMLCanvasElement;
    vi.spyOn(canvas, "getBoundingClientRect").mockReturnValue({
      left: 0,
      top: 0,
      width: 1000,
      height: 500,
      right: 1000,
      bottom: 500,
      x: 0,
      y: 0,
      toJSON: () => ({})
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
    expect(screen.getByText((_, node) => node?.textContent === "4/4 · BẬT")).toBeInTheDocument();
  });

  it("removes a confirmed zone from the UI and persists only when configuration is saved", async () => {
    window.sessionStorage.setItem("sentinel.auth.access_token", "token-1");
    const points = [{x: 0.1, y: 0.1}, {x: 0.4, y: 0.1}, {x: 0.4, y: 0.4}, {x: 0.1, y: 0.4}];
    const zones = [
      {zone_id: "zone_1", display_name: "Vùng 1", points, machine_state: "running", enabled: true, order: 0},
      {zone_id: "zone_2", display_name: "Vùng 2", points, machine_state: "stopped", enabled: true, order: 1},
    ];
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("/auth/me")) return jsonResponse({user, expires_at: "2026-08-11T00:00:00Z"});
      if (url.includes("/ppe-requirements/")) return jsonResponse({
        camera_id: "uploaded_video",
        zone_id: "zone_01",
        profile: "hat_vest_v1",
        hat_required: false,
        vest_required: false,
        is_configured: false,
        updated_at: null,
      });
      if (url.includes("/monitoring-zones") && init?.method === "PUT") {
        return jsonResponse({camera_id: "uploaded_video", revision: 2, zones: [zones[0]], updated_at: null});
      }
      if (url.includes("/monitoring-zones")) {
        return jsonResponse({camera_id: "uploaded_video", revision: 1, zones, updated_at: null});
      }
      return jsonResponse([]);
    });
    vi.stubGlobal("fetch", fetchMock);
    const confirmRemoval = vi.spyOn(window, "confirm").mockReturnValue(false);
    const canvasLabels = new Set<string>();
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({
      clearRect: () => canvasLabels.clear(),
      beginPath: vi.fn(),
      moveTo: vi.fn(),
      lineTo: vi.fn(),
      closePath: vi.fn(),
      fill: vi.fn(),
      stroke: vi.fn(),
      arc: vi.fn(),
      setLineDash: vi.fn(),
      fillText: (label: string) => canvasLabels.add(label),
    } as unknown as CanvasRenderingContext2D);

    render(<App />);
    await screen.findByRole("heading", {name: "Live Monitor"});
    await screen.findByText("2 vùng đã cấu hình");
    expect(canvasLabels).toContain("Vùng 2");
    fireEvent.click(screen.getByRole("button", {name: /Vùng 2/}));

    fireEvent.click(screen.getByRole("button", {name: "Xóa vùng Vùng 2"}));
    expect(screen.getByText("2 vùng đã cấu hình")).toBeInTheDocument();

    confirmRemoval.mockReturnValue(true);
    fireEvent.click(screen.getByRole("button", {name: "Xóa vùng Vùng 2"}));
    expect(screen.getByText("1 vùng đã cấu hình")).toBeInTheDocument();
    expect(screen.queryByRole("button", {name: /Vùng 2/})).not.toBeInTheDocument();
    expect(canvasLabels).not.toContain("Vùng 2");
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === "PUT")).toBe(false);

    fireEvent.click(screen.getByRole("button", {name: "Lưu cấu hình vùng"}));
    await waitFor(() => {
      const saveCall = fetchMock.mock.calls.find(([, init]) => init?.method === "PUT");
      expect(saveCall).toBeDefined();
      expect(JSON.parse(String(saveCall?.[1]?.body)).zones).toEqual([zones[0]]);
    });
  });
});
