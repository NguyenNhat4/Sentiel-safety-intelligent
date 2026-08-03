import {describe, expect, it} from "vitest";
import {findPointAt, normalizedPointerPosition} from "./canvas";

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
});
