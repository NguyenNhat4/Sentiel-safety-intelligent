import {describe, expect, it} from "vitest";
import {detectionLabel, findPointAt, getDetectionColor, isDisplayedPpeDetection, normalizedPointerPosition, requiredPpeBadges} from "./canvas";

describe("monitor Canvas coordinates", () => {
  it("normalizes and clamps pointer coordinates", () => {
    const rect = {left: 100, top: 50, width: 400, height: 200};
    expect(normalizedPointerPosition(300, 150, rect)).toEqual({x: 0.5, y: 0.5});
    expect(normalizedPointerPosition(0, 400, rect)).toEqual({x: 0, y: 1});
  });

  it("selects a point only inside the pixel hit radius", () => {
    const points = [{x: 0.25, y: 0.5}];
    expect(findPointAt(points, {x: 0.27, y: 0.5}, {width: 400, height: 200})).toBe(0);
    expect(findPointAt(points, {x: 0.5, y: 0.5}, {width: 400, height: 200})).toBeNull();
  });

  it("shows only required PPE with a readable status per person", () => {
    const badges = requiredPpeBadges(
      {
        bbox: [0, 0, 10, 20], confidence: 0.9, inside_zone: false, safety_shirt: true,
        ppe: {
          helmet: {status: "present", confidence: 0.9},
          safety_glasses: {status: "unknown", confidence: null},
          gloves: {status: "missing", confidence: 0.8},
        },
        missing_required_ppe: ["gloves"],
      },
      {helmet_required: true, safety_glasses_required: false, gloves_required: true},
    );

    expect(badges).toEqual([
      {label: "✓ MŨ", tone: "present"},
      {label: "✕ GĂNG", tone: "missing"},
    ]);
  });

  it("labels every model detection with its class name and confidence", () => {
    expect(detectionLabel({class_id: 7, class_name: "tool", bbox: [0, 0, 10, 20], confidence: 0.794, person_index: null}))
      .toBe("TOOL · 79%");
  });

  it("maps detection classes to consistent bounding box & list colors", () => {
    expect(getDetectionColor("person", 0, true)).toBe("#ff4940");
    expect(getDetectionColor("person", 0, false)).toBe("#22c55e");
    expect(getDetectionColor("helmet")).toBe("#f59e0b");
    expect(getDetectionColor("shoes")).toBe("#3b82f6");
    expect(getDetectionColor("gloves")).toBe("#10b981");
  });

  it("limits operator PPE displays to the canonical SH17 class names", () => {
    expect(isDisplayedPpeDetection("helmet")).toBe(true);
    expect(isDisplayedPpeDetection(" glasses ")).toBe(true);
    expect(isDisplayedPpeDetection("GLOVES")).toBe(true);
    expect(isDisplayedPpeDetection("safety-vest")).toBe(true);
    expect(isDisplayedPpeDetection("person")).toBe(false);
    expect(isDisplayedPpeDetection("tool")).toBe(false);
    expect(isDisplayedPpeDetection("safety-suit")).toBe(false);
  });
});
