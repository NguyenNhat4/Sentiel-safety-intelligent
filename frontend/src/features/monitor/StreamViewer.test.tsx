import {fireEvent, render, screen, waitFor} from "@testing-library/react";
import {beforeEach, expect, it, vi} from "vitest";
import {CameraDetectionClient} from "../../api/camera-detection-client";
import {listCameraConfigurations} from "../../api/camera-configurations";
import {listMediaAssets} from "../../api/media-assets";
import {listCameraSessions, replayCamera, runSimulation} from "../../api/simulation";
import type {CameraInferenceResult} from "../../types";
import {StreamViewer} from "./StreamViewer";

let resultHandler: (result: CameraInferenceResult) => void = () => undefined;
vi.mock("../../api/auth", () => ({getAccessToken: () => "token"}));
vi.mock("../../api/camera-configurations", () => ({listCameraConfigurations: vi.fn()}));
vi.mock("../../api/media-assets", () => ({listMediaAssets: vi.fn()}));
vi.mock("../../api/simulation", () => ({listCameraSessions: vi.fn(), replayCamera: vi.fn(), runSimulation: vi.fn()}));
vi.mock("../../api/camera-detection-client", () => ({CameraDetectionClient: vi.fn(function(options: {onResult: typeof resultHandler}) { resultHandler = options.onResult; return {connect: vi.fn().mockResolvedValue(undefined), close: vi.fn()}; })}));
vi.mock("../media/AuthenticatedMedia", () => ({AuthenticatedMedia: ({label, playbackKey, onEnded}: {label: string; playbackKey: string; onEnded: () => void}) => <button aria-label={label} data-playback-key={playbackKey} onClick={event => { event.stopPropagation(); onEnded(); }}>media</button>}));

const session = {id: "session-current", camera_id: "cam_1", asset_id: "asset-1", media_type: "video" as const, status: "RUNNING" as const, config_revision: 1, inference_fps: 1.5, started_at: "2026-08-23T00:00:00Z", running_at: "2026-08-23T00:00:01Z", completed_at: null, error_code: null};
const result = (sessionId: string, fps: number): CameraInferenceResult => ({type: "camera_inference_result", camera_id: "cam_1", session_id: sessionId, asset_id: "asset-1", media_type: "video", video_time: 1, session_status: "RUNNING", inference_fps: fps, source_timestamp_ms: 1, captured_at: 1, frame_width: 100, frame_height: 100, frame_id: 1, result: "normal", review_required: false, people: [], rule: {} as CameraInferenceResult["rule"]});

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(listCameraConfigurations).mockResolvedValue([{camera_id: "cam_1", revision: 1, asset_id: "asset-1", machine_state: "stopped", zones: [], updated_at: null}]);
  vi.mocked(listMediaAssets).mockResolvedValue([{id: "asset-1", display_name: "Demo", media_type: "video", status: "READY", content_type: "video/mp4", size_bytes: 10, uploaded_at: "2026-08-23T00:00:00Z", assigned_camera_id: "cam_1", can_delete: false}]);
  vi.mocked(listCameraSessions).mockResolvedValue([session]);
  vi.mocked(runSimulation).mockResolvedValue({sessions: [{...session, id: "session-run", status: "STARTING"}], errors: {}});
  vi.mocked(replayCamera).mockResolvedValue({...session, id: "session-replay", status: "STARTING"});
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
  fireEvent.click(screen.getByRole("button", {name: "Replay Camera 1"}));
  await waitFor(() => expect(replayCamera).toHaveBeenCalledWith("cam_1"));
  expect(screen.getByRole("button", {name: "Media Camera 1"})).toHaveAttribute("data-playback-key", "session-replay");
});

it("does not expose run or configuration actions to system admins", async () => {
  render(<StreamViewer role="system_admin" onConfigure={vi.fn()} />);
  await screen.findByRole("heading", {name: "Camera 1"});
  expect(screen.queryByRole("button", {name: "Chạy mô phỏng"})).not.toBeInTheDocument();
  expect(screen.queryByRole("button", {name: "Cấu hình Camera 1"})).not.toBeInTheDocument();
  expect(CameraDetectionClient).toHaveBeenCalled();
});
