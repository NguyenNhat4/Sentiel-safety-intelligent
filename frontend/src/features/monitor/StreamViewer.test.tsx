import {act, fireEvent, render, screen, waitFor} from "@testing-library/react";
import {beforeEach, expect, it, vi} from "vitest";
import {CameraDetectionClient} from "../../api/camera-detection-client";
import {listCameraConfigurations} from "../../api/camera-configurations";
import {listMediaAssets} from "../../api/media-assets";
import {saveReviewedEvent} from "../../api/events";
import {listCameraSessions, replayCamera, runSimulation} from "../../api/simulation";
import type {CameraInferenceResult} from "../../types";
import {StreamViewer} from "./StreamViewer";

let resultHandler: (result: CameraInferenceResult) => void = () => undefined;
let playbackTimeHandlers: Record<string, (time: number) => void> = {};
vi.mock("../../api/auth", () => ({getAccessToken: () => "token"}));
vi.mock("../../api/camera-configurations", () => ({listCameraConfigurations: vi.fn()}));
vi.mock("../../api/media-assets", () => ({listMediaAssets: vi.fn()}));
vi.mock("../../api/events", () => ({saveReviewedEvent: vi.fn()}));
vi.mock("../../api/simulation", () => ({listCameraSessions: vi.fn(), replayCamera: vi.fn(), runSimulation: vi.fn()}));
vi.mock("../../api/camera-detection-client", () => ({CameraDetectionClient: vi.fn(function(options: {onResult: typeof resultHandler}) { resultHandler = options.onResult; return {connect: vi.fn().mockResolvedValue(undefined), close: vi.fn()}; })}));
vi.mock("../media/AuthenticatedMedia", () => ({AuthenticatedMedia: ({label, playbackKey, playing, onPlaybackTime, onEnded}: {label: string; playbackKey: string; playing?: boolean; onPlaybackTime?: (time: number) => void; onEnded: () => void}) => {
  if (onPlaybackTime) playbackTimeHandlers[label] = onPlaybackTime;
  return <button aria-label={label} data-playback-key={playbackKey} data-playing={String(Boolean(playing))} onClick={event => { event.stopPropagation(); onEnded(); }}>media</button>;
}}));

const session = {id: "session-current", camera_id: "cam_1", asset_id: "asset-1", media_type: "video" as const, status: "RUNNING" as const, config_revision: 1, inference_fps: 1.5, started_at: "2026-08-23T00:00:00Z", running_at: "2026-08-23T00:00:01Z", completed_at: null, error_code: null};
const result = (sessionId: string, fps: number): CameraInferenceResult => ({type: "camera_inference_result", camera_id: "cam_1", session_id: sessionId, asset_id: "asset-1", media_type: "video", video_time: 1, session_status: "RUNNING", inference_fps: fps, source_timestamp_ms: 1, captured_at: 1, frame_width: 100, frame_height: 100, frame_id: 1, result: "normal", review_required: false, people: [], rule: {} as CameraInferenceResult["rule"]});

beforeEach(() => {
  vi.resetAllMocks();
  playbackTimeHandlers = {};
  vi.mocked(listCameraConfigurations).mockResolvedValue([{camera_id: "cam_1", revision: 1, asset_id: "asset-1", machine_state: "stopped", ppe_requirements: {profile: "hat_vest_v1", hat_required: false, vest_required: false}, zones: [], updated_at: null}]);
  vi.mocked(listMediaAssets).mockResolvedValue([{id: "asset-1", display_name: "Demo", media_type: "video", status: "READY", content_type: "video/mp4", size_bytes: 10, uploaded_at: "2026-08-23T00:00:00Z", assigned_camera_id: "cam_1", can_delete: false}]);
  vi.mocked(listCameraSessions).mockResolvedValue([session]);
  vi.mocked(runSimulation).mockResolvedValue({sessions: [{...session, id: "session-run", status: "STARTING"}], errors: {}});
  vi.mocked(replayCamera).mockResolvedValue({...session, id: "session-replay", status: "STARTING"});
  vi.mocked(saveReviewedEvent).mockResolvedValue({id: 1} as never);
});

it("buffers detections until video playback reaches their timestamp", async () => {
  render(<StreamViewer role="safety_manager" onConfigure={vi.fn()} />);
  await screen.findByText("RUNNING");
  resultHandler({...result("session-current", 2.5), video_time: 2});

  expect(screen.queryByLabelText("Detection overlay frame 1")).not.toBeInTheDocument();
  act(() => playbackTimeHandlers["Media Camera 1"]?.(1.6));
  expect(screen.queryByLabelText("Detection overlay frame 1")).not.toBeInTheDocument();

  act(() => playbackTimeHandlers["Media Camera 1"]?.(1.9));
  expect(screen.getByLabelText("Detection overlay frame 1")).toBeInTheDocument();

  act(() => playbackTimeHandlers["Media Camera 1"]?.(2.3));
  expect(screen.queryByLabelText("Detection overlay frame 1")).not.toBeInTheDocument();
});

it("renders four permanent slots and opens the exact camera only for safety managers", async () => {
  const configure = vi.fn();
  render(<StreamViewer role="safety_manager" onConfigure={configure} />);
  expect(await screen.findByRole("heading", {name: "Camera 4"})).toBeInTheDocument();
  expect(screen.getAllByText("Bấm vào đây để cấu hình")).toHaveLength(3);
  fireEvent.click(screen.getByRole("button", {name: "Cấu hình Camera 3"}));
  expect(configure).toHaveBeenCalledWith("cam_3");
  expect(screen.getByRole("button", {name: "Chạy mô phỏng"})).toBeInTheDocument();
});

it("runs once, ignores stale sessions, displays rolling FPS, and replays one completed camera", async () => {
  render(<StreamViewer role="safety_manager" onConfigure={vi.fn()} />);
  await screen.findByText("RUNNING");
  fireEvent.click(screen.getByRole("button", {name: "Chạy mô phỏng"}));
  await waitFor(() => expect(runSimulation).toHaveBeenCalledOnce());
  expect(screen.getByRole("button", {name: "Media Camera 1"})).toHaveAttribute("data-playback-key", "session-run");
  resultHandler(result("session-current", 99));
  expect(screen.queryByText("99.0")).not.toBeInTheDocument();
  resultHandler(result("session-run", 2.75));
  expect(await screen.findByText("2.8")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {name: "Media Camera 1"}));
  vi.mocked(replayCamera).mockResolvedValue({...session, id: "session-replay", status: "COMPLETED"});
  fireEvent.click(screen.getByRole("button", {name: "Replay Camera 1"}));
  await waitFor(() => expect(replayCamera).toHaveBeenCalledWith("cam_1"));
  expect(screen.getByRole("button", {name: "Media Camera 1"})).toHaveAttribute("data-playback-key", "session-replay");
  expect(screen.getByRole("button", {name: "Media Camera 1"})).toHaveAttribute("data-playing", "true");
});

it("does not expose run or configuration actions to system admins", async () => {
  render(<StreamViewer role="system_admin" onConfigure={vi.fn()} />);
  await screen.findByRole("heading", {name: "Camera 1"});
  expect(screen.queryByRole("button", {name: "Chạy mô phỏng"})).not.toBeInTheDocument();
  expect(screen.queryByRole("button", {name: "Cấu hình Camera 1"})).not.toBeInTheDocument();
  expect(CameraDetectionClient).toHaveBeenCalled();
});

it("opens direct-camera HITL review and persists the reviewed occurrence", async () => {
  render(<StreamViewer role="safety_manager" onConfigure={vi.fn()} />);
  await screen.findByText("RUNNING");
  resultHandler({
    ...result("session-current", 1.5),
    result: "violate",
    review_required: true,
    has_active_violation: true,
    monitoring_session_id: "00000000-0000-0000-0000-000000000001",
    snapshot_data: "data:image/jpeg;base64,AA==",
    people: [{
      track_id: 7,
      bbox: [10, 10, 30, 80],
      confidence: 0.95,
      foot_point: [20, 80],
      inside_zone: true,
      ppe: {hat: {status: "present", confidence: 0.9}, vest: {status: "present", confidence: 0.9}},
      missing_required_ppe: [],
      active_violations: [{
        occurrence_id: "00000000-0000-0000-0000-000000000002",
        rule_key: "zone_intrusion:press",
        zone_id: "press",
        is_new: true,
      }],
    }],
    rule: {
      person_inside_zone: true,
      machine_state: "running",
      ppe_profile: "hat_vest_v1",
      camera_id: "cam_1",
      zone_id: "press",
      ppe_requirements: {profile: "hat_vest_v1", hat_required: false, vest_required: false},
      ppe_alert: false,
    },
  });

  expect(await screen.findByRole("dialog")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {name: /Vi phạm thực tế/}));
  await waitFor(() => expect(saveReviewedEvent).toHaveBeenCalledOnce());
  expect(vi.mocked(saveReviewedEvent).mock.calls[0][0]).toMatchObject({
    camera_id: "cam_1",
    track_id: 7,
    occurrence_ids: ["00000000-0000-0000-0000-000000000002"],
    status: "acknowledged",
  });
});

it("persists a shared occurrence once and closes the HITL review", async () => {
  render(<StreamViewer role="safety_manager" onConfigure={vi.fn()} />);
  await screen.findByText("RUNNING");
  const sharedViolation = {
    occurrence_id: "00000000-0000-0000-0000-000000000003",
    rule_key: "zone_intrusion:press",
    zone_id: "press",
    is_new: true,
  };
  const person = (trackId: number) => ({
    track_id: trackId,
    bbox: [10, 10, 30, 80] as [number, number, number, number],
    confidence: 0.95,
    foot_point: [20, 80] as [number, number],
    inside_zone: true,
    ppe: {hat: {status: "present" as const, confidence: 0.9}, vest: {status: "present" as const, confidence: 0.9}},
    missing_required_ppe: [],
    active_violations: [sharedViolation],
  });
  resultHandler({
    ...result("session-current", 1.5),
    result: "violate",
    review_required: true,
    has_active_violation: true,
    monitoring_session_id: "00000000-0000-0000-0000-000000000001",
    snapshot_data: "data:image/jpeg;base64,AA==",
    people: [person(7), person(8)],
    rule: {
      person_inside_zone: true,
      machine_state: "running",
      ppe_profile: "hat_vest_v1",
      camera_id: "cam_1",
      zone_id: "press",
      ppe_requirements: {profile: "hat_vest_v1", hat_required: false, vest_required: false},
      ppe_alert: false,
    },
  });

  const violate = await screen.findByRole("button", {name: /Vi phạm thực tế/});
  fireEvent.click(violate);
  fireEvent.click(violate);
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(saveReviewedEvent).toHaveBeenCalledOnce();
});

it("names the missing PPE item in the HITL popup", async () => {
  render(<StreamViewer role="safety_manager" onConfigure={vi.fn()} />);
  await screen.findByText("RUNNING");
  resultHandler({
    ...result("session-current", 1.5),
    result: "violate",
    review_required: true,
    has_active_violation: true,
    monitoring_session_id: "00000000-0000-0000-0000-000000000001",
    people: [{
      track_id: 9,
      bbox: [10, 10, 30, 80],
      confidence: 0.95,
      foot_point: [20, 80],
      inside_zone: false,
      ppe: {hat: {status: "missing", confidence: null}, vest: {status: "present", confidence: 0.9}},
      missing_required_ppe: ["hat"],
      active_violations: [{occurrence_id: "00000000-0000-0000-0000-000000000004", rule_key: "missing_ppe:hat", zone_id: "camera_wide", is_new: true}],
    }],
    rule: {
      person_inside_zone: false,
      machine_state: "running",
      ppe_profile: "hat_vest_v1",
      camera_id: "cam_1",
      zone_id: "camera_wide",
      ppe_requirements: {profile: "hat_vest_v1", hat_required: true, vest_required: false},
      ppe_alert: true,
    },
  });

  expect(await screen.findByRole("heading", {name: "Phát hiện thiếu mũ bảo hộ"})).toBeInTheDocument();
  expect(screen.queryByText("Phát hiện thiếu PPE")).not.toBeInTheDocument();
});
