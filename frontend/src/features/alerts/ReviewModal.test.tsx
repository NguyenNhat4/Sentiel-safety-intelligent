import {fireEvent, render, screen} from "@testing-library/react";
import {describe, expect, it, vi} from "vitest";
import {ReviewModal} from "./ReviewModal";

describe("ReviewModal", () => {
  it("does not render when isOpen is false", () => {
    render(
      <ReviewModal
        isOpen={false}
        onClose={vi.fn()}
        timer="00:00"
        reviewSaving={false}
        alertTitle="Test Title"
        alertSummary="Test Summary"
        onReview={vi.fn()}
      />
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders modal dialog and handles user decisions when isOpen is true", () => {
    const onReview = vi.fn();
    const onClose = vi.fn();

    render(
      <ReviewModal
        isOpen={true}
        onClose={onClose}
        snapshot="data:image/jpeg;base64,1234"
        timer="00:12"
        reviewSaving={false}
        alertTitle="Phát hiện người trong vùng cấm"
        alertSummary="Video đã dừng để xác minh."
        onReview={onReview}
      />
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Phát hiện người trong vùng cấm")).toBeInTheDocument();
    expect(screen.getByText("00:12")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", {name: /Vi phạm thực tế/}));
    expect(onReview).toHaveBeenLastCalledWith("acknowledged");

    fireEvent.click(screen.getByRole("button", {name: /Bình thường \/ báo sai/}));
    expect(onReview).toHaveBeenLastCalledWith("false_alarm");

    fireEvent.click(screen.getByRole("button", {name: "Đóng pop-up"}));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("draws the frame's people and object boxes over a review snapshot", () => {
    render(
      <ReviewModal
        isOpen
        onClose={vi.fn()}
        snapshot="data:image/jpeg;base64,1234"
        people={[{
          bbox: [10, 15, 80, 90], confidence: 0.9, inside_zone: true,
          ppe: {
            hat: {status: "unknown", confidence: null},
            vest: {status: "unknown", confidence: null},
          },
          missing_required_ppe: [],
        }]}
        detections={[
          {class_id: 0, class_name: "hat", bbox: [20, 20, 50, 50], confidence: 0.8, person_index: 0},
          {class_id: 4, class_name: "vest", bbox: [25, 25, 45, 45], confidence: 0.8, person_index: 0},
          {class_id: 3, class_name: "person", bbox: [10, 15, 80, 90], confidence: 0.9, person_index: 0},
        ]}
        timer="00:12"
        reviewSaving={false}
        alertTitle="Review"
        alertSummary="Summary"
        onReview={vi.fn()}
      />
    );

    const image = screen.getByRole("img", {name: "Khung hình vi phạm cần xác minh"});
    Object.defineProperties(image, {
      naturalWidth: {configurable: true, value: 100},
      naturalHeight: {configurable: true, value: 100},
    });
    fireEvent.load(image);

    expect(screen.getByLabelText("Bounding box của khung hình review")).toBeInTheDocument();
    expect(screen.getAllByTestId("snapshot-box")).toHaveLength(3);
  });

  it("draws configured zones over a review snapshot", () => {
    render(
      <ReviewModal
        isOpen
        onClose={vi.fn()}
        snapshot="data:image/jpeg;base64,1234"
        zones={[{
          zone_id: "zone_01", display_name: "Khu vực máy dập", enabled: true, order: 0,
          points: [{x: 0.1, y: 0.2}, {x: 0.8, y: 0.2}, {x: 0.8, y: 0.9}, {x: 0.1, y: 0.9}],
        }]}
        people={[{
          bbox: [10, 15, 80, 90], confidence: 0.9, inside_zone: true,
          ppe: {hat: {status: "unknown", confidence: null}, vest: {status: "unknown", confidence: null}},
          missing_required_ppe: [], active_violations: [{occurrence_id: "occ-1", rule_key: "zone_intrusion", zone_id: "zone_01", is_new: true}],
        }]}
        timer="00:12"
        reviewSaving={false}
        alertTitle="Review"
        alertSummary="Summary"
        onReview={vi.fn()}
      />
    );

    const image = screen.getByRole("img", {name: "Khung hình vi phạm cần xác minh"});
    Object.defineProperties(image, {
      naturalWidth: {configurable: true, value: 100},
      naturalHeight: {configurable: true, value: 100},
    });
    fireEvent.load(image);

    expect(screen.getByTestId("snapshot-zone")).toBeInTheDocument();
    expect(screen.getByText("Khu vực máy dập")).toBeInTheDocument();
  });
});
