import {fireEvent, render, screen} from "@testing-library/react";
import {describe, expect, it, vi} from "vitest";
import {AlertPanel} from "./AlertPanel";
import type {MonitorView} from "../monitor/use-monitor";

const view: MonitorView = {
  violation: true, alertTitle: "Cần xác minh", severity: "VIOLATE", alertSummary: "Tóm tắt",
  reviewMessage: "Đang chờ", eventStatus: "Chưa lưu", confidenceLabel: "VIOLATE", confidenceWidth: "100%",
  zoneRule: {yes: true, text: "Trong vùng", badge: "YES"},
  machineRule: {yes: true, text: "Đang chạy", badge: "ON"},
  ppeRule: {yes: false, text: "Thiếu áo", badge: "MISS"}
};

describe("AlertPanel", () => {
  it("exposes both Human-in-the-Loop decisions when review is pending", () => {
    const onReview = vi.fn();
    render(<AlertPanel view={view} reviewPending reviewSaving={false} timer="00:03" onReview={onReview} />);
    fireEvent.click(screen.getByRole("button", {name: /Vi phạm thực tế/}));
    fireEvent.click(screen.getByRole("button", {name: /báo sai/}));
    expect(onReview).toHaveBeenNthCalledWith(1, "acknowledged");
    expect(onReview).toHaveBeenNthCalledWith(2, "false_alarm");
  });
});
