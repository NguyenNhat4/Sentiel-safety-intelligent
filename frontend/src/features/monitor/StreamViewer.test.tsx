import {act, fireEvent, render, screen, waitFor} from "@testing-library/react";
import {beforeEach, expect, it, vi} from "vitest";
import {CameraDetectionClient} from "../../api/camera-detection-client";
import {listCameraConfigurations} from "../../api/camera-configurations";
import {listMediaAssets} from "../../api/media-assets";
import {loadPendingEvents, saveReviewedEvent} from "../../api/events";
import type {SafetyEventUpdate} from "../../api/events";
import {listCameraSessions, replayCamera, runSimulation} from "../../api/simulation";
import type {CameraInferenceResult, MediaStorageBackend} from "../../types";
import {PpeAlertToast} from "../alerts/PpeAlertToast";
import {preloadSnapshot} from "../alerts/preload-snapshot";
import {StreamViewer} from "./StreamViewer";

let resultHandler: (result: CameraInferenceResult) => void = () => undefined;
let playbackTimeHandlers: Record<string, (time: number) => void> = {};
let eventUpdateHandler: (update: SafetyEventUpdate) => void = () => undefined;
vi.mock("../../api/auth", () => ({getAccessToken: () => "token"}));
vi.mock("../../api/camera-configurations", () => ({listCameraConfigurations: vi.fn()}));
vi.mock("../../api/media-assets", () => ({listMediaAssets: vi.fn()}));
vi.mock("../../api/events", () => ({
  loadPendingEvents: vi.fn(),
  saveReviewedEvent: vi.fn(),
  subscribeToSafetyEventUpdates: (listener: (update: SafetyEventUpdate) => void) => {
    eventUpdateHandler = listener;
    return vi.fn();
  },
}));
vi.mock("../../api/simulation", () => ({listCameraSessions: vi.fn(), replayCamera: vi.fn(), runSimulation: vi.fn()}));
vi.mock("../../api/camera-detection-client", () => ({CameraDetectionClient: vi.fn(function(options: {onResult: typeof resultHandler}) { resultHandler = options.onResult; return {connect: vi.fn().mockResolvedValue(undefined), close: vi.fn()}; })}));
vi.mock("../alerts/preload-snapshot", () => ({preloadSnapshot: vi.fn()}));
vi.mock("../media/AuthenticatedMedia", () => ({AuthenticatedMedia: ({label, playbackKey, playing, storageBackend, onPlaybackTime, onEnded}: {label: string; playbackKey: string; playing?: boolean; storageBackend: MediaStorageBackend; onPlaybackTime?: (time: number) => void; onEnded: () => void}) => {
  if (onPlaybackTime) playbackTimeHandlers[label] = onPlaybackTime;
  return <button aria-label={label} data-playback-key={playbackKey} data-playing={String(Boolean(playing))} data-storage-backend={storageBackend} onClick={event => { event.stopPropagation(); onEnded(); }}>media</button>;
}}));

const session = {id: "session-current", camera_id: "cam_1", asset_id: "asset-1", media_type: "video" as const, status: "RUNNING" as const, config_revision: 1, inference_fps: 1.5, started_at: "2026-08-23T00:00:00Z", running_at: "2026-08-23T00:00:01Z", completed_at: null, error_code: null};
const result = (sessionId: string, fps: number): CameraInferenceResult => ({type: "camera_inference_result", camera_id: "cam_1", session_id: sessionId, asset_id: "asset-1", media_type: "video", video_time: 1, session_status: "RUNNING", inference_fps: fps, source_timestamp_ms: 1, captured_at: 1, frame_width: 100, frame_height: 100, frame_id: 1, result: "normal", review_required: false, people: [], rule: {} as CameraInferenceResult["rule"]});
const pendingEvent = (id: number, inference: CameraInferenceResult, eventType = "zone_intrusion") => ({
  id,
  timestamp: "2026-08-23T00:00:02Z",
  zone_id: eventType === "missing_ppe" ? "camera_wide" : "press",
  camera_id: inference.camera_id,
  event_type: eventType,
  severity: eventType === "missing_ppe" ? "high" : "critical",
  status: "unacknowledged" as const,
  snapshot_path: "/snapshots/pending.jpg",
  details: {
    violations: inference.people.flatMap(person => person.active_violations?.map(item => item.rule_key) ?? []),
    video_timestamp_seconds: inference.video_time,
    pending_review: inference,
  },
});

beforeEach(() => {
  vi.resetAllMocks();
  playbackTimeHandlers = {};
  eventUpdateHandler = () => undefined;
  vi.mocked(listCameraConfigurations).mockResolvedValue([{camera_id: "cam_1", revision: 1, asset_id: "asset-1", machine_state: "stopped", ppe_requirements: {profile: "hat_vest_v1", hat_required: false, vest_required: false}, zones: [], updated_at: null}]);
  vi.mocked(listMediaAssets).mockResolvedValue([{id: "asset-1", display_name: "Demo", media_type: "video", status: "READY", content_type: "video/mp4", size_bytes: 10, storage_backend: "s3", uploaded_at: "2026-08-23T00:00:00Z", assigned_camera_id: "cam_1", can_delete: false}]);
  vi.mocked(listCameraSessions).mockResolvedValue([session]);
  vi.mocked(loadPendingEvents).mockResolvedValue([]);
  vi.mocked(runSimulation).mockResolvedValue({sessions: [{...session, id: "session-run", status: "STARTING"}], errors: {}});
  vi.mocked(replayCamera).mockResolvedValue({...session, id: "session-replay", status: "STARTING"});
  vi.mocked(saveReviewedEvent).mockResolvedValue({id: 1} as never);
  vi.mocked(preloadSnapshot).mockResolvedValue(true);
});

it("buffers detections until video playback reaches their timestamp", async () => {
  render(<StreamViewer role="safety_manager" onConfigure={vi.fn()} />);
  await screen.findByText("RUNNING");
  expect(screen.getByRole("button", {name: "Media Camera 1"})).toHaveAttribute("data-storage-backend", "s3");
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

it("exposes run and configuration actions to system admins", async () => {
  const configure = vi.fn();
  render(<StreamViewer role="system_admin" onConfigure={configure} />);
  await screen.findByRole("heading", {name: "Camera 1"});
  expect(screen.getByRole("button", {name: "Chạy mô phỏng"})).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {name: "Cấu hình Camera 1"}));
  expect(configure).toHaveBeenCalledWith("cam_1");
  expect(CameraDetectionClient).toHaveBeenCalled();
});

it("opens direct-camera HITL review and persists the reviewed occurrence", async () => {
  render(<StreamViewer role="safety_manager" onConfigure={vi.fn()} />);
  await screen.findByText("RUNNING");
  const inference = {
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
    pending_event_ids: [41],
    rule: {
      person_inside_zone: true,
      machine_state: "running",
      ppe_profile: "hat_vest_v1",
      camera_id: "cam_1",
      zone_id: "press",
      ppe_requirements: {profile: "hat_vest_v1", hat_required: false, vest_required: false},
      ppe_alert: false,
    },
  } satisfies CameraInferenceResult;
  vi.mocked(loadPendingEvents).mockResolvedValue([pendingEvent(41, inference)]);
  resultHandler(inference);

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

it("waits for the persisted snapshot to preload before opening HITL", async () => {
  let finishLoading: (loaded: boolean) => void = () => undefined;
  vi.mocked(preloadSnapshot).mockReturnValue(new Promise(resolve => { finishLoading = resolve; }));
  const inference = {
    ...result("session-current", 1.5),
    result: "violate",
    review_required: true,
    pending_event_ids: [42],
    monitoring_session_id: "00000000-0000-0000-0000-000000000001",
    people: [{
      track_id: 8,
      bbox: [10, 10, 30, 80], confidence: 0.95, foot_point: [20, 80], inside_zone: true,
      ppe: {hat: {status: "present", confidence: 0.9}, vest: {status: "present", confidence: 0.9}},
      missing_required_ppe: [],
      active_violations: [{occurrence_id: "occ-42", rule_key: "zone_intrusion:press", zone_id: "press", is_new: true}],
    }],
    rule: {person_inside_zone: true, machine_state: "running", ppe_profile: "hat_vest_v1", camera_id: "cam_1", zone_id: "press", ppe_requirements: {profile: "hat_vest_v1", hat_required: false, vest_required: false}, ppe_alert: false},
  } satisfies CameraInferenceResult;
  render(<StreamViewer role="safety_manager" onConfigure={vi.fn()} />);
  await screen.findByText("RUNNING");
  vi.mocked(loadPendingEvents).mockResolvedValue([pendingEvent(42, inference)]);

  resultHandler(inference);
  await waitFor(() => expect(preloadSnapshot).toHaveBeenCalledWith("http://localhost:3000/snapshots/pending.jpg"));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

  finishLoading(true);
  expect(await screen.findByRole("dialog")).toBeInTheDocument();
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
  const inference = {
    ...result("session-current", 1.5),
    result: "violate",
    review_required: true,
    has_active_violation: true,
    monitoring_session_id: "00000000-0000-0000-0000-000000000001",
    snapshot_data: "data:image/jpeg;base64,AA==",
    people: [person(7), person(8)],
    pending_event_ids: [42],
    rule: {
      person_inside_zone: true,
      machine_state: "running",
      ppe_profile: "hat_vest_v1",
      camera_id: "cam_1",
      zone_id: "press",
      ppe_requirements: {profile: "hat_vest_v1", hat_required: false, vest_required: false},
      ppe_alert: false,
    },
  } satisfies CameraInferenceResult;
  vi.mocked(loadPendingEvents).mockResolvedValue([pendingEvent(42, inference)]);
  resultHandler(inference);

  const violate = await screen.findByRole("button", {name: /Vi phạm thực tế/});
  fireEvent.click(violate);
  fireEvent.click(violate);
  await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  expect(saveReviewedEvent).toHaveBeenCalledOnce();
});

it("shows a closeable PPE toast and keeps the pending row", async () => {
  render(<StreamViewer role="safety_manager" onConfigure={vi.fn()} />);
  await screen.findByText("RUNNING");
  const inference = {
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
    pending_event_ids: [43],
    rule: {
      person_inside_zone: false,
      machine_state: "running",
      ppe_profile: "hat_vest_v1",
      camera_id: "cam_1",
      zone_id: "camera_wide",
      ppe_requirements: {profile: "hat_vest_v1", hat_required: true, vest_required: false},
      ppe_alert: true,
    },
  } satisfies CameraInferenceResult;
  vi.mocked(loadPendingEvents).mockResolvedValue([pendingEvent(43, inference, "missing_ppe")]);
  resultHandler(inference);

  expect(await screen.findByLabelText("Cảnh báo PPE mới")).toBeInTheDocument();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.getAllByText("Thiếu mũ bảo hộ")).toHaveLength(2);
  fireEvent.click(screen.getByRole("button", {name: "Đóng thông báo PPE"}));
  expect(screen.queryByLabelText("Cảnh báo PPE mới")).not.toBeInTheDocument();
  expect(screen.getByText("Chưa xử lý")).toBeInTheDocument();
});

it("automatically closes a PPE toast after three seconds", () => {
  vi.useFakeTimers();
  const onClose = vi.fn();
  const alert = pendingEvent(44, result("session-current", 1.5), "missing_ppe");
  render(<PpeAlertToast alert={alert} onOpen={vi.fn()} onClose={onClose} />);
  act(() => vi.advanceTimersByTime(2999));
  expect(onClose).not.toHaveBeenCalled();
  act(() => vi.advanceTimersByTime(1));
  expect(onClose).toHaveBeenCalledOnce();
  vi.useRealTimers();
});

it("restores pending alerts after returning to Live Monitor", async () => {
  const inference = result("session-current", 1.5);
  vi.mocked(loadPendingEvents).mockResolvedValue([pendingEvent(60, inference, "missing_ppe")]);
  render(<StreamViewer role="safety_manager" onConfigure={vi.fn()} />);

  expect(await screen.findByLabelText("1 cảnh báo chưa xử lý")).toBeInTheDocument();
  expect(screen.queryByLabelText("Cảnh báo PPE mới")).not.toBeInTheDocument();
});

it("reconciles the pending inbox after an event changes on Camera Detail", async () => {
  const inference = result("session-current", 1.5);
  vi.mocked(loadPendingEvents).mockResolvedValueOnce([pendingEvent(61, inference, "missing_ppe")]);
  render(<StreamViewer role="safety_manager" onConfigure={vi.fn()} />);
  expect(await screen.findByLabelText("1 cảnh báo chưa xử lý")).toBeInTheDocument();
  vi.mocked(loadPendingEvents).mockResolvedValueOnce([]);

  act(() => eventUpdateHandler({eventIds: [61], cameraIds: ["cam_1"]}));

  await waitFor(() => expect(screen.queryByLabelText("1 cảnh báo chưa xử lý")).not.toBeInTheDocument());
  expect(loadPendingEvents).toHaveBeenCalledTimes(2);
});

it("queues new zone alerts and never stacks HITL popups", async () => {
  render(<StreamViewer role="safety_manager" onConfigure={vi.fn()} />);
  await screen.findByText("RUNNING");
  const zoneInference = (id: number, zoneId: string): CameraInferenceResult => ({
    ...result("session-current", 1.5),
    result: "violate",
    review_required: true,
    pending_event_ids: [id],
    monitoring_session_id: "00000000-0000-0000-0000-000000000001",
    people: [{
      track_id: id,
      bbox: [10, 10, 30, 80], confidence: 0.95, foot_point: [20, 80], inside_zone: true,
      ppe: {hat: {status: "present", confidence: 0.9}, vest: {status: "present", confidence: 0.9}},
      missing_required_ppe: [],
      active_violations: [{occurrence_id: `00000000-0000-0000-0000-0000000000${id}`, rule_key: `zone_intrusion:${zoneId}`, zone_id: zoneId, is_new: true}],
    }],
    rule: {person_inside_zone: true, machine_state: "running", ppe_profile: "hat_vest_v1", camera_id: "cam_1", zone_id: zoneId, ppe_requirements: {profile: "hat_vest_v1", hat_required: false, vest_required: false}, ppe_alert: false},
  });
  const first = zoneInference(50, "press");
  const second = zoneInference(51, "forklift");
  const firstEvent = pendingEvent(50, first);
  const secondEvent = {...pendingEvent(51, second), zone_id: "forklift"};
  vi.mocked(loadPendingEvents).mockResolvedValueOnce([firstEvent]);
  resultHandler(first);
  expect(await screen.findByText("press")).toBeInTheDocument();
  vi.mocked(loadPendingEvents).mockResolvedValueOnce([secondEvent, firstEvent]);
  resultHandler(second);
  expect(screen.getAllByRole("dialog")).toHaveLength(1);
  expect(screen.queryByText("forklift")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {name: "Đóng pop-up"}));
  expect(await screen.findByText("forklift")).toBeInTheDocument();
  expect(screen.getAllByRole("dialog")).toHaveLength(1);
});
