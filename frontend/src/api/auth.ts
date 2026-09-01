import type {
  AuthenticatedUser,
  CreateUserRequest,
  LoginRequest,
  LoginResponse,
  ManagedUser,
  PasswordChangeRequest,
  UserRole,
  UserRoleUpdate
} from "../types";
import type {TelegramLinkComplete, TelegramLinkStart} from "../types";
import {apiUrl} from "./config";
import {clearQueryCache} from "./query-cache";

const TOKEN_STORAGE_KEY = "sentinel.auth.access_token";

export function getAccessToken(): string | null {
  const token = window.sessionStorage.getItem(TOKEN_STORAGE_KEY);
  if (!token) clearQueryCache();
  return token;
}

export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  clearQueryCache();
  const response = await fetch(apiUrl("/auth/login"), {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(credentials)
  });
  if (!response.ok) throw new Error(await readErrorMessage(response, "Khong the dang nhap"));
  const result = await response.json() as LoginResponse;
  window.sessionStorage.setItem(TOKEN_STORAGE_KEY, result.access_token);
  return result;
}

export async function getCurrentUser(): Promise<AuthenticatedUser | null> {
  const token = getAccessToken();
  if (!token) return null;
  const response = await fetch(apiUrl("/auth/me"), {headers: {Authorization: `Bearer ${token}`}});
  if (response.status === 401 || response.status === 403) {
    window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    clearQueryCache();
    return null;
  }
  if (!response.ok) throw new Error(await readErrorMessage(response, "Không thể kiểm tra phiên đăng nhập"));
  return (await response.json() as {user: AuthenticatedUser}).user;
}

export async function logout(): Promise<void> {
  const token = getAccessToken();
  try {
    if (token) await fetch(apiUrl("/auth/logout"), {method: "POST", headers: {Authorization: `Bearer ${token}`}});
  } finally {
    window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    clearQueryCache();
  }
}

export async function listUsers(query = "", role: UserRole | "" = ""): Promise<ManagedUser[]> {
  const params = new URLSearchParams();
  if (query.trim()) params.set("query", query.trim());
  if (role) params.set("role", role);
  return authenticatedRequest<ManagedUser[]>(`/auth/users${params.size ? `?${params.toString()}` : ""}`);
}

export function createUser(payload: CreateUserRequest): Promise<ManagedUser> {
  return authenticatedRequest<ManagedUser>("/auth/users", {method: "POST", body: JSON.stringify(payload)});
}

export function updateUserRole(userId: string, payload: UserRoleUpdate): Promise<ManagedUser> {
  return authenticatedRequest<ManagedUser>(`/auth/users/${encodeURIComponent(userId)}/role`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function changePassword(userId: string, payload: PasswordChangeRequest): Promise<AuthenticatedUser> {
  return authenticatedRequest<AuthenticatedUser>(`/auth/users/${encodeURIComponent(userId)}/password`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function changeOwnPassword(payload: PasswordChangeRequest): Promise<AuthenticatedUser> {
  return authenticatedRequest<AuthenticatedUser>("/auth/password", {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export function deleteUser(userId: string): Promise<void> {
  return authenticatedRequest<void>(`/auth/users/${encodeURIComponent(userId)}`, {method: "DELETE"});
}

export function startTelegramLink(userId: string): Promise<TelegramLinkStart> {
  return authenticatedRequest<TelegramLinkStart>(`/auth/users/${encodeURIComponent(userId)}/telegram-link`, {method: "POST"});
}

export function completeTelegramLink(userId: string): Promise<TelegramLinkComplete> {
  return authenticatedRequest<TelegramLinkComplete>(`/auth/users/${encodeURIComponent(userId)}/telegram-link/complete`, {method: "POST"});
}

export function disconnectTelegramLink(userId: string): Promise<ManagedUser> {
  return authenticatedRequest<ManagedUser>(`/auth/users/${encodeURIComponent(userId)}/telegram-link`, {method: "DELETE"});
}

async function authenticatedRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAccessToken();
  if (!token) throw new Error("Phiên đăng nhập đã hết hạn.");
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: {"Content-Type": "application/json", Authorization: `Bearer ${token}`, ...init.headers}
  });
  if (!response.ok) throw new Error(await readErrorMessage(response, "Không thể hoàn tất yêu cầu"));
  return response.status === 204 ? undefined as T : response.json() as Promise<T>;
}

async function readErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json() as {detail?: string};
    return body.detail || `${fallback} (HTTP ${response.status})`;
  } catch {
    return `${fallback} (HTTP ${response.status})`;
  }
}
