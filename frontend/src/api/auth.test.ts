import {afterEach, describe, expect, it, vi} from "vitest";
import {deleteUser, disconnectTelegramLink, getCurrentUser, listUsers, login, logout, updateUserRole} from "./auth";
import {peekQuery, setQueryData} from "./query-cache";

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

describe("authentication transport", () => {
  it("stores the API token after a successful login", async () => {
    setQueryData("events:area", [{id: 1}]);
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({access_token: "token-1", token_type: "bearer", user}), {status: 200}));
    vi.stubGlobal("fetch", fetchMock);
    await expect(login({email: user.email, password: "Sentinel123!"})).resolves.toMatchObject({user});
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/auth/login", expect.objectContaining({method: "POST"}));
    expect(window.sessionStorage.getItem("sentinel.auth.access_token")).toBe("token-1");
    expect(peekQuery("events:area")).toBeUndefined();
  });

  it("clears an invalid persisted session", async () => {
    setQueryData("media-assets:list", [{id: "private"}]);
    window.sessionStorage.setItem("sentinel.auth.access_token", "expired-token");
    vi.stubGlobal("fetch", vi.fn(async () => new Response("Unauthorized", {status: 401})));
    await expect(getCurrentUser()).resolves.toBeNull();
    expect(window.sessionStorage.getItem("sentinel.auth.access_token")).toBeNull();
    expect(peekQuery("media-assets:list")).toBeUndefined();
  });

  it("preserves the local session and cache on temporary auth storage failure", async () => {
    window.sessionStorage.setItem("sentinel.auth.access_token", "token-1");
    setQueryData("media-assets:list", [{id: "cached"}]);
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({detail: "Authentication storage is unavailable"}), {status: 503})));
    await expect(getCurrentUser()).rejects.toThrow("Authentication storage is unavailable");
    expect(window.sessionStorage.getItem("sentinel.auth.access_token")).toBe("token-1");
    expect(peekQuery("media-assets:list")).toEqual([{id: "cached"}]);
  });

  it("revokes the server session and clears the local token", async () => {
    window.sessionStorage.setItem("sentinel.auth.access_token", "token-1");
    const fetchMock = vi.fn(async () => new Response(null, {status: 204}));
    vi.stubGlobal("fetch", fetchMock);
    await logout();
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/auth/logout", {
      method: "POST",
      headers: {Authorization: "Bearer token-1"}
    });
    expect(window.sessionStorage.getItem("sentinel.auth.access_token")).toBeNull();
  });

  it("clears local session data even when server logout fails", async () => {
    window.sessionStorage.setItem("sentinel.auth.access_token", "token-1");
    setQueryData("camera-configurations:list", [{camera_id: "cam_1"}]);
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("offline"); }));
    await expect(logout()).rejects.toThrow("offline");
    expect(window.sessionStorage.getItem("sentinel.auth.access_token")).toBeNull();
    expect(peekQuery("camera-configurations:list")).toBeUndefined();
  });

  it("sends the bearer token for system administration requests", async () => {
    window.sessionStorage.setItem("sentinel.auth.access_token", "admin-token");
    const managedUser = {...user, is_active: true, created_at: "2026-08-11T00:00:00Z"};
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === "DELETE") return new Response(null, {status: 204});
      return new Response(JSON.stringify(String(input).endsWith("/role") ? managedUser : [managedUser]), {status: 200});
    });
    vi.stubGlobal("fetch", fetchMock);

    await listUsers("Safety", "safety_manager");
    await updateUserRole(user.id, {role: "area_manager"});
    await disconnectTelegramLink(user.id);
    await deleteUser(user.id);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/users?query=Safety&role=safety_manager",
      expect.objectContaining({headers: expect.objectContaining({Authorization: "Bearer admin-token"})})
    );
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/auth/users/${user.id}/telegram-link`,
      expect.objectContaining({method: "DELETE", headers: expect.objectContaining({Authorization: "Bearer admin-token"})})
    );
    expect(fetchMock).toHaveBeenCalledWith(
      `/api/v1/auth/users/${user.id}`,
      expect.objectContaining({method: "DELETE", headers: expect.objectContaining({Authorization: "Bearer admin-token"})})
    );
  });
});
