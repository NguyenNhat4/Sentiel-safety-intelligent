import {useCallback, useEffect, useRef, useState} from "react";
import type {ChangeEvent, PointerEvent as ReactPointerEvent, RefObject} from "react";
import {InferenceClient} from "../../api/inference-client";
import {saveReviewedEvent, saveReviewedEventBatch} from "../../api/events";
import {loadMonitoringZones, saveMonitoringZones} from "../../api/monitoring-zones";
import type {
  EventBatchPayload,
  EventPayload,
  InferenceResult,
  ModelDetection,
  MonitoringZone,
  PersonDetection,
  PpeRequirementUpdate,
  ReviewStatus,
  ZonePoint,
} from "../../types";
import {drawOverlay, normalizedPointerPosition} from "./canvas";
import {createZoneDraft, findZonePointAt, zoneGeometryConflict} from "./zone-editor";

const SAMPLE_INTERVAL_SECONDS = 0.1;
const JPEG_QUALITY = 1.0;
const PREVIEW_CANDIDATES = [0.05, 0.5, 1, 2, 3, 4, 5, 7, 10];
const DEFAULT_PPE_REQUIREMENTS: PpeRequirementUpdate = {
  profile: "hat_vest_v1",
  hat_required: false,
  vest_required: false,
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

const initialView = (machineIsRunning = true): MonitorView => ({
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
    yes: machineIsRunning,
    text: machineIsRunning ? "Máy đang chạy" : "Máy đã dừng",
    badge: machineIsRunning ? "ON" : "OFF"
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
  monitoringSessionId: string;
}

export function captureVideoSnapshot(video: HTMLVideoElement, capture: HTMLCanvasElement): string | undefined {
  if (!video.videoWidth || !video.videoHeight) return undefined;
  capture.width = video.videoWidth;
  capture.height = video.videoHeight;
  const context = capture.getContext("2d");
  if (!context) return undefined;
  context.drawImage(video, 0, 0, capture.width, capture.height);
  return capture.toDataURL("image/jpeg", JPEG_QUALITY);
}

export function useMonitor() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const captureRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [zones, setZones] = useState<MonitoringZone[]>([]);
  const zonesRef = useRef<MonitoringZone[]>([]);
  const appliedZonesRef = useRef<MonitoringZone[]>([]);
  const [zoneRevision, setZoneRevision] = useState(0);
  const zoneRevisionRef = useRef(0);
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>(null);
  const [drawingZoneId, setDrawingZoneId] = useState<string | null>(null);
  const [newDraftZoneId, setNewDraftZoneId] = useState<string | null>(null);
  const [zoneSaving, setZoneSaving] = useState(false);
  const [zoneHydrated, setZoneHydrated] = useState(false);
  const [latestPeople, setLatestPeople] = useState<PersonDetection[]>([]);
  const [latestDetections, setLatestDetections] = useState<ModelDetection[]>([]);
  const [activePpeRequirements, setActivePpeRequirements] = useState<PpeRequirementUpdate>(
    DEFAULT_PPE_REQUIREMENTS,
  );
  const [selectedPoint, setSelectedPoint] = useState<number | null>(null);
  const draggingPoint = useRef<number | null>(null);
  const draggingZoneId = useRef<string | null>(null);
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
    previewCandidateIndex: 0,
    monitoringSessionId: crypto.randomUUID()
  });
  const resultHandler = useRef<(result: InferenceResult) => void>(() => undefined);
  const failureHandler = useRef<(message: string) => void>(() => undefined);
  const clientRef = useRef<InferenceClient | undefined>(undefined);

  if (!clientRef.current) {
    clientRef.current = new InferenceClient({
      getConfiguration: () => ({
        zones: appliedZonesRef.current,
        zone_revision: zoneRevisionRef.current,
        camera_id: "uploaded_video",
        machine_state: machineRunningRef.current ? "running" : "stopped",
        monitoring_session_id: session.current.monitoringSessionId
      }),
      onResult: result => resultHandler.current(result),
      onFailure: message => failureHandler.current(message)
    });
  }
  const client = clientRef.current;

  const updateZones = useCallback((nextZones: MonitoringZone[]) => {
    zonesRef.current = nextZones;
    setZones(nextZones);
  }, []);

  const updateZone = useCallback((zoneId: string, change: (zone: MonitoringZone) => MonitoringZone) => {
    updateZones(zonesRef.current.map(zone => zone.zone_id === zoneId ? change(zone) : zone));
  }, [updateZones]);

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
    if (!video || !capture) return;
    const snapshot = captureVideoSnapshot(video, capture);
    if (snapshot) setPreviewSrc(snapshot);
  }, []);

  const showToast = useCallback((message: string) => setToast(message), []);

  const handleInferenceFailure = useCallback((message: string) => {
    stopRealtimeInference();
    setFlowStatus("Inference đã ngắt kết nối");
    showToast(message);
  }, [showToast, stopRealtimeInference]);

  function handleInferenceResult(result: InferenceResult): void {
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
    const video = videoRef.current;
    video?.pause();
    client.close();
    const reviewCopy = buildReviewCopy(result);
    setPlaybackLabel("▶ Tiếp tục");
    setPlaybackDisabled(true);
    setFlowStatus("Chờ xác minh");
    setView(current => ({
      ...current,
      violation: true,
      alertTitle: reviewCopy.title,
      severity: "VIOLATE",
      alertSummary: reviewCopy.summary,
      reviewMessage: reviewCopy.reviewMessage,
      eventStatus: "Đang chờ xác minh · chưa lưu",
      confidenceLabel: "VIOLATE",
      confidenceWidth: "100%"
    }));
    freezeAtViolationFrame(result);
  }

  resultHandler.current = handleInferenceResult;
  failureHandler.current = handleInferenceFailure;

  useEffect(() => {
    const canvas = overlayRef.current;
    if (canvas) drawOverlay(
      canvas,
      zones,
      latestPeople,
      latestDetections,
      selectedZoneId,
      selectedPoint,
      activePpeRequirements,
    );
  }, [activePpeRequirements, latestDetections, latestPeople, selectedPoint, selectedZoneId, zones]);

  useEffect(() => {
    let active = true;
    loadMonitoringZones("uploaded_video")
      .then(collection => {
        if (!active) return;
        appliedZonesRef.current = collection.zones;
        zoneRevisionRef.current = collection.revision;
        setZoneRevision(collection.revision);
        updateZones(collection.zones);
        setSelectedZoneId(collection.zones[0]?.zone_id ?? null);
        setZoneHydrated(true);
      })
      .catch(error => {
        if (active) {
          setZoneHydrated(true);
          showToast(error instanceof Error ? error.message : "Không thể tải cấu hình vùng");
        }
      });
    return () => { active = false; };
  }, [showToast, updateZones]);

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
      violationLatched: false, previewReady: false, previewCandidateIndex: 0,
      frameSequence: 0, monitoringSessionId: crypto.randomUUID()
    });
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
    setFlowStatus(zonesRef.current.length ? "Đã khôi phục cấu hình vùng" : "Chờ tạo vùng");
    setView(initialView(machineRunningRef.current));
    showToast("Video đã sẵn sàng. Bấm Tạo vùng nếu cần thêm khu vực nguy hiểm.");
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
    setZoneDisabled(false);
    setVideoMeta(`${video.videoWidth} × ${video.videoHeight} · ${formatTime(video.duration)}`);
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
    setPreviewSrc(undefined);
    setSelectedPoint(null);
    setPlaybackLabel("■ Dừng video");
    session.current.running = true;
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

  function freezeAtViolationFrame(result: InferenceResult): void {
    const video = videoRef.current;
    const capture = captureRef.current;
    if (!video || !capture || !video.videoWidth) {
      openViolationReview(result, result.snapshot_data);
      return;
    }

    let completed = false;
    const finish = () => {
      if (completed) return;
      completed = true;
      window.clearTimeout(fallbackTimer);
      video.removeEventListener("seeked", renderStoppedFrame);
      openViolationReview(result, captureVideoSnapshot(video, capture) ?? result.snapshot_data);
    };
    const renderStoppedFrame = () => {
      if (video.requestVideoFrameCallback) video.requestVideoFrameCallback(() => finish());
      else window.requestAnimationFrame(finish);
    };

    video.addEventListener("seeked", renderStoppedFrame, {once: true});
    const fallbackTimer = window.setTimeout(finish, 800);
    if (Math.abs(video.currentTime - result.video_time) < 0.01) renderStoppedFrame();
    else video.currentTime = result.video_time;
  }

  function openViolationReview(result: InferenceResult, snapshotData?: string): void {
    const reviewedFrame = snapshotData ? {...result, snapshot_data: snapshotData} : result;
    pendingViolationRef.current = reviewedFrame;
    setPendingViolation(reviewedFrame);
    setIsReviewModalOpen(true);
    setReviewStartedAt(Date.now());
  }

  function stopPreviewPlayback(): void {
    stopRealtimeInference();
    capturePausedFrame();
    setFlowStatus("Video đã dừng · có thể chỉnh vùng");
  }

  function handleEnded(): void {
    session.current.running = false;
    client.close();
    capturePausedFrame();
    const video = videoRef.current;
    if (video) video.currentTime = 0;
    setPlaybackLabel("↻ Phát lại");
    setPlaybackDisabled(false);
    setFlowStatus("Video đã kết thúc · bấm Phát lại để chạy lại cùng video");
  }

  function toggleMachine(): void {
    const running = !machineRunningRef.current;
    machineRunningRef.current = running;
    setMachineRunning(running);
    setView(current => ({
      ...current,
      machineRule: {yes: running, text: running ? "Máy đang chạy" : "Máy đã dừng", badge: running ? "ON" : "OFF"}
    }));
    client.updateConfiguration();
  }

  function resetZone(): void {
    if (!selectedZoneId) return;
    updateZone(selectedZoneId, zone => ({...zone, points: []}));
    setSelectedPoint(null);
    setDrawingZoneId(selectedZoneId);
    setFlowStatus("Vẽ lại vùng · 0/4");
  }

  function createZone(): void {
    if (drawingZoneId) return;
    if (!videoRef.current?.paused) stopPreviewPlayback();
    const draft = createZoneDraft(zonesRef.current);
    updateZones([...zonesRef.current, draft]);
    setSelectedZoneId(draft.zone_id);
    setNewDraftZoneId(draft.zone_id);
    setDrawingZoneId(draft.zone_id);
    setSelectedPoint(null);
    setFlowStatus(`${draft.display_name} · 0/4`);
  }

  function cancelZoneCreation(): void {
    if (!newDraftZoneId) return;
    updateZones(zonesRef.current.filter(zone => zone.zone_id !== newDraftZoneId));
    setNewDraftZoneId(null);
    setDrawingZoneId(null);
    setSelectedZoneId(appliedZonesRef.current[0]?.zone_id ?? null);
    setSelectedPoint(null);
    setFlowStatus("Đã hủy tạo vùng");
  }

  function deleteSelectedZone(): void {
    if (zoneSaving) return;
    const selectedIndex = zonesRef.current.findIndex(zone => zone.zone_id === selectedZoneId);
    if (selectedIndex === -1) return;

    const selected = zonesRef.current[selectedIndex];
    const confirmed = window.confirm(
      `Xóa "${selected.display_name}" khỏi cấu hình đang chỉnh sửa? Bấm Lưu cấu hình vùng để cập nhật database.`
    );
    if (!confirmed) return;

    const remaining = zonesRef.current
      .filter(zone => zone.zone_id !== selected.zone_id)
      .map((zone, order) => ({...zone, order}));
    const nextSelectedZoneId = remaining[Math.min(selectedIndex, remaining.length - 1)]?.zone_id ?? null;

    updateZones(remaining);
    setSelectedZoneId(nextSelectedZoneId);
    if (newDraftZoneId === selected.zone_id) setNewDraftZoneId(null);
    setDrawingZoneId(null);
    setSelectedPoint(null);
    draggingPoint.current = null;
    draggingZoneId.current = null;
    setFlowStatus(`Đã xóa ${selected.display_name} trên UI · chưa lưu`);
    showToast(`Đã xóa ${selected.display_name} trên UI. Bấm Lưu cấu hình vùng để cập nhật database.`);
  }

  async function saveZones(): Promise<void> {
    const incomplete = zonesRef.current.find(zone => zone.points.length !== 4);
    if (incomplete) {
      showToast(`${incomplete.display_name} cần đủ 4 điểm trước khi lưu.`);
      return;
    }
    const conflict = zoneGeometryConflict(zonesRef.current);
    if (conflict) {
      showToast(`Các vùng đang xung đột: ${conflict[0]}, ${conflict[1]}`);
      return;
    }
    setZoneSaving(true);
    try {
      const collection = await saveMonitoringZones("uploaded_video", zoneRevisionRef.current, zonesRef.current);
      appliedZonesRef.current = collection.zones;
      zoneRevisionRef.current = collection.revision;
      setZoneRevision(collection.revision);
      updateZones(collection.zones);
      setNewDraftZoneId(null);
      setDrawingZoneId(null);
      client.updateConfiguration();
      setFlowStatus(`Đã lưu ${collection.zones.length} vùng · revision ${collection.revision}`);
      showToast("Đã lưu cấu hình vùng.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "Không thể lưu cấu hình vùng");
    } finally {
      setZoneSaving(false);
    }
  }

  function handlePointerDown(event: ReactPointerEvent<HTMLCanvasElement>): void {
    const video = videoRef.current;
    if (!video?.videoWidth || !video.paused) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const position = normalizedPointerPosition(event.clientX, event.clientY, rect);
    const hit = findZonePointAt(zonesRef.current, position, rect);
    if (hit !== null) {
      setSelectedZoneId(hit.zoneId);
      setSelectedPoint(hit.pointIndex);
      draggingPoint.current = hit.pointIndex;
      draggingZoneId.current = hit.zoneId;
      event.currentTarget.setPointerCapture?.(event.pointerId);
      return;
    }
    if (!drawingZoneId) {
      setSelectedPoint(null);
      return;
    }
    const drawing = zonesRef.current.find(zone => zone.zone_id === drawingZoneId);
    if (!drawing || drawing.points.length >= 4) return;
    const points = [...drawing.points, position];
    updateZone(drawingZoneId, zone => ({...zone, points}));
    setSelectedPoint(points.length - 1);
    if (points.length === 4) {
      setDrawingZoneId(null);
      setNewDraftZoneId(null);
    }
    setFlowStatus(`${drawing.display_name} · ${points.length}/4${points.length === 4 ? " · sẵn sàng lưu" : ""}`);
  }

  function handlePointerMove(event: ReactPointerEvent<HTMLCanvasElement>): void {
    if (draggingPoint.current === null || !draggingZoneId.current) return;
    const pointIndex = draggingPoint.current;
    updateZone(draggingZoneId.current, zone => {
      const points = [...zone.points];
      points[pointIndex] = normalizedPointerPosition(
        event.clientX,
        event.clientY,
        event.currentTarget.getBoundingClientRect(),
      );
      return {...zone, points};
    });
  }

  function handlePointerUp(event: ReactPointerEvent<HTMLCanvasElement>): void {
    if (draggingPoint.current !== null) event.currentTarget.releasePointerCapture?.(event.pointerId);
    draggingPoint.current = null;
    draggingZoneId.current = null;
  }

  function deleteSelectedPoint(): void {
    if (selectedPoint === null || !selectedZoneId) return;
    updateZone(selectedZoneId, zone => ({...zone, points: zone.points.filter((_, index) => index !== selectedPoint)}));
    setSelectedPoint(null);
    setDrawingZoneId(selectedZoneId);
    setFlowStatus("Chờ đủ 4 điểm");
  }

  async function review(status: ReviewStatus): Promise<void> {
    const pending = pendingViolationRef.current;
    if (!pending) return;
    setReviewSaving(true);
    try {
      const batch = buildEventBatchPayload(status, pending, appliedZonesRef.current);
      if (batch) await saveReviewedEventBatch(batch);
      else await saveReviewedEvent(buildEventPayload(status, pending, [], machineRunningRef.current));
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

  const selectedZone = zones.find(zone => zone.zone_id === selectedZoneId);
  const selectedPointPosition = selectedPoint === null ? undefined : selectedZone?.points[selectedPoint];
  const timer = useReviewTimer(reviewStartedAt);

  return {
    refs: {videoRef, overlayRef, captureRef, fileInputRef},
    state: {
      zones, zoneRevision, zoneHydrated, selectedZoneId, selectedZone, drawingZoneId, newDraftZoneId, zoneSaving,
      machineRunning,
      pendingViolation, isReviewModalOpen, reviewSaving, view,
      fileLabel, videoMeta, previewSrc, stageReady, playbackDisabled, playbackLabel,
      zoneDisabled, flowStatus, toast, selectedPointPosition, timer,
      latestPeople, latestDetections, peopleCount: latestPeople.length,
      ppeRequirementCount: Number(activePpeRequirements.hat_required) + Number(activePpeRequirements.vest_required),
    },
    actions: {
      openFilePicker: () => fileInputRef.current?.click(), handleVideoSelection,
      handleLoadedMetadata, handleSeeked, handlePlayback, handleEnded, toggleMachine,
      resetZone, createZone, cancelZoneCreation, deleteSelectedZone, saveZones,
      selectZone: (zoneId: string) => { setSelectedZoneId(zoneId); setSelectedPoint(null); },
      updateSelectedZoneName: (displayName: string) => selectedZoneId
        && updateZone(selectedZoneId, zone => ({...zone, display_name: displayName})),
      toggleSelectedZoneEnabled: () => selectedZoneId
        && updateZone(selectedZoneId, zone => ({...zone, enabled: !zone.enabled})),
      handlePointerDown, handlePointerMove,
      handlePointerUp, deleteSelectedPoint, review,
      openReviewModal: () => setIsReviewModalOpen(true),
      closeReviewModal: () => setIsReviewModalOpen(false),
    }
  };
}

export function buildPpeRule(result: InferenceResult): RuleView {
  const requirements = result.rule.ppe_requirements;
  const requiredLabels = [
    requirements.hat_required ? "mũ bảo hộ" : null,
    requirements.vest_required ? "áo phản quang" : null,
  ].filter((label): label is string => label !== null);
  if (!requiredLabels.length) return {yes: null, text: "Không yêu cầu PPE", badge: "OFF"};

  const missing = [...new Set(result.people.flatMap(person => person.missing_required_ppe))];
  const ppeLabel: Record<string, string> = {hat: "mũ bảo hộ", vest: "áo phản quang"};
  if (missing.length) return {yes: false, text: `Thiếu: ${missing.map(item => ppeLabel[item]).join(", ")}`, badge: "MISS"};

  const hasUnknown = result.people.some(person =>
    requiredLabels.some(label => {
      const item = label === "mũ bảo hộ" ? "hat" : "vest";
      return person.ppe[item].status === "unknown";
    }),
  );
  if (hasUnknown) return {yes: null, text: `Đang kiểm tra ${requiredLabels.join(", ")}`, badge: "CHECK"};
  return {yes: true, text: `Đủ PPE: ${requiredLabels.join(", ")}`, badge: "OK"};
}

export function buildReviewCopy(result: InferenceResult): {
  title: string;
  summary: string;
  reviewMessage: string;
} {
  const ppeLabels: Record<"hat" | "vest", string> = {
    hat: "mũ bảo hộ",
    vest: "áo phản quang",
  };
  const ppeReasons = result.people.flatMap((person, index) => {
    if (!person.missing_required_ppe.length) return [];
    return `Người #${index + 1} thiếu ${person.missing_required_ppe.map(item => ppeLabels[item]).join(", ")}`;
  });
  const activeZones = result.rule.zone_results?.filter(zone => zone.violation) ?? [];
  const zoneReasons = activeZones.length
    ? activeZones.map(zone => `Vùng cấm "${zone.zone_id}" có người xâm nhập`)
    : result.rule.person_inside_zone
      ? ["Có người trong vùng cấm"]
      : [];
  const reasons = [...ppeReasons, ...zoneReasons];

  if (!reasons.length) {
    return {
      title: "Cần xác minh vi phạm an toàn",
      summary: "Rule an toàn đã kích hoạt nhưng chưa có lý do chi tiết từ frame. Hãy xác minh thủ công.",
      reviewMessage: "Khung hình đang chờ cán bộ an toàn xác minh",
    };
  }
  const hasPpeViolation = ppeReasons.length > 0;
  const hasZoneViolation = zoneReasons.length > 0;
  const title = hasPpeViolation && hasZoneViolation
    ? "Thiếu PPE và có người vào vùng cấm"
    : hasPpeViolation
      ? "Thiếu PPE bắt buộc"
      : "Có người vào vùng cấm";

  return {
    title,
    summary: `${reasons.join(". ")}. Video đã dừng để xác minh vi phạm thực tế hoặc báo sai.`,
    reviewMessage: `${reasons.length} lỗi cần xác minh: ${reasons.join("; ")}`,
  };
}

export function buildEventPayload(
  status: ReviewStatus,
  pending: InferenceResult,
  zonePoints: ZonePoint[],
  machineIsRunning: boolean
): EventPayload {
  const occurrenceIds = [...new Set(
    pending.people.flatMap(person =>
      person.active_violations?.filter(item => item.is_new).map(item => item.occurrence_id) ?? []
    ),
  )];
  return {
    zone_id: "zone_01",
    camera_id: "uploaded_video",
    event_type: "zone_intrusion",
    severity: "high",
    status,
    acknowledged_by: "Safety Officer",
    snapshot_data: pending.snapshot_data,
    snapshot_people: pending.people,
    snapshot_detections: pending.detections ?? [],
    monitoring_session_id: pending.monitoring_session_id,
    occurrence_ids: occurrenceIds,
    details: {
      inference_result: pending.result,
      review_result: status === "acknowledged" ? "actual_violation" : "normal",
      machine_state: machineIsRunning ? "running" : "stopped",
      video_timestamp_seconds: pending.video_time,
      people: pending.people,
      zone_points: zonePoints
    }
  };
}

export function buildEventBatchPayload(
  status: ReviewStatus,
  pending: InferenceResult,
  zones: MonitoringZone[],
): EventBatchPayload | null {
  if (!pending.monitoring_session_id) return null;
  const occurrencesByZone = new Map<string, string[]>();
  pending.people.forEach(person => {
    person.active_violations?.forEach(violation => {
      if (!violation.is_new || !violation.zone_id || !violation.rule_key.startsWith("zone_intrusion:")) return;
      const ids = occurrencesByZone.get(violation.zone_id) ?? [];
      if (!ids.includes(violation.occurrence_id)) ids.push(violation.occurrence_id);
      occurrencesByZone.set(violation.zone_id, ids);
    });
  });
  if (!occurrencesByZone.size) return null;
  const byId = new Map(zones.map(zone => [zone.zone_id, zone]));
  return {
    monitoring_session_id: pending.monitoring_session_id,
    camera_id: "uploaded_video",
    status,
    acknowledged_by: "Safety Officer",
    snapshot_data: pending.snapshot_data,
    snapshot_people: pending.people,
    snapshot_detections: pending.detections ?? [],
    events: [...occurrencesByZone.entries()]
      .sort((left, right) => (byId.get(left[0])?.order ?? 0) - (byId.get(right[0])?.order ?? 0))
      .map(([zoneId, occurrenceIds]) => ({
        zone_id: zoneId,
        event_type: "zone_intrusion" as const,
        severity: "critical",
        occurrence_ids: occurrenceIds,
        details: {
          review_result: status === "acknowledged" ? "actual_violation" : "normal",
          machine_state: byId.get(zoneId)?.machine_state ?? "running",
          video_timestamp_seconds: pending.video_time,
          people: pending.people,
          zone_points: byId.get(zoneId)?.points ?? [],
        },
      })),
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
