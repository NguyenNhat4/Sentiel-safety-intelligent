import {describe, expect, it} from "vitest";
import {changedCameraIds, sameMappings} from "./stream-mapping";

describe("stream mapping delta", () => {
  it("restarts only the player whose mapping changed", () => {
    const before = [
      {camera_id: "cam_1", stream_camera_id: "stream_a"},
      {camera_id: "cam_2", stream_camera_id: "stream_b"},
    ];
    const after = [
      {camera_id: "cam_1", stream_camera_id: "stream_c"},
      {camera_id: "cam_2", stream_camera_id: "stream_b"},
    ];

    expect(changedCameraIds(before, after)).toEqual(["cam_1"]);
    expect(sameMappings(before, after)).toBe(false);
    expect(sameMappings(after, [...after].reverse())).toBe(true);
  });
});
