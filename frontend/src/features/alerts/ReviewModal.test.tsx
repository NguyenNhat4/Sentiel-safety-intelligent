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
});
