import {fireEvent, render, screen} from "@testing-library/react";
import {describe, expect, it, vi} from "vitest";
import {AlertPanel} from "./AlertPanel";
import type {ModelDetection} from "../../types";
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

  it("renders total detections list and triggers open review modal", () => {
    const onReview = vi.fn();
    const onOpenModal = vi.fn();
    const detections: ModelDetection[] = [
      {class_id: 14, class_name: "shoes", bbox: [10, 10, 50, 50], confidence: 0.88, person_index: 0},
      {class_id: 10, class_name: "helmet", bbox: [20, 20, 40, 40], confidence: 0.94, person_index: null},
    ];

    render(
      <AlertPanel
        view={view}
        reviewPending
        reviewSaving={false}
        detections={detections}
        timer="00:05"
        onReview={onReview}
        onOpenModal={onOpenModal}
      />
    );

    expect(screen.getByText("OBJECT DETECTIONS GROUPED BY PERSON (2)")).toBeInTheDocument();
    expect(screen.getByText("SHOES")).toBeInTheDocument();
    expect(screen.getByText("HELMET")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", {name: /Mở Pop-up xác minh/}));
    expect(onOpenModal).toHaveBeenCalledTimes(1);
  });
});
