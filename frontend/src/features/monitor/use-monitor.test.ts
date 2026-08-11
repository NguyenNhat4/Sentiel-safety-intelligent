import {describe, expect, it, vi} from "vitest";
import type {InferenceResult} from "../../types";
import {buildEventPayload, buildPpeRule, captureVideoSnapshot} from "./use-monitor";

describe("review event payload", () => {
  const pending: InferenceResult = {
    type: "inference_result", frame_id: 1, video_time: 4.25,
    monitoring_session_id: "3cddfe85-9428-44d7-afbf-0cd9e5fc0640",
    result: "violate", review_required: true, snapshot_data: "data:image/jpeg;base64,AA==",
    people: [{
      track_id: 7,
      bbox: [0, 0, 10, 20], confidence: 0.9, inside_zone: true, safety_shirt: false,
      ppe: {
        helmet: {status: "unknown", confidence: null},
        safety_glasses: {status: "unknown", confidence: null},
        gloves: {status: "unknown", confidence: null},
      },
      missing_required_ppe: [],
      active_violations: [{occurrence_id: "7aedf540-36da-4cf8-bb9b-8cd7aeab460d", rule_key: "zone_intrusion", is_new: true}],
    }],
    detections: [{
      class_id: 1, class_name: "helmet", bbox: [2, 3, 8, 9], confidence: 0.8, person_index: 0,
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
    expect(payload.snapshot_people).toEqual(pending.people);
    expect(payload.snapshot_detections).toEqual(pending.detections);
    expect(payload).not.toHaveProperty("privacy_blurred");
    expect(payload.monitoring_session_id).toBe(pending.monitoring_session_id);
    expect(payload.occurrence_ids).toEqual(["7aedf540-36da-4cf8-bb9b-8cd7aeab460d"]);
  });

  it("does not attach an already reviewed active occurrence to a new grouped review", () => {
    const withOldOccurrence = {
      ...pending,
      people: [{
        ...pending.people[0],
        active_violations: [
          ...pending.people[0].active_violations!,
          {occurrence_id: "9a2c2d52-73ce-4a35-8a27-e5052925e17c", rule_key: "missing_ppe:helmet", is_new: false},
        ],
      }],
    };
    expect(buildEventPayload("acknowledged", withOldOccurrence, [], true).occurrence_ids)
      .toEqual(["7aedf540-36da-4cf8-bb9b-8cd7aeab460d"]);
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

describe("stopped-video review snapshot", () => {
  it("captures the full native video frame before the review modal opens", () => {
    const drawImage = vi.fn();
    const toDataURL = vi.fn().mockReturnValue("data:image/jpeg;base64,stopped-frame");
    const capture = {
      width: 0,
      height: 0,
      getContext: () => ({drawImage}),
      toDataURL,
    } as unknown as HTMLCanvasElement;
    const video = {videoWidth: 1920, videoHeight: 1080} as HTMLVideoElement;

    expect(captureVideoSnapshot(video, capture)).toBe("data:image/jpeg;base64,stopped-frame");
    expect(capture.width).toBe(1920);
    expect(capture.height).toBe(1080);
    expect(drawImage).toHaveBeenCalledWith(video, 0, 0, 1920, 1080);
  });
});
