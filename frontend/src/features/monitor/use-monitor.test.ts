import {describe, expect, it, vi} from "vitest";
import type {InferenceResult} from "../../types";
import {buildEventBatchPayload, buildEventPayload, buildHitlLogEntries, buildHumanReviewState, buildPpeRule, captureVideoSnapshot, reconcileHitlLogs} from "./use-monitor";

describe("review event payload", () => {
  const pending: InferenceResult = {
    type: "inference_result", frame_id: 1, video_time: 4.25,
    monitoring_session_id: "3cddfe85-9428-44d7-afbf-0cd9e5fc0640",
    result: "violate", review_required: true, snapshot_data: "data:image/jpeg;base64,AA==",
    people: [{
      track_id: 7,
      bbox: [0, 0, 10, 20], confidence: 0.9, inside_zone: true,
      ppe: {
        hat: {status: "unknown", confidence: null},
        vest: {status: "unknown", confidence: null},
      },
      missing_required_ppe: [],
      active_violations: [{occurrence_id: "7aedf540-36da-4cf8-bb9b-8cd7aeab460d", rule_key: "zone_intrusion", is_new: true}],
    }],
    detections: [{
      class_id: 0, class_name: "hat", bbox: [2, 3, 8, 9], confidence: 0.8, person_index: 0,
    }],
    rule: {
      person_inside_zone: true, machine_state: "running", ppe_profile: "hat_vest_v1",
      camera_id: "uploaded_video", zone_id: "zone_01",
      ppe_requirements: {profile: "hat_vest_v1", hat_required: false, vest_required: false},
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
          {occurrence_id: "9a2c2d52-73ce-4a35-8a27-e5052925e17c", rule_key: "missing_ppe:hat", is_new: false},
        ],
      }],
    };
    expect(buildEventPayload("acknowledged", withOldOccurrence, [], true).occurrence_ids)
      .toEqual(["7aedf540-36da-4cf8-bb9b-8cd7aeab460d"]);
  });

  it("uses configured hat-and-vest states", () => {
    expect(buildPpeRule(pending)).toEqual({yes: null, text: "Không yêu cầu PPE", badge: "OFF"});
    const hatRequired = {
      ...pending,
      rule: {
        ...pending.rule,
        ppe_requirements: {profile: "hat_vest_v1" as const, hat_required: true, vest_required: false},
      },
    };
    expect(buildPpeRule(hatRequired)).toEqual({yes: null, text: "Đang kiểm tra mũ bảo hộ", badge: "CHECK"});
  });

  it("partitions a grouped review into one event per zone", () => {
    const multi = {
      ...pending,
      people: [{
        ...pending.people[0],
        active_violations: [
          {occurrence_id: "7aedf540-36da-4cf8-bb9b-8cd7aeab460d", rule_key: "zone_intrusion:left", zone_id: "left", is_new: true},
          {occurrence_id: "9a2c2d52-73ce-4a35-8a27-e5052925e17c", rule_key: "zone_intrusion:right", zone_id: "right", is_new: true},
        ],
      }],
    };
    const zones = ["left", "right"].map((zoneId, order) => ({
      zone_id: zoneId, display_name: zoneId, points: [], machine_state: "running" as const, enabled: true, order,
    }));

    const payload = buildEventBatchPayload("acknowledged", multi, zones);
    expect(payload?.events.map(event => ({zone_id: event.zone_id, occurrence_ids: event.occurrence_ids}))).toEqual([
      {zone_id: "left", occurrence_ids: ["7aedf540-36da-4cf8-bb9b-8cd7aeab460d"]},
      {zone_id: "right", occurrence_ids: ["9a2c2d52-73ce-4a35-8a27-e5052925e17c"]},
    ]);
  });
});

describe("Human-in-the-Loop alert states", () => {
  const base: InferenceResult = {
    type: "inference_result", frame_id: 1, video_time: 0, result: "normal", review_required: false, people: [],
    rule: {
      person_inside_zone: false, machine_state: "running", ppe_profile: "hat_vest_v1", camera_id: "uploaded_video", zone_id: "zone_01",
      ppe_requirements: {profile: "hat_vest_v1", hat_required: true, vest_required: true}, ppe_alert: false,
    },
  };
  const person = {bbox: [0, 0, 10, 20] as [number, number, number, number], confidence: 0.9, inside_zone: false,
    ppe: {hat: {status: "present" as const, confidence: 0.9}, vest: {status: "present" as const, confidence: 0.9}}, missing_required_ppe: [] as Array<"hat" | "vest">};

  it("prioritizes forbidden-zone entry, then missing PPE, then an unknown PPE review", () => {
    expect(buildHumanReviewState({...base, people: [{...person, inside_zone: true}]}).tone).toBe("critical");
    expect(buildHumanReviewState({...base, people: [{...person, missing_required_ppe: ["hat"]}]}).tone).toBe("unknown");
    expect(buildHumanReviewState({...base, rule: {...base.rule, ppe_alert: true}, people: [{...person, missing_required_ppe: ["hat"]}]}).tone).toBe("warning");
    expect(buildHumanReviewState({...base, people: [{...person, ppe: {...person.ppe, vest: {status: "unknown", confidence: null}}}]}).tone).toBe("unknown");
    expect(buildHumanReviewState({...base, people: [person]}).tone).toBe("normal");
  });
});

describe("Human-in-the-Loop warning logs", () => {
  it("retracts only an unreviewed PPE log for the same TrackID", () => {
    const sessionId = "3cddfe85-9428-44d7-afbf-0cd9e5fc0640";
    const result: InferenceResult = {
      type: "inference_result", frame_id: 1, video_time: 2, result: "violate", review_required: true,
      monitoring_session_id: sessionId, snapshot_data: "data:image/jpeg;base64,AA==",
      people: [{bbox: [0, 0, 10, 20], confidence: 0.9, inside_zone: false, track_id: 9,
        ppe: {hat: {status: "missing", confidence: null}, vest: {status: "present", confidence: 0.9}},
        missing_required_ppe: ["hat"],
        active_violations: [
          {occurrence_id: "7aedf540-36da-4cf8-bb9b-8cd7aeab460d", rule_key: "missing_ppe:hat", is_new: true},
        ]}],
      rule: {person_inside_zone: false, machine_state: "running", ppe_profile: "hat_vest_v1", camera_id: "uploaded_video", zone_id: "zone_01",
        ppe_requirements: {profile: "hat_vest_v1", hat_required: true, vest_required: true}, ppe_alert: true},
    };
    const logs = buildHitlLogEntries(result);
    const presentIds = new Set([`${sessionId}:person:9`]);

    expect(reconcileHitlLogs(logs, [], presentIds)).toEqual([]);
    expect(reconcileHitlLogs([{...logs[0], reviewStatus: "reviewed"}], [], presentIds)).toHaveLength(1);
  });

  it("creates one combined warning per person for all missing PPE items", () => {
    const result: InferenceResult = {
      type: "inference_result", frame_id: 1, video_time: 0, result: "violate", review_required: true,
      people: [{bbox: [0, 0, 10, 20], confidence: 0.9, inside_zone: false, track_id: 9,
        ppe: {hat: {status: "missing", confidence: null}, vest: {status: "missing", confidence: null}},
        missing_required_ppe: ["hat", "vest"],
        active_violations: [
          {occurrence_id: "7aedf540-36da-4cf8-bb9b-8cd7aeab460d", rule_key: "missing_ppe:hat", is_new: true},
          {occurrence_id: "90494038-ea97-405b-830d-75d0b2613826", rule_key: "missing_ppe:vest", is_new: true},
        ]}],
      rule: {person_inside_zone: false, machine_state: "running", ppe_profile: "hat_vest_v1", camera_id: "uploaded_video", zone_id: "zone_01",
        ppe_requirements: {profile: "hat_vest_v1", hat_required: true, vest_required: true}, ppe_alert: true},
    };
    const logs = buildHitlLogEntries(result);
    expect(logs.map(entry => entry.title)).toEqual(["Thiếu mũ bảo hộ và áo phản quang"]);
    expect(logs).toHaveLength(1);
    expect(logs[0].reviewResult?.people).toEqual([result.people[0]]);

    const vestOnly: InferenceResult = {
      ...result,
      frame_id: 2,
      review_required: false,
      snapshot_data: undefined,
      people: [{
        ...result.people[0],
        ppe: {...result.people[0].ppe, hat: {status: "present", confidence: 0.9}},
        missing_required_ppe: ["vest"],
        active_violations: [
          {occurrence_id: "90494038-ea97-405b-830d-75d0b2613826", rule_key: "missing_ppe:vest", is_new: false},
        ],
      }],
    };
    const reconciled = reconcileHitlLogs(logs, buildHitlLogEntries(vestOnly), new Set(["session:person:9"]));

    expect(reconciled[0].violationKeys).toEqual(["missing_ppe:vest"]);
    expect(reconciled[0].reviewResult?.snapshot_data).toBe(result.snapshot_data);
    expect(reconciled[0].reviewResult?.people[0].active_violations?.[0].is_new).toBe(true);
  });

  it("keeps hat, vest and zone intrusion in one person event", () => {
    const result: InferenceResult = {
      type: "inference_result", frame_id: 2, video_time: 1, result: "violate", review_required: true,
      monitoring_session_id: "3cddfe85-9428-44d7-afbf-0cd9e5fc0640",
      people: [{bbox: [0, 0, 10, 20], confidence: 0.9, inside_zone: true, track_id: 9,
        ppe: {hat: {status: "missing", confidence: null}, vest: {status: "missing", confidence: null}},
        missing_required_ppe: ["hat", "vest"],
        active_violations: [
          {occurrence_id: "7aedf540-36da-4cf8-bb9b-8cd7aeab460d", rule_key: "missing_ppe:hat", is_new: true},
          {occurrence_id: "90494038-ea97-405b-830d-75d0b2613826", rule_key: "missing_ppe:vest", is_new: true},
          {occurrence_id: "4f6d4ee1-28fd-43a8-b754-736b80fcf742", rule_key: "zone_intrusion:zone_01", zone_id: "zone_01", is_new: true},
        ]}],
      rule: {person_inside_zone: true, machine_state: "running", ppe_profile: "hat_vest_v1", camera_id: "uploaded_video", zone_id: "zone_01",
        ppe_requirements: {profile: "hat_vest_v1", hat_required: true, vest_required: true}, ppe_alert: true},
    };

    const payload = buildEventPayload("acknowledged", result, [], true);
    expect(payload.track_id).toBe(9);
    expect(payload.event_type).toBe("person_safety_violation");
    expect(payload.occurrence_ids).toHaveLength(3);
    expect(payload.details.violations).toEqual([
      "missing_ppe:hat", "missing_ppe:vest", "zone_intrusion:zone_01",
    ]);

    const logs = buildHitlLogEntries(result);
    const zoneOnly: InferenceResult = {
      ...result,
      frame_id: 3,
      people: [{
        ...result.people[0],
        ppe: {hat: {status: "present", confidence: 0.9}, vest: {status: "present", confidence: 0.9}},
        missing_required_ppe: [],
        active_violations: [
          {occurrence_id: "4f6d4ee1-28fd-43a8-b754-736b80fcf742", rule_key: "zone_intrusion:zone_01", zone_id: "zone_01", is_new: false},
        ],
      }],
    };
    const reconciled = reconcileHitlLogs(
      logs,
      buildHitlLogEntries(zoneOnly),
      new Set([`${result.monitoring_session_id}:person:9`]),
    );

    expect(reconciled[0].violationKeys).toEqual(["zone_intrusion:zone_01"]);
    expect(reconciled[0].reviewResult?.people[0].active_violations?.map(item => item.rule_key))
      .toEqual(["zone_intrusion:zone_01"]);
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
