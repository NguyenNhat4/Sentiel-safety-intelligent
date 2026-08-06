import {describe, expect, it} from "vitest";
import {findPointAt, normalizedPointerPosition, requiredPpeBadges} from "./canvas";

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
});
