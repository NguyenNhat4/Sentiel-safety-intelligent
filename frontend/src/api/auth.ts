import type {LoginRequest, LoginResponse, UserRole} from "../types";

const MOCK_ACCOUNTS: Record<string, {password: string; role: UserRole; full_name: string; role_label: string}> = {
  "antoan@sentinel.local": {password: "Sentinel123!", role: "safety_manager", full_name: "Nguyễn Anh Tuấn", role_label: "Quản lý an toàn"},
  "khuvuc@sentinel.local": {password: "Sentinel123!", role: "area_manager", full_name: "Trần Minh Hà", role_label: "Quản lý khu vực"},
  "mophong@sentinel.local": {password: "Sentinel123!", role: "simulation_operator", full_name: "Lê Gia Huy", role_label: "Vận hành mô phỏng"}
};

/** Temporary client-side mock. Replace its body with POST /api/v1/auth/login when auth is available. */
export async function login(credentials: LoginRequest): Promise<LoginResponse> {
  await new Promise<void>((resolve) => window.setTimeout(resolve, 350));
  const account = MOCK_ACCOUNTS[credentials.email.trim().toLowerCase()];
  if (!account || account.password !== credentials.password) throw new Error("Email hoặc mật khẩu không chính xác.");
  return {access_token: `mock-token-${account.role}`, token_type: "bearer", user: {id: account.role, full_name: account.full_name, email: credentials.email.trim().toLowerCase(), role: account.role, role_label: account.role_label}};
}

/** Temporary local logout. A real implementation will revoke/clear the stored session. */
export async function logout(): Promise<void> { await Promise.resolve(); }
