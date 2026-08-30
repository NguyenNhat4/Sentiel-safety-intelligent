import {afterEach, describe, expect, it, vi} from "vitest";
import {deleteUser, disconnectTelegramLink, getCurrentUser, listUsers, login, logout, updateUserRole} from "./auth";

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
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({access_token: "token-1", token_type: "bearer", user}), {status: 200}));
    vi.stubGlobal("fetch", fetchMock);
    await expect(login({email: user.email, password: "Sentinel123!"})).resolves.toMatchObject({user});
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/auth/login", expect.objectContaining({method: "POST"}));
    expect(window.sessionStorage.getItem("sentinel.auth.access_token")).toBe("token-1");
  });

  it("clears an invalid persisted session", async () => {
    window.sessionStorage.setItem("sentinel.auth.access_token", "expired-token");
    vi.stubGlobal("fetch", vi.fn(async () => new Response("Unauthorized", {status: 401})));
    await expect(getCurrentUser()).resolves.toBeNull();
    expect(window.sessionStorage.getItem("sentinel.auth.access_token")).toBeNull();
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
