import {useCallback, useEffect, useRef, useState} from "react";
import type {ChangeEvent, PointerEvent as ReactPointerEvent, RefObject} from "react";
import {InferenceClient} from "../../api/inference-client";
import {saveReviewedEvent} from "../../api/events";
import type {
  EventPayload,
  InferenceResult,
  ModelDetection,
  PersonDetection,
  PpeRequirementUpdate,
  ReviewStatus,
  ZonePoint,
} from "../../types";
import {drawOverlay, findPointAt, normalizedPointerPosition} from "./canvas";

const SAMPLE_INTERVAL_SECONDS = 0.5;
const JPEG_QUALITY = 0.82;
const PREVIEW_CANDIDATES = [0.05, 0.5, 1, 2, 3, 4, 5, 7, 10];
const DEFAULT_PPE_REQUIREMENTS: PpeRequirementUpdate = {
  helmet_required: false,
  safety_glasses_required: false,
  gloves_required: false,
};

interface RuleView {yes: boolean | null; text: string; badge: string}

export interface MonitorView {
  violation: boolean;
  alertTitle: string;
  severity: "NORMAL" | "VIOLATE";
  alertSummary: string;
  reviewMessage: string;
  eventStatus: string;
  confidenceLabel: string;
  confidenceWidth: string;
  zoneRule: RuleView;
  machineRule: RuleView;
  ppeRule: RuleView;
}

const initialView = (machineRunning = true): MonitorView => ({
  violation: false,
  alertTitle: "Chưa có vi phạm",
  severity: "NORMAL",
  alertSummary: "Cảnh báo PPE chỉ áp dụng cho các loại đã được cấu hình bắt buộc.",
  reviewMessage: "Khung hình vi phạm sẽ hiện tại đây",
  eventStatus: "CHƯA CÓ SỰ KIỆN ĐƯỢC LƯU",
  confidenceLabel: "READY",
  confidenceWidth: "12%",
  zoneRule: {yes: null, text: "Chưa phát hiện", badge: "—"},
  machineRule: {
    yes: machineRunning,
    text: machineRunning ? "Machine A đang chạy" : "Machine A đã dừng",
    badge: machineRunning ? "ON" : "OFF"
  },
  ppeRule: {yes: null, text: "Chưa phát hiện", badge: "—"}
});

interface SessionState {
  running: boolean;
  frameSequence: number;
  lastHandledFrame: number;
  lastSampleTime: number;
  violationLatched: boolean;
  previewReady: boolean;
  previewCandidateIndex: number;
}

export function useMonitor() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const captureRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [zonePoints, setZonePoints] = useState<ZonePoint[]>([]);
  const zonePointsRef = useRef<ZonePoint[]>([]);
  const [latestPeople, setLatestPeople] = useState<PersonDetection[]>([]);
  const [latestDetections, setLatestDetections] = useState<ModelDetection[]>([]);
  const [activePpeRequirements, setActivePpeRequirements] = useState<PpeRequirementUpdate>(
    DEFAULT_PPE_REQUIREMENTS,
  );
  const [selectedPoint, setSelectedPoint] = useState<number | null>(null);
  const draggingPoint = useRef<number | null>(null);
  const [selectingZone, setSelectingZone] = useState(false);
  const [machineRunning, setMachineRunning] = useState(true);
  const machineRunningRef = useRef(true);
  const [pendingViolation, setPendingViolation] = useState<InferenceResult | null>(null);
  const pendingViolationRef = useRef<InferenceResult | null>(null);
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [reviewStartedAt, setReviewStartedAt] = useState<number | null>(null);
  const [reviewSaving, setReviewSaving] = useState(false);
  const [view, setView] = useState<MonitorView>(() => initialView());
  const [fileLabel, setFileLabel] = useState("Chưa chọn video");
  const [videoMeta, setVideoMeta] = useState("CHỌN VIDEO ĐỂ BẮT ĐẦU");
  const [previewSrc, setPreviewSrc] = useState<string>();
  const [stageReady, setStageReady] = useState(false);
  const [playbackDisabled, setPlaybackDisabled] = useState(true);
  const [playbackLabel, setPlaybackLabel] = useState("▶ Phát video");
  const [zoneDisabled, setZoneDisabled] = useState(true);
  const [flowStatus, setFlowStatus] = useState("Sẵn sàng");
  const [toast, setToast] = useState<string>();
  const videoUrl = useRef<string | undefined>(undefined);
  const session = useRef<SessionState>({
    running: false,
    frameSequence: 0,
    lastHandledFrame: -1,
    lastSampleTime: -1,
    violationLatched: false,
    previewReady: false,
    previewCandidateIndex: 0
  });
  const resultHandler = useRef<(result: InferenceResult) => void>(() => undefined);
  const failureHandler = useRef<(message: string) => void>(() => undefined);
  const clientRef = useRef<InferenceClient | undefined>(undefined);

  if (!clientRef.current) {
    clientRef.current = new InferenceClient({
      getConfiguration: () => ({
        zone_points: zonePointsRef.current.length === 4 ? zonePointsRef.current : [],
        machine_state: machineRunningRef.current ? "running" : "stopped"
      }),
      onResult: result => resultHandler.current(result),
      onFailure: message => failureHandler.current(message)
    });
  }
  const client = clientRef.current;

  const updateZonePoints = useCallback((points: ZonePoint[]) => {
    zonePointsRef.current = points;
    setZonePoints(points);
  }, []);

  const stopRealtimeInference = useCallback(() => {
    session.current.running = false;
    client.close();
    videoRef.current?.pause();
    setPlaybackLabel("▶ Phát video");
    setPlaybackDisabled(false);
  }, [client]);

  const capturePausedFrame = useCallback(() => {
    const video = videoRef.current;
    const capture = captureRef.current;
    if (!video?.videoWidth || !capture?.width) return;
    capture.getContext("2d")?.drawImage(video, 0, 0, capture.width, capture.height);
    setPreviewSrc(capture.toDataURL("image/jpeg", 0.9));
  }, []);

  const showToast = useCallback((message: string) => setToast(message), []);

  const handleInferenceFailure = useCallback((message: string) => {
    stopRealtimeInference();
    setFlowStatus("Inference đã ngắt kết nối");
    showToast(message);
  }, [showToast, stopRealtimeInference]);

  const handleInferenceResult = useCallback((result: InferenceResult) => {
    if (result.frame_id <= session.current.lastHandledFrame) return;
    session.current.lastHandledFrame = result.frame_id;
    setLatestPeople(result.people);
    setLatestDetections(result.detections ?? []);
    setActivePpeRequirements(result.rule.ppe_requirements);
    const inside = result.people.some(person => person.inside_zone);
    const violation = result.result === "violate";
    setView(current => ({
      ...current,
      violation,
      alertTitle: violation ? current.alertTitle : "Trạng thái bình thường",
      severity: violation ? "VIOLATE" : "NORMAL",
      alertSummary: violation ? current.alertSummary : "Frame hiện tại không vi phạm rule an toàn đã định nghĩa.",
      zoneRule: {yes: inside, text: inside ? "Trong vùng nguy hiểm" : "Ngoài vùng", badge: inside ? "YES" : "NO"},
      ppeRule: buildPpeRule(result),
    }));
    if (!result.review_required) session.current.violationLatched = false;
    if (!result.review_required || session.current.violationLatched) return;
    session.current.violationLatched = true;
    session.current.running = false;
    pendingViolationRef.current = result;
    setPendingViolation(result);
    setIsReviewModalOpen(true);
    const video = videoRef.current;
    if (video) {
      video.pause();
      video.currentTime = result.video_time;
    }
    client.close();
    setPlaybackLabel("▶ Tiếp tục");
    setPlaybackDisabled(true);
    setReviewStartedAt(Date.now());
    setFlowStatus("Chờ xác minh");
    setView(current => ({
      ...current,
      violation: true,
      alertTitle: "Người vào vùng cấm khi máy đang chạy",
      severity: "VIOLATE",
      alertSummary: "Video đã dừng tại frame phát hiện người trong vùng. Hãy xác nhận vi phạm thực tế hoặc bình thường / báo sai.",
      reviewMessage: "Khung hình đang chờ cán bộ an toàn xác minh",
      eventStatus: "Đang chờ xác minh · chưa lưu",
      confidenceLabel: "VIOLATE",
      confidenceWidth: "100%"
    }));
  }, [client]);

  resultHandler.current = handleInferenceResult;
  failureHandler.current = handleInferenceFailure;

  useEffect(() => {
    const canvas = overlayRef.current;
    if (canvas) drawOverlay(canvas, zonePoints, latestPeople, latestDetections, selectedPoint, activePpeRequirements);
  }, [activePpeRequirements, latestDetections, latestPeople, selectedPoint, zonePoints]);

  useEffect(() => {
    if (!toast) return;
    const timeout = window.setTimeout(() => setToast(undefined), 3000);
    return () => clearTimeout(timeout);
  }, [toast]);

  useEffect(() => () => {
    client.close();
    if (videoUrl.current) URL.revokeObjectURL(videoUrl.current);
  }, [client]);

  function handleVideoSelection(event: ChangeEvent<HTMLInputElement>): void {
    const file = event.target.files?.[0];
    const video = videoRef.current;
    if (!file || !video) return;
    client.close();
    video.pause();
    if (videoUrl.current) URL.revokeObjectURL(videoUrl.current);
    videoUrl.current = URL.createObjectURL(file);
    video.src = videoUrl.current;
    video.load();
    Object.assign(session.current, {
      running: false, lastHandledFrame: -1, lastSampleTime: -1,
      violationLatched: false, previewReady: false, previewCandidateIndex: 0
    });
    updateZonePoints([]);
    setLatestPeople([]);
    setLatestDetections([]);
    setSelectedPoint(null);
    pendingViolationRef.current = null;
    setPendingViolation(null);
    setReviewStartedAt(null);
    setPreviewSrc(undefined);
    setStageReady(false);
    setFileLabel(file.name);
    setVideoMeta("ĐANG TẢI VIDEO");
    setPlaybackDisabled(true);
    setZoneDisabled(true);
    setPlaybackLabel("▶ Phát video");
    setFlowStatus("Chờ cấu hình vùng");
    setView(initialView(machineRunningRef.current));
    showToast("Video đã sẵn sàng. Hãy chọn 4 điểm cho vùng nguy hiểm.");
  }

  function handleLoadedMetadata(): void {
    const video = videoRef.current;
    const overlay = overlayRef.current;
    const capture = captureRef.current;
    if (!video || !overlay || !capture) return;
    overlay.width = capture.width = video.videoWidth;
    overlay.height = capture.height = video.videoHeight;
    setStageReady(true);
    setPlaybackDisabled(false);
    setVideoMeta(`${video.videoWidth} × ${video.videoHeight} · ${formatTime(video.duration)}`);
    setSelectingZone(true);
    seekPreviewCandidate();
  }

  function handleSeeked(): void {
    if (session.current.running || pendingViolationRef.current || session.current.previewReady) return;
    const video = videoRef.current;
    if (!video) return;
    if (video.requestVideoFrameCallback) video.requestVideoFrameCallback(() => evaluatePreviewCandidate());
    else window.setTimeout(evaluatePreviewCandidate, 30);
  }

  function evaluatePreviewCandidate(): void {
    const video = videoRef.current;
    if (!video?.videoWidth || session.current.running || session.current.previewReady) return;
    const sample = document.createElement("canvas");
    sample.width = 32;
    sample.height = 18;
    const context = sample.getContext("2d", {willReadFrequently: true});
    if (!context) return;
    context.drawImage(video, 0, 0, sample.width, sample.height);
    const pixels = context.getImageData(0, 0, sample.width, sample.height).data;
    let brightness = 0;
    for (let index = 0; index < pixels.length; index += 4) {
      brightness += (pixels[index] + pixels[index + 1] + pixels[index + 2]) / 3;
    }
    brightness /= pixels.length / 4;
    const candidate = PREVIEW_CANDIDATES[session.current.previewCandidateIndex];
    const lastCandidate = session.current.previewCandidateIndex >= PREVIEW_CANDIDATES.length - 1
      || candidate >= video.duration - 0.01;
    if (brightness < 18 && !lastCandidate) {
      session.current.previewCandidateIndex += 1;
      seekPreviewCandidate();
      return;
    }
    capturePausedFrame();
    session.current.previewReady = true;
    setPlaybackDisabled(false);
    setZoneDisabled(false);
    setFlowStatus("Chờ cấu hình vùng");
  }

  function seekPreviewCandidate(): void {
    const video = videoRef.current;
    if (!video) return;
    const candidate = PREVIEW_CANDIDATES[session.current.previewCandidateIndex];
    video.currentTime = Math.min(candidate, Math.max(0, video.duration - 0.01));
  }

  async function handlePlayback(): Promise<void> {
    const video = videoRef.current;
    if (!video?.src || pendingViolationRef.current) return;
    if (!video.paused) {
      stopPreviewPlayback();
      return;
    }
    session.current.previewReady = true;
    setSelectingZone(false);
    setPreviewSrc(undefined);
    setSelectedPoint(null);
    setPlaybackLabel("■ Dừng video");
    session.current.running = true;
    session.current.frameSequence = 0;
    session.current.lastHandledFrame = -1;
    session.current.lastSampleTime = -1;
    setFlowStatus("Đang inference realtime");
    setView(current => ({...current, confidenceLabel: "RUNNING", confidenceWidth: "70%"}));
    if (video.ended) video.currentTime = 0;
    if (session.current.running) {
      setFlowStatus("Đang kết nối inference");
      try {
        await client.connect();
        setFlowStatus("Đang inference realtime");
      } catch (error) {
        client.close();
        session.current.running = false;
        setPlaybackLabel("▶ Phát video");
        setFlowStatus("Không thể kết nối inference");
        showToast(error instanceof Error ? error.message : "Không thể kết nối inference");
        return;
      }
    }
    try {
      await video.play();
      if (session.current.running) requestAnimationFrame(sampleFrameLoop);
    } catch {
      stopRealtimeInference();
      showToast("Trình duyệt không thể phát video đã chọn.");
    }
  }

  function sampleFrameLoop(): void {
    const video = videoRef.current;
    const capture = captureRef.current;
    if (!session.current.running || !video || video.ended || !capture) return;
    const sampleDue = video.currentTime - session.current.lastSampleTime >= SAMPLE_INTERVAL_SECONDS;
    if (client.canSend && sampleDue) {
      session.current.lastSampleTime = video.currentTime;
      capture.getContext("2d")?.drawImage(video, 0, 0, capture.width, capture.height);
      const frameId = session.current.frameSequence++;
      const videoTime = video.currentTime;
      capture.toBlob(blob => {
        if (blob && session.current.running) client.sendFrame(frameId, videoTime, blob);
      }, "image/jpeg", JPEG_QUALITY);
    }
    if (session.current.running) requestAnimationFrame(sampleFrameLoop);
  }

  function stopPreviewPlayback(): void {
    stopRealtimeInference();
    capturePausedFrame();
    setSelectingZone(true);
    setFlowStatus("Chọn hoặc điều chỉnh 4 điểm");
  }

  function handleEnded(): void {
    session.current.running = false;
    client.close();
    setPlaybackLabel("↻ Phát lại");
    capturePausedFrame();
  }

  function toggleMachine(): void {
    const running = !machineRunningRef.current;
    machineRunningRef.current = running;
    setMachineRunning(running);
    setView(current => ({
      ...current,
      machineRule: {yes: running, text: running ? "Machine A đang chạy" : "Machine A đã dừng", badge: running ? "ON" : "OFF"}
    }));
    client.updateConfiguration();
  }

  function resetZone(): void {
    stopRealtimeInference();
    updateZonePoints([]);
    setSelectedPoint(null);
    setSelectingZone(true);
    setFlowStatus("Chờ cấu hình vùng");
  }

  function toggleZoneEditing(): void {
    if (!videoRef.current?.paused) {
      stopPreviewPlayback();
      setSelectingZone(true);
      return;
    }
    setSelectingZone(current => !current);
  }

  function handlePointerDown(event: ReactPointerEvent<HTMLCanvasElement>): void {
    const video = videoRef.current;
    if (!selectingZone || !video?.videoWidth || !video.paused) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const position = normalizedPointerPosition(event.clientX, event.clientY, rect);
    const hit = findPointAt(zonePointsRef.current, position, rect);
    if (hit !== null) {
      setSelectedPoint(hit);
      draggingPoint.current = hit;
      event.currentTarget.setPointerCapture?.(event.pointerId);
    } else if (zonePointsRef.current.length < 4) {
      updateZonePoints([...zonePointsRef.current, position]);
      setSelectedPoint(zonePointsRef.current.length - 1);
    } else setSelectedPoint(null);
    setFlowStatus(zonePointsRef.current.length === 4 ? "Zone sẵn sàng · inference realtime" : "Zone tùy chọn · detection vẫn chạy khi phát video");
  }

  function handlePointerMove(event: ReactPointerEvent<HTMLCanvasElement>): void {
    if (draggingPoint.current === null) return;
    const points = [...zonePointsRef.current];
    points[draggingPoint.current] = normalizedPointerPosition(event.clientX, event.clientY, event.currentTarget.getBoundingClientRect());
    updateZonePoints(points);
  }

  function handlePointerUp(event: ReactPointerEvent<HTMLCanvasElement>): void {
    if (draggingPoint.current !== null) event.currentTarget.releasePointerCapture?.(event.pointerId);
    draggingPoint.current = null;
  }

  function deleteSelectedPoint(): void {
    if (selectedPoint === null) return;
    updateZonePoints(zonePointsRef.current.filter((_, index) => index !== selectedPoint));
    setSelectedPoint(null);
    setSelectingZone(true);
    setFlowStatus("Chờ đủ 4 điểm");
  }

  async function review(status: ReviewStatus): Promise<void> {
    const pending = pendingViolationRef.current;
    if (!pending) return;
    setReviewSaving(true);
    try {
      await saveReviewedEvent(buildEventPayload(status, pending, zonePointsRef.current, machineRunningRef.current));
      pendingViolationRef.current = null;
      setPendingViolation(null);
      setIsReviewModalOpen(false);
      setReviewStartedAt(null);
      setPlaybackDisabled(false);
      setFlowStatus("Đã đóng xác minh");
      setView(initialView(machineRunningRef.current));
      showToast("Kết quả xác minh và khung hình đã được lưu.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Không thể lưu kết quả xác minh");
    } finally {
      setReviewSaving(false);
    }
  }

  const selectedPointPosition = selectedPoint === null ? undefined : zonePoints[selectedPoint];
  const timer = useReviewTimer(reviewStartedAt);

  return {
    refs: {videoRef, overlayRef, captureRef, fileInputRef},
    state: {
      zonePoints, selectingZone, machineRunning, pendingViolation, isReviewModalOpen, reviewSaving, view,
      fileLabel, videoMeta, previewSrc, stageReady, playbackDisabled, playbackLabel,
      zoneDisabled, flowStatus, toast, selectedPointPosition, timer,
      latestPeople, latestDetections, peopleCount: latestPeople.length,
      ppeRequirementCount: Object.values(activePpeRequirements).filter(Boolean).length,
    },
    actions: {
      openFilePicker: () => fileInputRef.current?.click(), handleVideoSelection,
      handleLoadedMetadata, handleSeeked, handlePlayback, handleEnded, toggleMachine,
      resetZone, toggleZoneEditing, handlePointerDown, handlePointerMove,
      handlePointerUp, deleteSelectedPoint, review,
      openReviewModal: () => setIsReviewModalOpen(true),
      closeReviewModal: () => setIsReviewModalOpen(false),
    }
  };
}

export function buildPpeRule(result: InferenceResult): RuleView {
  const requirements = result.rule.ppe_requirements;
  const requiredLabels = [
    requirements.helmet_required ? "mũ" : null,
    requirements.safety_glasses_required ? "kính" : null,
    requirements.gloves_required ? "găng" : null,
  ].filter((label): label is string => label !== null);
  if (!requiredLabels.length) return {yes: null, text: "Không yêu cầu PPE", badge: "OFF"};

  const missing = [...new Set(result.people.flatMap(person => person.missing_required_ppe))];
  const ppeLabel: Record<string, string> = {helmet: "mũ", safety_glasses: "kính", gloves: "găng"};
  if (missing.length) return {yes: false, text: `Thiếu: ${missing.map(item => ppeLabel[item]).join(", ")}`, badge: "MISS"};

  const hasUnknown = result.people.some(person =>
    requiredLabels.some(label => {
      const item = label === "mũ" ? "helmet" : label === "kính" ? "safety_glasses" : "gloves";
      return person.ppe[item].status === "unknown";
    }),
  );
  if (hasUnknown) return {yes: null, text: `Đang kiểm tra ${requiredLabels.join(", ")}`, badge: "CHECK"};
  return {yes: true, text: `Đủ PPE: ${requiredLabels.join(", ")}`, badge: "OK"};
}

export function buildEventPayload(
  status: ReviewStatus,
  pending: InferenceResult,
  zonePoints: ZonePoint[],
  machineRunning: boolean
): EventPayload {
  return {
    zone_id: "zone_01",
    camera_id: "uploaded_video",
    event_type: "zone_intrusion_while_machine_running",
    severity: "high",
    status,
    acknowledged_by: "Safety Officer",
    snapshot_data: pending.snapshot_data,
    details: {
      inference_result: pending.result,
      review_result: status === "acknowledged" ? "actual_violation" : "normal",
      machine_state: machineRunning ? "running" : "stopped",
      video_timestamp_seconds: pending.video_time,
      people: pending.people,
      zone_points: zonePoints
    }
  };
}

function useReviewTimer(startedAt: number | null): string {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!startedAt) return;
    setNow(Date.now());
    const interval = window.setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(interval);
  }, [startedAt]);
  if (!startedAt) return "00:00";
  const seconds = Math.floor((now - startedAt) / 1000);
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

function formatTime(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
}

export type MonitorRefs = {
  videoRef: RefObject<HTMLVideoElement | null>;
  overlayRef: RefObject<HTMLCanvasElement | null>;
  captureRef: RefObject<HTMLCanvasElement | null>;
  fileInputRef: RefObject<HTMLInputElement | null>;
};
