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

  it("displays the backend-annotated snapshot without browser overlays", () => {
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
        timer="00:12"
        reviewSaving={false}
        alertTitle="Review"
        alertSummary="Summary"
        onReview={vi.fn()}
      />
    );

    expect(screen.getByRole("img", {name: "Khung hình vi phạm cần xác minh"})).toHaveAttribute("src", "data:image/jpeg;base64,1234");
    expect(screen.queryByTestId("snapshot-box")).not.toBeInTheDocument();
    expect(screen.queryByTestId("snapshot-zone")).not.toBeInTheDocument();
    expect(screen.queryByRole("graphics-document")).not.toBeInTheDocument();
  });
});
