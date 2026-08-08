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
          bbox: [10, 15, 80, 90], confidence: 0.9, inside_zone: true, safety_shirt: false,
          ppe: {
            helmet: {status: "unknown", confidence: null},
            safety_glasses: {status: "unknown", confidence: null},
            gloves: {status: "unknown", confidence: null},
          },
          missing_required_ppe: [],
        }]}
        detections={[{class_id: 10, class_name: "helmet", bbox: [20, 20, 50, 50], confidence: 0.8, person_index: 0}]}
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
    expect(screen.getAllByTestId("snapshot-box")).toHaveLength(2);
  });
});
