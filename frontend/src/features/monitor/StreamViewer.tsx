import {useEffect, useRef, useState} from "react";
import {getAccessToken} from "../../api/auth";
import {listCameraConfigurations} from "../../api/camera-configurations";
import {CameraDetectionClient} from "../../api/camera-detection-client";
import {loadPendingEvents, saveReviewedEvent, subscribeToSafetyEventUpdates} from "../../api/events";
import {assetUrl} from "../../api/config";
import {listMediaAssets} from "../../api/media-assets";
import {listCameraSessions, replayCamera, runSimulation} from "../../api/simulation";
import type {CameraConfiguration, CameraInferenceResult, CameraSession, InferenceResult, MediaAsset, ReviewStatus, SafetyEvent, UserRole} from "../../types";
import {PendingViolationList} from "../alerts/PendingViolationList";
import {PpeAlertToast} from "../alerts/PpeAlertToast";
import {isZoneAlert} from "../alerts/pending-violation";
import {preloadSnapshot} from "../alerts/preload-snapshot";
import {ReviewModal} from "../alerts/ReviewModal";
import {violationRuleLabel} from "../alerts/violation-copy";
import {AuthenticatedMedia} from "../media/AuthenticatedMedia";
import {DetectionOverlay} from "./DetectionOverlay";
import {buildEventPayload} from "./use-monitor";
import "./stream.css";

export const CAMERA_IDS = ["cam_1", "cam_2", "cam_3", "cam_4"] as const;
const DETECTION_SYNC_TOLERANCE_SECONDS = 0.2;
const MAX_BUFFERED_DETECTIONS_PER_CAMERA = 240;

export function StreamViewer({active = true, role, onConfigure}: {active?: boolean; role: UserRole; onConfigure: (cameraId: string) => void}) {
  const canConfigure = role === "safety_manager" || role === "system_admin";
  const [configurations, setConfigurations] = useState<Record<string, CameraConfiguration>>({});
  const [assets, setAssets] = useState<Record<string, MediaAsset>>({});
  const [sessions, setSessions] = useState<Record<string, CameraSession>>({});
  const [detections, setDetections] = useState<Record<string, CameraInferenceResult>>({});
  const [ended, setEnded] = useState<Record<string, boolean>>({});
  const [playbackRequested, setPlaybackRequested] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [replaying, setReplaying] = useState("");
  const [error, setError] = useState("");
  const [pendingAlerts, setPendingAlerts] = useState<SafetyEvent[]>([]);
  const [activeAlert, setActiveAlert] = useState<SafetyEvent | null>(null);
  const [ppeToast, setPpeToast] = useState<SafetyEvent | null>(null);
  const [pendingReview, setPendingReview] = useState<CameraInferenceResult | null>(null);
  const [reviewSaving, setReviewSaving] = useState(false);
  const [reviewStartedAt, setReviewStartedAt] = useState<number | null>(null);
  const runningRef = useRef(false);
  const replayingRef = useRef(false);
  const reviewSavingRef = useRef(false);
  const sessionsRef = useRef(sessions);
  const configurationsRef = useRef(configurations);
  const activeAlertRef = useRef<SafetyEvent | null>(null);
  const openAlertRef = useRef<(alert: SafetyEvent) => void>(() => undefined);
  const pendingReviewRef = useRef<CameraInferenceResult | null>(null);
  const detectionBuffersRef = useRef<Record<string, CameraInferenceResult[]>>({});
  const playbackTimesRef = useRef<Record<string, number>>({});
  const displayedDetectionKeysRef = useRef<Record<string, string>>({});
  const zoneQueueRef = useRef<SafetyEvent[]>([]);
  const announcedAlertIdsRef = useRef(new Set<number>());
  const reviewLoadIdRef = useRef(0);
  sessionsRef.current = sessions;
  configurationsRef.current = configurations;

  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    setLoading(true);
    void Promise.all([listCameraConfigurations(controller.signal), listMediaAssets(), listCameraSessions(controller.signal), loadPendingEvents(controller.signal)])
      .then(([configurationList, inventory, sessionList, alerts]) => {
        const indexedConfigurations = indexBy(configurationList, "camera_id");
        configurationsRef.current = indexedConfigurations;
        setConfigurations(indexedConfigurations);
        setAssets(indexBy(inventory, "id"));
        applySessions(sessionList);
        setPendingAlerts(alerts);
        alerts.forEach(alert => announcedAlertIdsRef.current.add(alert.id));
      })
      .catch(reason => { if (!controller.signal.aborted) setError(errorText(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [active]);

  useEffect(() => subscribeToSafetyEventUpdates(() => {
    void loadPendingEvents().then(alerts => {
      setPendingAlerts(alerts);
      const pendingIds = new Set(alerts.map(alert => alert.id));
      zoneQueueRef.current = zoneQueueRef.current.filter(alert => pendingIds.has(alert.id));
      setPpeToast(current => current && pendingIds.has(current.id) ? current : null);
      const openAlert = activeAlertRef.current;
      if (openAlert && !pendingIds.has(openAlert.id)) {
        reviewLoadIdRef.current += 1;
        activeAlertRef.current = null;
        setActiveAlert(null);
        pendingReviewRef.current = null;
        setPendingReview(null);
        setReviewStartedAt(null);
        const next = zoneQueueRef.current.shift();
        if (next) openAlertRef.current(next);
      }
    }).catch(reason => setError(errorText(reason)));
  }), []);

  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => {
      void listCameraSessions().then(applySessions).catch(reason => setError(errorText(reason)));
    }, 2000);
    return () => window.clearInterval(timer);
  }, [active]);

  useEffect(() => {
    const accessToken = getAccessToken();
    if (!accessToken) return;
    let disposed = false;
    let retryTimer: number | undefined;
    const announcePersistedAlerts = (eventIds: number[]) => {
      void loadPendingEvents().then(alerts => {
        setPendingAlerts(alerts);
        const fresh = alerts.filter(alert => eventIds.includes(alert.id) && !announcedAlertIdsRef.current.has(alert.id));
        fresh.forEach(alert => announcedAlertIdsRef.current.add(alert.id));
        for (const alert of fresh) {
          if (isZoneAlert(alert)) {
            if (activeAlertRef.current) zoneQueueRef.current.push(alert);
            else openAlertRef.current(alert);
          }
          else setPpeToast(alert);
        }
      }).catch(reason => setError(errorText(reason)));
    };
    const client = new CameraDetectionClient({
      accessToken,
      cameraIds: [...CAMERA_IDS],
      onResult: result => {
        const current = sessionsRef.current[result.camera_id];
        if (!current || result.session_id !== current.id || current.status === "ERROR") return;
        const updated = {...current, status: result.session_status, inference_fps: result.inference_fps};
        sessionsRef.current = {...sessionsRef.current, [result.camera_id]: updated};
        if (result.session_status === "ERROR") {
          clearDetectionSync(result.camera_id);
        } else if (result.media_type === "image") {
          showSynchronizedDetection(result.camera_id, result);
        } else {
          bufferDetection(result);
        }
        if (result.review_required && result.pending_event_ids?.length) announcePersistedAlerts(result.pending_event_ids);
        setSessions(values => ({...values, [result.camera_id]: updated}));
      },
      onSessionStatus: status => {
        const current = sessionsRef.current[status.camera_id];
        if (!current || status.session_id !== current.id) return;
        const updated = {...current, status: status.session_status, inference_fps: status.inference_fps, error_code: status.error_code ?? null};
        sessionsRef.current = {...sessionsRef.current, [status.camera_id]: updated};
        setSessions(values => ({...values, [status.camera_id]: updated}));
        if (status.session_status === "ERROR") clearDetectionSync(status.camera_id);
      },
      onFailure: message => { setError(message); scheduleRetry(); },
    });
    const connect = () => void client.connect().catch(reason => { if (!disposed) { setError(errorText(reason)); scheduleRetry(); } });
    const scheduleRetry = () => { if (!disposed && !retryTimer) retryTimer = window.setTimeout(() => { retryTimer = undefined; connect(); }, 3000); };
    connect();
    return () => { disposed = true; if (retryTimer) window.clearTimeout(retryTimer); client.close(); };
  }, []);

  function applySessions(next: CameraSession[]) {
    const compatible = next.filter(session => configurationsRef.current[session.camera_id]?.asset_id === session.asset_id);
    const indexed = indexLatestBy(compatible, "camera_id");
    const previousSessions = sessionsRef.current;
    setDetections(current => {
      const retained = {...current};
      for (const cameraId of CAMERA_IDS) {
        const previous = previousSessions[cameraId];
        const incoming = indexed[cameraId];
        if (!incoming || incoming.status === "ERROR" || previous?.id !== incoming.id) {
          delete detectionBuffersRef.current[cameraId];
          delete playbackTimesRef.current[cameraId];
          delete displayedDetectionKeysRef.current[cameraId];
          delete retained[cameraId];
        }
      }
      return retained;
    });
    setEnded(current => {
      const nextEnded = {...current};
      for (const cameraId of CAMERA_IDS) if (sessionsRef.current[cameraId]?.id !== indexed[cameraId]?.id) delete nextEnded[cameraId];
      return nextEnded;
    });
    setPlaybackRequested(current => {
      const retained = {...current};
      for (const cameraId of CAMERA_IDS) if (!indexed[cameraId]) delete retained[cameraId];
      return retained;
    });
    sessionsRef.current = indexed;
    setSessions(indexed);
  }

  function bufferDetection(result: CameraInferenceResult) {
    const current = detectionBuffersRef.current[result.camera_id] ?? [];
    const sessionResults = current.filter(item => item.session_id === result.session_id && item.frame_id !== result.frame_id);
    sessionResults.push(result);
    sessionResults.sort((left, right) => left.video_time - right.video_time || left.frame_id - right.frame_id);
    detectionBuffersRef.current[result.camera_id] = sessionResults.slice(-MAX_BUFFERED_DETECTIONS_PER_CAMERA);
    const playbackTime = playbackTimesRef.current[result.camera_id];
    if (playbackTime !== undefined) synchronizeDetection(result.camera_id, playbackTime);
  }

  function handlePlaybackTime(cameraId: string, playbackTime: number) {
    playbackTimesRef.current[cameraId] = playbackTime;
    synchronizeDetection(cameraId, playbackTime);
  }

  function synchronizeDetection(cameraId: string, playbackTime: number) {
    const session = sessionsRef.current[cameraId];
    if (!session) {
      showSynchronizedDetection(cameraId);
      return;
    }
    const cutoff = playbackTime - DETECTION_SYNC_TOLERANCE_SECONDS;
    const candidates = (detectionBuffersRef.current[cameraId] ?? []).filter(
      result => result.session_id === session.id && result.video_time >= cutoff,
    );
    detectionBuffersRef.current[cameraId] = candidates;
    let closest: CameraInferenceResult | undefined;
    let closestDelta = Number.POSITIVE_INFINITY;
    for (const candidate of candidates) {
      const delta = Math.abs(candidate.video_time - playbackTime);
      if (delta <= DETECTION_SYNC_TOLERANCE_SECONDS && delta < closestDelta) {
        closest = candidate;
        closestDelta = delta;
      }
    }
    showSynchronizedDetection(cameraId, closest);
  }

  function showSynchronizedDetection(cameraId: string, result?: CameraInferenceResult) {
    const nextKey = result ? `${result.session_id}:${result.frame_id}` : "";
    if ((displayedDetectionKeysRef.current[cameraId] ?? "") === nextKey) return;
    if (nextKey) displayedDetectionKeysRef.current[cameraId] = nextKey;
    else delete displayedDetectionKeysRef.current[cameraId];
    setDetections(values => result ? {...values, [cameraId]: result} : without(values, cameraId));
  }

  function clearDetectionSync(cameraId: string) {
    delete detectionBuffersRef.current[cameraId];
    delete playbackTimesRef.current[cameraId];
    showSynchronizedDetection(cameraId);
  }

  async function run() {
    if (runningRef.current) return;
    runningRef.current = true; setRunning(true); setError("");
    setPlaybackRequested(Object.fromEntries(CAMERA_IDS.map(cameraId => [cameraId, true])));
    try {
      const result = await runSimulation();
      const started = new Set(result.sessions.map(item => item.camera_id));
      applySessions([...Object.values(sessionsRef.current).filter(item => !started.has(item.camera_id)), ...result.sessions]);
      const failures = Object.entries(result.errors);
      if (failures.length) setError(failures.map(([cameraId, reason]) => `${cameraId}: ${reason}`).join(" · "));
    }
    catch (reason) { setError(errorText(reason)); }
    finally { runningRef.current = false; setRunning(false); }
  }

  async function replay(cameraId: string) {
    if (replayingRef.current) return;
    replayingRef.current = true; setReplaying(cameraId); setError("");
    setPlaybackRequested(current => ({...current, [cameraId]: true}));
    try { applySessions([...Object.values(sessionsRef.current).filter(item => item.camera_id !== cameraId), await replayCamera(cameraId)]); }
    catch (reason) { setError(errorText(reason)); }
    finally { replayingRef.current = false; setReplaying(""); }
  }

  function showReview(result: CameraInferenceResult | null, alert: SafetyEvent | null = null) {
    activeAlertRef.current = alert;
    setActiveAlert(alert);
    pendingReviewRef.current = result;
    setPendingReview(result);
    setReviewStartedAt(result ? Date.now() : null);
  }

  function openAlert(alert: SafetyEvent) {
    const result = alert.details?.pending_review;
    if (!result) {
      setError("Cảnh báo không còn đủ dữ liệu để mở HITL.");
      return;
    }
    const currentAlert = activeAlertRef.current;
    if (currentAlert && currentAlert.id !== alert.id) {
      if (!zoneQueueRef.current.some(item => item.id === alert.id)) zoneQueueRef.current.push(alert);
      return;
    }
    activeAlertRef.current = alert;
    setActiveAlert(alert);
    const snapshot = assetUrl(alert.snapshot_path) ?? undefined;
    const loadId = ++reviewLoadIdRef.current;
    if (!snapshot) {
      showReview({...result, snapshot_data: undefined}, alert);
      return;
    }
    void preloadSnapshot(snapshot).then(loaded => {
      if (reviewLoadIdRef.current !== loadId || activeAlertRef.current?.id !== alert.id) return;
      if (!loaded) setError("Không thể tải snapshot; popup được mở để cảnh báo không bị bỏ lỡ.");
      showReview({...result, snapshot_data: loaded ? snapshot : undefined}, alert);
    });
  }
  openAlertRef.current = openAlert;

  function closeReview() {
    reviewLoadIdRef.current += 1;
    showReview(null);
    const next = zoneQueueRef.current.shift();
    if (next) openAlert(next);
  }

  async function review(status: ReviewStatus) {
    const pending = pendingReviewRef.current;
    if (!pending || reviewSavingRef.current) return;
    const configuration = configurations[pending.camera_id];
    reviewSavingRef.current = true; setReviewSaving(true);
    setError("");
    try {
      const claimedOccurrences = new Set<string>();
      const payloads = pending.people.flatMap(person => {
        const newViolations = person.active_violations?.filter(violation => violation.is_new) ?? [];
        const unclaimedViolations = newViolations.filter(violation => {
          if (claimedOccurrences.has(violation.occurrence_id)) return false;
          claimedOccurrences.add(violation.occurrence_id);
          return true;
        });
        if (!unclaimedViolations.length) return [];
        const zoneId = unclaimedViolations.find(violation => violation.zone_id)?.zone_id ?? pending.rule.zone_id;
        const zone = configuration?.zones.find(item => item.zone_id === zoneId);
        const inference = {
          ...pending,
          type: "inference_result",
          people: [{...person, active_violations: unclaimedViolations}],
        } satisfies InferenceResult;
        return [buildEventPayload(
          status,
          inference,
          zone?.points ?? [],
          configuration?.machine_state === "running",
          zone?.display_name ?? zoneId,
        )];
      });
      if (!payloads.length) throw new Error("Không có occurrence mới để lưu.");
      for (const payload of payloads) await saveReviewedEvent(payload);
      const reviewedId = activeAlertRef.current?.id;
      if (reviewedId != null) setPendingAlerts(current => current.filter(item => item.id !== reviewedId));
      closeReview();
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      reviewSavingRef.current = false; setReviewSaving(false);
    }
  }

  const reviewTimer = useReviewTimer(reviewStartedAt);
  const violationKeys = pendingReview?.people.flatMap(person => person.active_violations
    ?.filter(violation => violation.is_new)
    .map(violation => violation.rule_key) ?? []) ?? [];
  const violationLabel = violationRuleLabel(violationKeys);
  const reviewTitle = `Phát hiện ${violationLabel.charAt(0).toLocaleLowerCase("vi-VN")}${violationLabel.slice(1)}`;

  if (loading) return <div className="stream-empty-state" role="status"><strong>Đang tải Live Monitor</strong></div>;

  return <div className="monitor-stream-shell">
    <div className="monitor-actions"><div>{canConfigure && <p className="monitor-config-hint">Đã upload video? Bấm vào camera để mở cấu hình.</p>}</div>{canConfigure && <button className="inference-btn" disabled={running || !Object.values(configurations).some(item => item.asset_id)} onClick={() => void run()}>{running ? "Đang khởi động…" : "Chạy mô phỏng"}</button>}</div>
    {error && <p className="stream-config-error" role="alert">{error}</p>}
    <div className="monitor-workspace"><div className="monitor-camera-grid">{CAMERA_IDS.map((cameraId, index) => {
      const configuration = configurations[cameraId];
      const asset = configuration?.asset_id ? assets[configuration.asset_id] : undefined;
      const storedSession = sessions[cameraId];
      const session = storedSession?.asset_id === configuration?.asset_id ? storedSession : undefined;
      const detection = session && detections[cameraId]?.session_id === session.id ? detections[cameraId] : undefined;
      const replayVisible = asset?.media_type === "video" && (ended[cameraId] || session?.status === "COMPLETED");
      return <article className={`active-stream-view ${canConfigure ? "configurable" : ""}`} key={cameraId} role={canConfigure ? "button" : undefined} tabIndex={canConfigure ? 0 : undefined} aria-label={canConfigure ? `Cấu hình Camera ${index + 1}` : undefined} onClick={() => canConfigure && onConfigure(cameraId)} onKeyDown={event => { if (canConfigure && (event.key === "Enter" || event.key === " ")) onConfigure(cameraId); }}>
        <h3>Camera {index + 1}</h3>
        {asset ? <><AuthenticatedMedia assetId={asset.id} mediaType={asset.media_type} storageBackend={asset.storage_backend} label={`Media Camera ${index + 1}`} playing={Boolean(playbackRequested[cameraId]) || session?.status === "STARTING" || session?.status === "RUNNING"} playbackKey={session?.id} onPlaybackTime={time => handlePlaybackTime(cameraId, time)} onEnded={() => { setPlaybackRequested(current => ({...current, [cameraId]: false})); setEnded(current => ({...current, [cameraId]: true})); }} /><DetectionOverlay result={detection} />
          {session && <div className={`stream-badge ${session.status.toLowerCase()}`}>{session.status}</div>}
          {session?.inference_fps != null && <div className="inference-fps">FPS infer <strong>{session.inference_fps.toFixed(1)}</strong></div>}
          {session?.status === "ERROR" && <div className="session-error">{session.error_code || "Phiên mô phỏng gặp lỗi."}</div>}
          {replayVisible && <button className="camera-replay" aria-label={`Replay Camera ${index + 1}`} disabled={Boolean(replaying)} onClick={event => { event.stopPropagation(); void replay(cameraId); }}>↻ <span>Replay</span></button>}
        </> : <div className="stream-empty-state"><strong>{canConfigure ? "Bấm vào đây để cấu hình" : "Camera chưa được cấu hình"}</strong><span>Camera {index + 1}</span></div>}
      </article>;
    })}</div>
    <PendingViolationList alerts={pendingAlerts} onOpen={openAlert} /></div>
    <PpeAlertToast alert={ppeToast} onOpen={() => { if (ppeToast) openAlert(ppeToast); setPpeToast(null); }} onClose={() => setPpeToast(null)} />
    <ReviewModal
      isOpen={pendingReview !== null}
      onClose={closeReview}
      snapshot={pendingReview?.snapshot_data}
      people={pendingReview?.people}
      zones={pendingReview ? configurations[pendingReview.camera_id]?.zones : undefined}
      timer={reviewTimer}
      reviewSaving={reviewSaving}
      alertTitle={reviewTitle}
      alertSummary={pendingReview ? `${pendingReview.camera_id} · ${new Date(activeAlert?.timestamp ?? Date.now()).toLocaleString("vi-VN")}` : ""}
      onReview={status => void review(status)}
      closeable
    />
  </div>;
}

function indexBy<T, K extends keyof T>(items: T[], key: K): Record<string, T> { return Object.fromEntries(items.map(item => [String(item[key]), item])); }
function indexLatestBy<T, K extends keyof T>(items: T[], key: K): Record<string, T> {
  const indexed: Record<string, T> = {};
  for (const item of items) {
    const value = String(item[key]);
    if (!(value in indexed)) indexed[value] = item;
  }
  return indexed;
}
function without<T>(values: Record<string, T>, key: string): Record<string, T> { const next = {...values}; delete next[key]; return next; }
function errorText(reason: unknown): string { return reason instanceof Error ? reason.message : "Không thể đồng bộ Live Monitor."; }

function useReviewTimer(startedAt: number | null): string {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!startedAt) return;
    setNow(Date.now());
    const interval = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(interval);
  }, [startedAt]);
  if (!startedAt) return "00:00";
  const seconds = Math.floor((now - startedAt) / 1000);
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}
