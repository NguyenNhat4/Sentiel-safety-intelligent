import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {afterEach, describe, expect, it, vi} from "vitest";
import App from "./App";

describe("Sentinel login", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows three role entry points", () => {
    render(<App />);
    expect(screen.getByRole("button", {name: /Quản lý an toàn/})).toBeInTheDocument();
    expect(screen.getByRole("button", {name: /Quản lý khu vực/})).toBeInTheDocument();
    expect(screen.getByRole("button", {name: /Mô phỏng streaming/})).toBeInTheDocument();
  });

  it("opens the existing live-monitor baseline after a safety-manager login", async () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText("Email công việc"), {target: {value: "antoan@sentinel.local"}});
    fireEvent.change(screen.getByLabelText("Mật khẩu"), {target: {value: "Sentinel123!"}});
    fireEvent.click(screen.getByRole("button", {name: "Đăng nhập"}));
    await waitFor(() => expect(screen.getByRole("heading", {name: "Live Monitor"})).toBeInTheDocument());
  });

  it("shows an error for invalid mock credentials", async () => {
    render(<App />);
    fireEvent.change(screen.getByLabelText("Email công việc"), {target: {value: "wrong@example.com"}});
    fireEvent.change(screen.getByLabelText("Mật khẩu"), {target: {value: "wrong-password"}});
    fireEvent.click(screen.getByRole("button", {name: "Đăng nhập"}));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Email hoặc mật khẩu không chính xác."));
  });
});
