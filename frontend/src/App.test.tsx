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
    if (url.includes("/camera-configurations/cam_")) return jsonResponse({camera_id: url.match(/cam_[1-4]/)?.[0], revision: 0, asset_id: null, machine_state: "stopped", zones: [], updated_at: null});
    if (url.includes("/camera-configurations") || url.includes("/media-assets") || url.includes("/camera-sessions")) return jsonResponse([]);
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
    expect(screen.getByText("Tài khoản dùng thử")).toBeInTheDocument();
    expect(screen.getByText("admin@sentinel.local")).toBeInTheDocument();
    expect(screen.queryByText("Mật khẩu chung:")).not.toBeInTheDocument();
  });

  it("fills the login form from a demo account shortcut", async () => {
    vi.stubGlobal("fetch", vi.fn());
    render(<App />);
    await screen.findByRole("button", {name: /Đăng nhập/});
    fireEvent.click(screen.getByRole("button", {name: "Dùng tài khoản admin@sentinel.local"}));
    expect(screen.getByLabelText("Email công việc")).toHaveValue("admin@sentinel.local");
    expect(screen.getByLabelText("Mật khẩu")).toHaveValue("Sentinel123!");
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

    await screen.findByRole("button", {name: /Thư viện media/});
    expect(screen.getByRole("button", {name: /Quan sát hệ thống/})).toBeInTheDocument();
    expect(screen.queryByRole("button", {name: /Cấu hình camera/})).not.toBeInTheDocument();
    expect(screen.getByRole("button", {name: /Live monitor/})).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", {name: /Quản trị hệ thống/}));
    expect(await screen.findByRole("tab", {name: "Tài khoản"})).toBeInTheDocument();
    expect(screen.getByRole("tab", {name: "Vai trò & quyền"})).toBeInTheDocument();
    expect(screen.getByRole("tab", {name: "Bảo mật"})).toBeInTheDocument();
    expect(screen.getByRole("button", {name: /Thư viện media/})).toBeInTheDocument();
    expect(screen.getByRole("button", {name: /Quản trị hệ thống/})).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", {name: /Live monitor/}));
    expect(await screen.findByRole("heading", {name: "Live Monitor"})).toBeInTheDocument();
    expect(screen.getByRole("heading", {name: "Camera 1"})).toBeInTheDocument();
    expect(screen.getByRole("button", {name: "Chạy mô phỏng"})).toBeInTheDocument();
    expect(screen.getByRole("button", {name: "Cấu hình Camera 1"})).toBeInTheDocument();
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
    expect(screen.queryByRole("button", {name: /Quan sát hệ thống/})).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", {name: /Nhật ký vi phạm/}));
    await waitFor(() => expect(screen.getByText("Chưa có vi phạm nào được xác nhận.")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", {name: /Live monitor/}));
    expect(await screen.findAllByText("Bấm vào đây để cấu hình")).toHaveLength(4);
    expect(screen.getByText(/Đã upload video.*bấm vào camera thêm một lần nữa để mở cấu hình/i)).toBeInTheDocument();
    expect(screen.queryByText("Tách riêng vi phạm thực tế và báo sai, nhưng giữ cả hai để truy vết quyết định.")).not.toBeInTheDocument();
  });

  it("opens the exact internal camera configuration without a sidebar item", async () => {
    mockAuthenticatedSession();
    render(<App />);
    await screen.findByRole("heading", {name: "Live Monitor"});
    expect(await screen.findByRole("heading", {name: "Camera 1"})).toBeInTheDocument();
    expect(screen.getByRole("heading", {name: "Camera 4"})).toBeInTheDocument();
    expect(screen.queryByRole("button", {name: /Cấu hình camera/})).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", {name: "Cấu hình Camera 2"}));
    expect(await screen.findByRole("heading", {name: "Cấu hình Camera 2"})).toBeInTheDocument();
    expect(screen.queryAllByText("Cấu hình Camera 2")).toHaveLength(1);
    expect(screen.queryByRole("combobox", {name: "Chọn camera"})).not.toBeInTheDocument();
  });

  it("does not render the removed local video upload controls", async () => {
    mockAuthenticatedSession();
    const {container} = render(<App />);
    await screen.findByRole("heading", {name: "Live Monitor"});
    expect(container.querySelector('input[type="file"]')).not.toBeInTheDocument();
    expect(container.querySelector("video")).not.toBeInTheDocument();
  });

});
