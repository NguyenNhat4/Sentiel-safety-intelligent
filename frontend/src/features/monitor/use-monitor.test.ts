import {describe, expect, it} from "vitest";
import type {InferenceResult} from "../../types";
import {buildEventPayload, buildPpeRule} from "./use-monitor";

describe("review event payload", () => {
  const pending: InferenceResult = {
    type: "inference_result", frame_id: 1, video_time: 4.25,
    result: "violate", review_required: true, snapshot_data: "data:image/jpeg;base64,AA==",
    people: [{
      bbox: [0, 0, 10, 20], confidence: 0.9, inside_zone: true, safety_shirt: false,
      ppe: {
        helmet: {status: "unknown", confidence: null},
        safety_glasses: {status: "unknown", confidence: null},
        gloves: {status: "unknown", confidence: null},
      },
      missing_required_ppe: [],
    }],
    rule: {
      person_inside_zone: true, machine_state: "running", safety_shirt_required: true,
      camera_id: "uploaded_video", zone_id: "zone_01",
      ppe_requirements: {helmet_required: false, safety_glasses_required: false, gloves_required: false},
      ppe_alert: false,
    }
  };

  it("maps acknowledged review without changing the backend contract", () => {
    const payload = buildEventPayload("acknowledged", pending, [{x: 0.1, y: 0.2}], true);
    expect(payload.status).toBe("acknowledged");
    expect(payload.details).toMatchObject({
      review_result: "actual_violation",
      machine_state: "running",
      video_timestamp_seconds: 4.25
    });
    expect(payload.snapshot_data).toBe(pending.snapshot_data);
  });

  it("uses configured PPE states instead of the legacy safety-shirt heuristic", () => {
    expect(buildPpeRule(pending)).toEqual({yes: null, text: "Không yêu cầu PPE", badge: "OFF"});
    const helmetRequired = {
      ...pending,
      rule: {
        ...pending.rule,
        ppe_requirements: {helmet_required: true, safety_glasses_required: false, gloves_required: false},
      },
    };
    expect(buildPpeRule(helmetRequired)).toEqual({yes: null, text: "Đang kiểm tra mũ", badge: "CHECK"});
  });
});
