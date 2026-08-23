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
  ppeRule: {yes: false, text: "Thiếu áo", badge: "MISS"},
};

describe("AlertPanel", () => {
  it("opens review only after an operator selects a Human-in-the-Loop log", () => {
    const onOpenModal = vi.fn();
    render(<AlertPanel view={view} reviewPending timer="00:03" onOpenModal={onOpenModal}
      hitlLogs={[{id: "ppe-1", tone: "warning", title: "Thiếu áo phản quang", detail: "Người #1", reviewStatus: "pending", hasNewOccurrence: true}]} />);

    fireEvent.click(screen.getByRole("button", {name: /Thiếu áo phản quang/}));
    expect(onOpenModal).toHaveBeenCalledTimes(1);
    expect(onOpenModal).toHaveBeenCalledWith("ppe-1");
    expect(screen.queryByRole("button", {name: /Vi phạm thực tế/})).not.toBeInTheDocument();
  });

  it("lists selected PPE detections accurately", () => {
    const detections: ModelDetection[] = [
      {class_id: 3, class_name: "person", bbox: [10, 10, 50, 50], confidence: 0.88, person_index: 0},
      {class_id: 0, class_name: "hat", bbox: [20, 20, 40, 40], confidence: 0.94, person_index: null},
      {class_id: 4, class_name: "vest", bbox: [30, 20, 45, 40], confidence: 0.92, person_index: null},
    ];
    render(<AlertPanel view={view} reviewPending={false} timer="00:05" detections={detections}
      people={[{track_id: 2, bbox: [0, 0, 100, 120], confidence: 0.95, inside_zone: false,
        ppe: {hat: {status: "present", confidence: 0.94}, vest: {status: "present", confidence: 0.92}}, missing_required_ppe: []}]} />);

    expect(screen.getByText("OBJECT DETECTIONS GROUPED BY PERSON (3)")).toBeInTheDocument();
    expect(screen.getByText("PERSON #2")).toBeInTheDocument();
    expect(screen.getByText("HAT")).toBeInTheDocument();
    expect(screen.getByText("VEST")).toBeInTheDocument();
  });
});
