import {act, fireEvent, render, screen} from "@testing-library/react";
import {beforeEach, describe, expect, it, vi} from "vitest";
import {loadEventDetail} from "../../api/events";
import type {SafetyEventUpdate} from "../../api/events";
import type {EventDetail} from "../../types";
import {EventDetailDialog} from "./EventDetailDialog";

let eventUpdateHandler: (update: SafetyEventUpdate) => void = () => undefined;
vi.mock("../../api/events", () => ({
  loadEventDetail: vi.fn(),
  subscribeToSafetyEventUpdates: (listener: (update: SafetyEventUpdate) => void) => {
    eventUpdateHandler = listener;
    return vi.fn();
  },
}));

const detail: EventDetail = {
  id: 42,
  timestamp: "2026-08-15T03:05:32Z",
  zone_id: "zone_01",
  camera_id: "uploaded_video",
  event_type: "missing_ppe_and_intrusion",
  severity: "high",
  status: "acknowledged",
  acknowledged_by: "Nguyễn Anh Tuấn",
  snapshot_path: "/snapshots/event-42.jpg",
  decision_context: {
    schema_version: "decision_context_v1",
    rule: {
      rule_version: "safety_rule_v1",
      violation_frame_count: 4,
      triggered_rule_keys: ["zone_intrusion:zone_01", "missing_ppe:hat"],
      ppe_profile: "hat_vest_v1",
      ppe_requirements: {profile: "hat_vest_v1", hat_required: true, vest_required: false},
    },
    scene: {
      camera_id: "uploaded_video",
      zone_id: "zone_01",
      zone_name: "Máy dập A",
      frame_id: 12,
      video_timestamp_seconds: 6,
      machine_state: "running",
      zone_revision: 3,
      zone_points: [{x: 0.2, y: 0.2}, {x: 0.8, y: 0.2}, {x: 0.8, y: 0.8}, {x: 0.2, y: 0.8}],
      people: [{
        track_id: 7,
        bbox: [40, 10, 80, 100],
        confidence: 0.91,
        inside_zone: true,
        ppe: {
          hat: {status: "missing", confidence: null},
          vest: {status: "present", confidence: 0.88},
        },
        missing_required_ppe: ["hat"],
      }],
      detections: [],
    },
    system_decision: {
      result: "violate",
      reason_codes: ["zone_intrusion", "missing_required_ppe:hat"],
      severity: "high",
    },
    human_review: {
      outcome: "actual_violation",
      actor_user_id: "user-1",
      actor_name: "Nguyễn Anh Tuấn",
      actor_role: "safety_manager",
      reviewed_at: "2026-08-15T03:05:40Z",
    },
  },
  summary: {
    text: "Tại Vùng 1, hệ thống phát hiện 1 người và đánh dấu là vi phạm do xâm nhập vùng. Nguyễn Anh Tuấn xác nhận đây là vi phạm thực tế.",
    source: "deterministic",
    context_schema_version: "decision_context_v1",
  },
};

describe("EventDetailDialog", () => {
  beforeEach(() => {
    eventUpdateHandler = () => undefined;
    vi.mocked(loadEventDetail).mockResolvedValue(detail);
  });

  it("presents the persisted AI to rule to HITL audit chain", async () => {
    render(<EventDetailDialog eventId={42} onClose={vi.fn()} />);

    expect(screen.getByRole("status")).toHaveTextContent("Đang tải");
    expect(await screen.findByRole("dialog", {name: "Chi tiết sự kiện #42"})).toBeInTheDocument();
    expect(screen.getByRole("heading", {name: "AI quan sát"})).toBeInTheDocument();
    expect(screen.getByText(/91%/)).toBeInTheDocument();
    expect(screen.getByRole("heading", {name: "Rule quyết định"})).toBeInTheDocument();
    expect(screen.getByText(/safety_rule_v1/)).toBeInTheDocument();
    expect(screen.getByText("Thiếu mũ bảo hộ")).toBeInTheDocument();
    expect(screen.queryByText("missing_ppe:hat")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", {name: "Human review"})).toBeInTheDocument();
    expect(screen.queryByText("BƯỚC 1")).not.toBeInTheDocument();
    expect(screen.queryByText("BƯỚC 2")).not.toBeInTheDocument();
    expect(screen.queryByText("BƯỚC 3")).not.toBeInTheDocument();
    expect(screen.getAllByText(/Nguyễn Anh Tuấn/)).toHaveLength(2);
    expect(screen.getByText(/Nguồn: Mẫu xác định/)).toBeInTheDocument();
    expect(screen.getByText("xâm nhập vùng")).toHaveProperty("tagName", "STRONG");
    expect(screen.getAllByText("Nguyễn Anh Tuấn").every(element => element.tagName === "STRONG")).toBe(true);
    const image = screen.getByRole("img", {name: "Snapshot đã làm mờ của sự kiện 42"});
    Object.defineProperties(image, {naturalWidth: {configurable: true, value: 100}, naturalHeight: {configurable: true, value: 100}});
    fireEvent.load(image);
    expect(screen.getByTestId("snapshot-zone")).toBeInTheDocument();
    expect(screen.getAllByText("Máy dập A").length).toBeGreaterThanOrEqual(2);
    expect(screen.queryByTestId("snapshot-box")).not.toBeInTheDocument();
  });

  it("shows a limited-audit explanation for legacy events", async () => {
    vi.mocked(loadEventDetail).mockResolvedValue({...detail, decision_context: null});

    render(<EventDetailDialog eventId={42} onClose={vi.fn()} />);

    expect(await screen.findByText(/Audit hạn chế/)).toBeInTheDocument();
    expect(screen.getByText(/phiên bản hệ thống cũ/)).toBeInTheDocument();
  });

  it("closes from the explicitly labelled button", async () => {
    const onClose = vi.fn();
    render(<EventDetailDialog eventId={42} onClose={onClose} />);
    await screen.findByRole("dialog");

    fireEvent.click(screen.getByRole("button", {name: "Đóng chi tiết sự kiện"}));

    expect(onClose).toHaveBeenCalledOnce();
  });

  it("reloads an open detail when the same event is reviewed elsewhere", async () => {
    vi.mocked(loadEventDetail)
      .mockResolvedValueOnce(detail)
      .mockResolvedValueOnce({...detail, summary: {...detail.summary, text: "Audit đã cập nhật"}});
    render(<EventDetailDialog eventId={42} onClose={vi.fn()} />);
    await screen.findByRole("dialog");
    const callsBeforeUpdate = vi.mocked(loadEventDetail).mock.calls.length;

    act(() => eventUpdateHandler({eventIds: [42], cameraIds: ["uploaded_video"]}));

    expect(await screen.findByText("Audit đã cập nhật")).toBeInTheDocument();
    expect(loadEventDetail).toHaveBeenCalledTimes(callsBeforeUpdate + 1);
  });
});
