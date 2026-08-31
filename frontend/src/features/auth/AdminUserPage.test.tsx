import {fireEvent, render, screen} from "@testing-library/react";
import {beforeEach, describe, expect, it, vi} from "vitest";
import {listUsers} from "../../api/auth";
import type {ManagedUser} from "../../types";
import {AdminUserPage} from "./AdminUserPage";

vi.mock("../../api/auth", () => ({
  changePassword: vi.fn(),
  completeTelegramLink: vi.fn(),
  createUser: vi.fn(),
  deleteUser: vi.fn(),
  disconnectTelegramLink: vi.fn(),
  listUsers: vi.fn(),
  startTelegramLink: vi.fn(),
  updateUserRole: vi.fn()
}));

const linkedUser: ManagedUser = {
  id: "admin-1",
  full_name: "System Admin",
  email: "admin@sentinel.local",
  role: "system_admin",
  role_label: "Quản trị hệ thống",
  must_change_password: false,
  telegram_chat_id: "123456",
  telegram_username: "sentinel_admin",
  is_active: true,
  created_at: "2026-08-31T00:00:00Z"
};

const disconnectedUser: ManagedUser = {
  ...linkedUser,
  id: "manager-1",
  full_name: "Safety Manager",
  email: "antoan@sentinel.local",
  role: "safety_manager",
  role_label: "Cán bộ an toàn",
  telegram_chat_id: null,
  telegram_username: null
};

beforeEach(() => {
  vi.mocked(listUsers).mockResolvedValue([linkedUser, disconnectedUser]);
});

describe("Telegram controls", () => {
  it("shows exactly the action appropriate for the selected account state", async () => {
    render(<AdminUserPage currentUser={linkedUser} onLogout={vi.fn()} />);

    fireEvent.click(await screen.findByRole("tab", {name: "Vai trò & quyền"}));

    expect(screen.getByRole("button", {name: "Ngắt liên kết Telegram"})).toBeInTheDocument();
    expect(screen.queryByText("Liên kết Telegram")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", {name: /Safety Manager/}));

    expect(screen.getByText("Liên kết Telegram")).toBeInTheDocument();
    expect(screen.getByRole("button", {name: "Tạo QR liên kết"})).toBeInTheDocument();
    expect(screen.getByRole("button", {name: "Tạo link liên kết"})).toBeInTheDocument();
    expect(screen.queryByRole("button", {name: "Ngắt liên kết Telegram"})).not.toBeInTheDocument();
  });
});
