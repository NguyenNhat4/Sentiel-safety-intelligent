import {useCallback, useEffect, useRef, useState} from "react";
import type {ChangeEvent, PointerEvent as ReactPointerEvent, RefObject} from "react";
import {InferenceClient} from "../../api/inference-client";
import {saveReviewedEvent} from "../../api/events";
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
const JPEG_QUALITY = 0.82;
const PREVIEW_CANDIDATES = [0.05, 0.5, 1, 2, 3, 4, 5, 7, 10];
const DEFAULT_PPE_REQUIREMENTS: PpeRequirementUpdate = {
  profile: "hat_vest_v1",
  hat_required: false,
  vest_required: false,
  restricted_area_detection_enabled: false,
};

interface RuleView {yes: boolean | null; text: string; badge: string}
export type HumanReviewTone = "normal" | "critical" | "warning" | "unknown";

export interface HumanReviewState {
  tone: HumanReviewTone;
  message: string;
}

export interface HitlLogEntry {
  id: string;
  tone: "critical" | "warning";
  title: string;
  detail: string;
  reviewStatus: "pending" | "reviewed";
  hasNewOccurrence: boolean;
  violationKeys?: string[];
  reviewResult?: InferenceResult;
}

export interface MonitorView {
  violation: boolean;
  alertTitle: string;
  severity: "NORMAL" | "VIOLATE";
  alertSummary: string;
  reviewMessage: string;
  eventStatus: string;
  confidenceLabel: string;
  confidenceWidth: string;
  humanReviewTone?: HumanReviewTone;
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
  humanReviewTone: "normal",
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
  const selectedZoneIdRef = useRef<string | null>(null);
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
  const [hitlLogs, setHitlLogs] = useState<HitlLogEntry[]>([]);
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
  const videosByZone = useRef(new Map<string, {name: string; url: string}>());
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
        zone_points: selectedZoneForInference(appliedZonesRef.current, selectedZoneIdRef.current),
        machine_state: selectedMachineState(appliedZonesRef.current, selectedZoneIdRef.current),
        camera_id: "uploaded_video",
        zone_id: selectedZoneIdRef.current ?? "zone_01",
        monitoring_session_id: session.current.monitoringSessionId
      }),
      onResult: result => resultHandler.current(result),
      onFailure: message => failureHandler.current(message)
    });
  }
  const client = clientRef.current;

  useEffect(() => {
    selectedZoneIdRef.current = selectedZoneId;
  }, [selectedZoneId]);

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
    const humanReview = buildHumanReviewState(result);
    const newLogs = buildHitlLogEntries(result);
    const criticalCount = newLogs.filter(entry => entry.tone === "critical").length;
    const ppeCount = newLogs.filter(entry => entry.tone === "warning").length;
    const activeAlertTitle = criticalCount > 0
      ? `Đang có ${criticalCount} vi phạm vùng cấm${ppeCount > 0 ? ` và ${ppeCount} vi phạm PPE` : ""}`
      : `Đang có ${ppeCount} vi phạm PPE cần xác minh`;
    const activeAlertSummary = criticalCount > 0
      ? "Có người trong vùng cấm khi máy đang chạy. Streaming vẫn tiếp tục; chọn log để xem đúng khung hình."
      : "Thiếu mũ hoặc áo đã được xác nhận qua nhiều khung hình. Chọn log để xem đúng người và khung hình.";
    setHitlLogs(current => {
      const incomingById = new Map(newLogs.map(log => [log.id, log]));
      const updated = current.map(existing => {
        const incoming = incomingById.get(existing.id);
        if (!incoming) return existing;
        incomingById.delete(existing.id);
        const violationKeys = [...new Set([...(existing.violationKeys ?? []), ...(incoming.violationKeys ?? [])])];
        const tone: HitlLogEntry["tone"] = violationKeys.some(
          key => key.startsWith("zone_intrusion") || key === "restricted_area_person"
        ) ? "critical" : "warning";
        return {
          ...existing,
          tone,
          title: buildViolationTitle(violationKeys),
          detail: incoming.detail,
          violationKeys,
          hasNewOccurrence: incoming.hasNewOccurrence,
          reviewStatus: incoming.hasNewOccurrence ? "pending" : existing.reviewStatus,
          reviewResult: incoming.hasNewOccurrence && incoming.reviewResult?.snapshot_data
            ? incoming.reviewResult
            : existing.reviewResult,
        };
      });
      return [...incomingById.values(), ...updated];
    });
    setView(current => ({
      ...current,
      violation,
      alertTitle: violation ? activeAlertTitle : "Trạng thái bình thường",
      severity: violation ? "VIOLATE" : "NORMAL",
      alertSummary: violation ? activeAlertSummary : "Frame hiện tại không vi phạm rule an toàn đã định nghĩa.",
      zoneRule: {yes: inside, text: inside ? "Trong vùng nguy hiểm" : "Ngoài vùng", badge: inside ? "YES" : "NO"},
      ppeRule: buildPpeRule(result),
      humanReviewTone: criticalCount > 0 ? "critical" : humanReview.tone,
      reviewMessage: humanReview.message,
    }));
    if (!result.review_required) session.current.violationLatched = false;
    if (!result.review_required || session.current.violationLatched) return;
    session.current.violationLatched = true;
    setFlowStatus("Có cảnh báo cần xác minh");
    setView(current => ({
      ...current,
      violation: true,
      severity: "VIOLATE",
      reviewMessage: "Có log mới đang chờ cán bộ an toàn xác minh",
      eventStatus: "Đang chờ xác minh · chưa lưu",
      confidenceLabel: "VIOLATE",
      confidenceWidth: "100%",
    }));
    queueViolationReview(result);
  }

  resultHandler.current = handleInferenceResult;
  failureHandler.current = handleInferenceFailure;

  const pendingCriticalLogs = hitlLogs.filter(log => log.reviewStatus === "pending" && log.tone === "critical").length;
  const pendingPpeLogs = hitlLogs.filter(log => log.reviewStatus === "pending" && log.tone === "warning").length;
  const pendingReviewLogCount = pendingCriticalLogs + pendingPpeLogs;

  useEffect(() => {
    if (pendingReviewLogCount === 0) return;
    setView(current => ({
      ...current,
      violation: true,
      severity: "VIOLATE",
      alertTitle: `Có ${pendingReviewLogCount} log cần review`,
      alertSummary: `${pendingCriticalLogs} log nghiêm trọng · ${pendingPpeLogs} log PPE cần xác minh.`,
    }));
  }, [pendingCriticalLogs, pendingPpeLogs, pendingReviewLogCount]);

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
    videosByZone.current.forEach(video => URL.revokeObjectURL(video.url));
  }, [client]);

  function handleVideoSelection(event: ChangeEvent<HTMLInputElement>): void {
    const file = event.target.files?.[0];
    const video = videoRef.current;
    const zoneId = selectedZoneId;
    if (!file || !video || !zoneId) return;
    client.close();
    video.pause();
    const previous = videosByZone.current.get(zoneId);
    if (previous) URL.revokeObjectURL(previous.url);
    const zoneVideo = {name: file.name, url: URL.createObjectURL(file)};
    videosByZone.current.set(zoneId, zoneVideo);
    video.src = zoneVideo.url;
    video.load();
    Object.assign(session.current, {
      running: false, lastHandledFrame: -1, lastSampleTime: -1,
      violationLatched: false, previewReady: false, previewCandidateIndex: 0,
      frameSequence: 0, monitoringSessionId: crypto.randomUUID()
    });
    setLatestPeople([]);
    setLatestDetections([]);
    setHitlLogs([]);
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
    setFlowStatus(`${zonesRef.current.find(zone => zone.zone_id === zoneId)?.display_name ?? "Vùng"} · đang tải video`);
    setView(initialView(machineRunningRef.current));
    showToast("Video đã được gắn với vùng đang chọn.");
  }

  function switchSelectedZone(zoneId: string): void {
    if (zoneId === selectedZoneId) return;
    if (session.current.running) stopRealtimeInference();
    else client.close();
    setSelectedZoneId(zoneId);
    setSelectedPoint(null);
    setLatestPeople([]);
    setLatestDetections([]);
    setPreviewSrc(undefined);
    setStageReady(false);
    setPlaybackDisabled(true);
    setZoneDisabled(true);
    const video = videoRef.current;
    const zoneVideo = videosByZone.current.get(zoneId);
    const zone = zonesRef.current.find(item => item.zone_id === zoneId);
    setView(initialView(zone?.machine_state === "running"));
    if (!video || !zoneVideo) {
      video?.removeAttribute("src");
      setFileLabel(`${zone?.display_name ?? "Vùng"} chưa có video`);
      setVideoMeta("CHỌN VIDEO ĐỂ BẮT ĐẦU");
      setFlowStatus(`${zone?.display_name ?? "Vùng"} chưa có video`);
      return;
    }
    video.src = zoneVideo.url;
    video.load();
    setFileLabel(zoneVideo.name);
    setVideoMeta("ĐANG TẢI VIDEO");
    setFlowStatus(`${zone?.display_name ?? "Vùng"} · đang tải video`);
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
    if (!video?.src) return;
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

  function queueViolationReview(result: InferenceResult): void {
    pendingViolationRef.current = result;
    setPendingViolation(result);
    setReviewStartedAt(Date.now());
  }

  function openReviewLog(logId: string): void {
    const selectedLog = hitlLogs.find(log => log.id === logId);
    if (selectedLog?.reviewResult) {
      pendingViolationRef.current = selectedLog.reviewResult;
      setPendingViolation(selectedLog.reviewResult);
      setReviewStartedAt(Date.now());
    }
    setIsReviewModalOpen(true);
  }

  function stopPreviewPlayback(): void {
    stopRealtimeInference();
    capturePausedFrame();
    setFlowStatus("Video đã dừng · có thể chỉnh vùng");
  }

  function handleEnded(): void {
    session.current.running = false;
    client.close();
    const video = videoRef.current;
    if (video) video.currentTime = 0;
    setPlaybackLabel("↻ Phát lại");
    capturePausedFrame();
  }

  function toggleMachine(): void {
    const selected = zonesRef.current.find(zone => zone.zone_id === selectedZoneId);
    const running = selected ? selected.machine_state !== "running" : !machineRunningRef.current;
    machineRunningRef.current = running;
    setMachineRunning(running);
    if (selected) updateZone(selected.zone_id, zone => ({...zone, machine_state: running ? "running" : "stopped"}));
    setView(current => ({
      ...current,
      machineRule: {yes: running, text: running ? "Máy đang chạy" : "Máy đã dừng", badge: running ? "ON" : "OFF"}
    }));
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
      await saveReviewedEvent(buildEventPayload(status, pending, [], machineRunningRef.current));
      const reviewedLogIds = new Set(buildHitlLogEntries(pending).map(log => log.id));
      setHitlLogs(current => current.map(log => reviewedLogIds.has(log.id)
        ? {...log, reviewStatus: "reviewed", hasNewOccurrence: false}
        : log));
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
      machineRunning: selectedZone ? selectedZone.machine_state === "running" : machineRunning,
      pendingViolation, isReviewModalOpen, reviewSaving, view,
      pendingReviewCounts: {critical: pendingCriticalLogs, other: pendingPpeLogs},
      hitlLogs,
      fileLabel, videoMeta, previewSrc, stageReady, playbackDisabled, playbackLabel,
      zoneDisabled, flowStatus, toast, selectedPointPosition, timer,
      latestPeople, latestDetections, peopleCount: latestPeople.length,
      ppeRequirementCount: Number(activePpeRequirements.hat_required) + Number(activePpeRequirements.vest_required),
    },
    actions: {
      openFilePicker: () => fileInputRef.current?.click(), handleVideoSelection,
      handleLoadedMetadata, handleSeeked, handlePlayback, handleEnded, toggleMachine,
      resetZone, createZone, cancelZoneCreation, deleteSelectedZone, saveZones,
      selectZone: switchSelectedZone,
      updateSelectedZoneName: (displayName: string) => selectedZoneId
        && updateZone(selectedZoneId, zone => ({...zone, display_name: displayName})),
      toggleSelectedZoneEnabled: () => selectedZoneId
        && updateZone(selectedZoneId, zone => ({...zone, enabled: !zone.enabled})),
      handlePointerDown, handlePointerMove,
      handlePointerUp, deleteSelectedPoint, review,
      openReviewLog,
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
  if (missing.length) {
    if (result.rule.ppe_alert) {
      return {yes: false, text: `Thiếu: ${missing.map(item => ppeLabel[item]).join(", ")}`, badge: "MISS"};
    }
    return {yes: null, text: "Đang xác nhận PPE qua nhiều khung hình", badge: "CHECK"};
  }

  const hasUnknown = result.people.some(person =>
    requiredLabels.some(label => {
      const item = label === "mũ bảo hộ" ? "hat" : "vest";
      return person.ppe[item].status === "unknown";
    }),
  );
  if (hasUnknown) return {yes: null, text: `Đang kiểm tra ${requiredLabels.join(", ")}`, badge: "CHECK"};
  return {yes: true, text: `Đủ PPE: ${requiredLabels.join(", ")}`, badge: "OK"};
}

export function buildHumanReviewState(result: InferenceResult): HumanReviewState {
  if (result.rule.restricted_area_alert) {
    return {tone: "critical", message: "Phát hiện người trong phạm vi camera · cần xử lý ngay"};
  }
  if (result.people.some(person => person.inside_zone)) {
    return {tone: "critical", message: "Người đã đi vào vùng cấm · cần xử lý ngay"};
  }

  if (result.rule.ppe_alert) {
    return {tone: "warning", message: "Phát hiện người thiếu mũ hoặc áo theo quy định"};
  }

  if (result.people.some(person => person.missing_required_ppe.length > 0)) {
    return {tone: "unknown", message: "Đang xác nhận PPE qua nhiều khung hình"};
  }

  const required = result.rule.ppe_requirements;
  const hasUnknownPpe = result.people.some(person =>
    (required.hat_required && person.ppe.hat.status === "unknown")
    || (required.vest_required && person.ppe.vest.status === "unknown"),
  );
  if (hasUnknownPpe) {
    return {tone: "unknown", message: "Không xác định được PPE · cần người review"};
  }

  return {tone: "normal", message: "Không có cảnh báo · người đã đủ mũ và áo theo quy định"};
}

export function buildHitlLogEntries(result: InferenceResult): HitlLogEntry[] {
  const ppeLabel = {hat: "mũ bảo hộ", vest: "áo phản quang"} as const;
  const entries: HitlLogEntry[] = [];
  result.people.forEach((person, index) => {
    const personLabel = `Người #${person.track_id ?? index + 1}`;
    const violations = person.active_violations ?? [];
    const hasZoneIntrusion = violations.some(entry => entry.rule_key.startsWith("zone_intrusion"));
    const hasRestrictedAreaAlert = violations.some(entry => entry.rule_key === "restricted_area_person");
    const missingPpe = [...new Set(violations
      .filter(entry => entry.rule_key.startsWith("missing_ppe:"))
      .map(entry => entry.rule_key.split(":", 2)[1] as keyof typeof ppeLabel)
      .filter(item => item in ppeLabel))];
    if (!hasZoneIntrusion && !hasRestrictedAreaAlert && missingPpe.length === 0) return;
    const missingLabel = missingPpe.map(item => ppeLabel[item]).join(" và ");
    const violationKeys = [...new Set(violations.map(entry => entry.rule_key))];
    entries.push({
      id: `${result.monitoring_session_id ?? "session"}:person:${person.track_id ?? index + 1}`,
      tone: hasZoneIntrusion || hasRestrictedAreaAlert ? "critical" : "warning",
      title: hasRestrictedAreaAlert
        ? `Phát hiện người trong phạm vi camera${missingLabel ? ` · thiếu ${missingLabel}` : ""}`
        : hasZoneIntrusion
        ? `Đi vào vùng cấm${missingLabel ? ` · thiếu ${missingLabel}` : ""}`
        : `Thiếu ${missingLabel}`,
      detail: `${personLabel} · cần xác minh`,
      reviewStatus: "pending",
      hasNewOccurrence: violations.some(entry => entry.is_new),
      violationKeys,
      reviewResult: {
        ...result,
        people: [person],
        detections: (result.detections ?? [])
          .filter(detection => detection.person_index === index)
          .map(detection => ({...detection, person_index: 0})),
      },
    });
  });
  return entries;
}

function buildViolationTitle(violationKeys: string[]): string {
  const labels: string[] = [];
  if (violationKeys.some(key => key === "restricted_area_person")) labels.push("trong phạm vi camera");
  else if (violationKeys.some(key => key.startsWith("zone_intrusion"))) labels.push("vào vùng cấm");
  if (violationKeys.includes("missing_ppe:hat")) labels.push("thiếu mũ bảo hộ");
  if (violationKeys.includes("missing_ppe:vest")) labels.push("thiếu áo phản quang");
  return labels.join(" · ") || "Vi phạm an toàn";
}

export function buildEventPayload(
  status: ReviewStatus,
  pending: InferenceResult,
  zonePoints: ZonePoint[],
  machineRunning: boolean
): EventPayload {
  const person = pending.people[0];
  const violations = person?.active_violations ?? [];
  const occurrenceIds = [...new Set(
    violations.filter(item => item.is_new).map(item => item.occurrence_id),
  )];
  const violationKeys = [...new Set(violations.map(item => item.rule_key))];
  const zoneId = violations.find(item => item.zone_id)?.zone_id ?? pending.rule.zone_id;
  const critical = violationKeys.some(key => key.startsWith("zone_intrusion") || key === "restricted_area_person");
  return {
    zone_id: zoneId,
    camera_id: "uploaded_video",
    event_type: "person_safety_violation",
    severity: critical ? "critical" : "high",
    status,
    acknowledged_by: "Safety Officer",
    snapshot_data: pending.snapshot_data,
    snapshot_people: pending.people,
    snapshot_detections: pending.detections ?? [],
    monitoring_session_id: pending.monitoring_session_id,
    track_id: person?.track_id,
    occurrence_ids: occurrenceIds,
    details: {
      inference_result: pending.result,
      review_result: status === "acknowledged" ? "actual_violation" : "normal",
      machine_state: machineRunning ? "running" : "stopped",
      video_timestamp_seconds: pending.video_time,
      people: person ? [person] : [],
      violations: violationKeys,
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

function selectedZoneForInference(zones: MonitoringZone[], selectedZoneId: string | null): ZonePoint[] {
  const zone = zones.find(item => item.zone_id === selectedZoneId);
  return zone?.enabled && zone.points.length === 4 ? zone.points : [];
}

function selectedMachineState(zones: MonitoringZone[], selectedZoneId: string | null): "running" | "stopped" {
  return zones.find(item => item.zone_id === selectedZoneId)?.machine_state ?? "stopped";
}

export type MonitorRefs = {
  videoRef: RefObject<HTMLVideoElement | null>;
  overlayRef: RefObject<HTMLCanvasElement | null>;
  captureRef: RefObject<HTMLCanvasElement | null>;
  fileInputRef: RefObject<HTMLInputElement | null>;
};
