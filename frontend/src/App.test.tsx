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

afterEach(() => {
  window.sessionStorage.clear();
  vi.restoreAllMocks();
});

describe("Sentinel authentication", () => {
  it("shows the login page when there is no saved session", async () => {
    vi.stubGlobal("fetch", vi.fn());
    render(<App />);
    await waitFor(() => expect(screen.getByRole("button", {name: /\u0110\u0103ng nh\u1eadp/})).toBeInTheDocument());
  });

  it("opens the application after the API accepts credentials", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/auth/login")) {
        return new Response(JSON.stringify({access_token: "token-1", token_type: "bearer", user}), {status: 200});
      }
      return new Response(JSON.stringify({user, expires_at: "2026-08-11T00:00:00Z"}), {status: 200});
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);
    await screen.findByRole("button", {name: /\u0110\u0103ng nh\u1eadp/});
    fireEvent.change(screen.getByLabelText(/Email/), {target: {value: user.email}});
    fireEvent.change(screen.getByLabelText(/M\u1eadt kh\u1ea9u/), {target: {value: "Sentinel123!"}});
    fireEvent.click(screen.getByRole("button", {name: /\u0110\u0103ng nh\u1eadp/}));
    await waitFor(() => expect(screen.getByRole("heading", {name: "Live Monitor"})).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/auth/login", expect.objectContaining({method: "POST"}));
  });

  it("opens the tabbed system administration page for a system admin", async () => {
    const admin = {...user, id: "admin-1", email: "admin@sentinel.local", role: "system_admin" as const, role_label: "Quản trị hệ thống"};
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/auth/login")) return new Response(JSON.stringify({access_token: "admin-token", token_type: "bearer", user: admin}), {status: 200});
      if (String(input).includes("/auth/users")) return new Response(JSON.stringify([{...admin, is_active: true, created_at: "2026-08-11T00:00:00Z"}]), {status: 200});
      return new Response(JSON.stringify({user: admin, expires_at: "2026-08-11T00:00:00Z"}), {status: 200});
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
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      access_token: "first-login-token",
      token_type: "bearer",
      user: firstLoginUser
    }), {status: 200})));
    render(<App />);
    await screen.findByRole("button", {name: /Đăng nhập/});
    fireEvent.change(screen.getByLabelText(/Email/), {target: {value: firstLoginUser.email}});
    fireEvent.change(screen.getByLabelText(/^Mật khẩu$/), {target: {value: "Temporary123!"}});
    fireEvent.click(screen.getByRole("button", {name: /Đăng nhập/}));

    expect(await screen.findByRole("heading", {name: "Lần đăng nhập đầu tiên"})).toBeInTheDocument();
    expect(screen.queryByRole("heading", {name: "Live Monitor"})).not.toBeInTheDocument();
  });
});
