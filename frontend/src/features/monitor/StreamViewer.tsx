import {useEffect, useRef, useState} from "react";
import {getAccessToken} from "../../api/auth";
import {listCameraConfigurations} from "../../api/camera-configurations";
import {CameraDetectionClient} from "../../api/camera-detection-client";
import {saveReviewedEvent} from "../../api/events";
import {listMediaAssets} from "../../api/media-assets";
import {listCameraSessions, replayCamera, runSimulation} from "../../api/simulation";
import type {CameraConfiguration, CameraInferenceResult, CameraSession, InferenceResult, MediaAsset, ReviewStatus, UserRole} from "../../types";
import {ReviewModal} from "../alerts/ReviewModal";
import {AuthenticatedMedia} from "../media/AuthenticatedMedia";
import {DetectionOverlay} from "./DetectionOverlay";
import {buildEventPayload} from "./use-monitor";
import "./stream.css";

export const CAMERA_IDS = ["cam_1", "cam_2", "cam_3", "cam_4"] as const;

export function StreamViewer({role, onConfigure}: {role: UserRole; onConfigure: (cameraId: string) => void}) {
  const canConfigure = role === "safety_manager";
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
  const [pendingReview, setPendingReview] = useState<CameraInferenceResult | null>(null);
  const [reviewSaving, setReviewSaving] = useState(false);
  const [reviewStartedAt, setReviewStartedAt] = useState<number | null>(null);
  const runningRef = useRef(false);
  const replayingRef = useRef(false);
  const sessionsRef = useRef(sessions);
  const pendingReviewRef = useRef<CameraInferenceResult | null>(null);
  const reviewQueueRef = useRef<CameraInferenceResult[]>([]);
  const seenReviewOccurrencesRef = useRef(new Set<string>());
  sessionsRef.current = sessions;

  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([listCameraConfigurations(controller.signal), listMediaAssets(), listCameraSessions(controller.signal)])
      .then(([configurationList, inventory, sessionList]) => {
        setConfigurations(indexBy(configurationList, "camera_id"));
        setAssets(indexBy(inventory, "id"));
        applySessions(sessionList);
      })
      .catch(reason => { if (!controller.signal.aborted) setError(errorText(reason)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      void listCameraSessions().then(applySessions).catch(reason => setError(errorText(reason)));
    }, 2000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const accessToken = getAccessToken();
    if (!accessToken) return;
    let disposed = false;
    let retryTimer: number | undefined;
    const enqueueReview = (result: CameraInferenceResult) => {
      const occurrenceIds = result.people.flatMap(person => person.active_violations
        ?.filter(violation => violation.is_new)
        .map(violation => violation.occurrence_id) ?? []);
      if (!occurrenceIds.length || occurrenceIds.every(id => seenReviewOccurrencesRef.current.has(id))) return;
      occurrenceIds.forEach(id => seenReviewOccurrencesRef.current.add(id));
      if (pendingReviewRef.current) {
        reviewQueueRef.current.push(result);
        return;
      }
      pendingReviewRef.current = result;
      setPendingReview(result);
      setReviewStartedAt(Date.now());
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
          setDetections(values => without(values, result.camera_id));
        } else {
          setDetections(values => ({...values, [result.camera_id]: result}));
        }
        if (result.review_required) enqueueReview(result);
        setSessions(values => ({...values, [result.camera_id]: updated}));
      },
      onSessionStatus: status => {
        const current = sessionsRef.current[status.camera_id];
        if (!current || status.session_id !== current.id) return;
        const updated = {...current, status: status.session_status, inference_fps: status.inference_fps, error_code: status.error_code ?? null};
        sessionsRef.current = {...sessionsRef.current, [status.camera_id]: updated};
        setSessions(values => ({...values, [status.camera_id]: updated}));
        if (status.session_status === "ERROR") setDetections(values => without(values, status.camera_id));
      },
      onFailure: message => { setError(message); scheduleRetry(); },
    });
    const connect = () => void client.connect().catch(reason => { if (!disposed) { setError(errorText(reason)); scheduleRetry(); } });
    const scheduleRetry = () => { if (!disposed && !retryTimer) retryTimer = window.setTimeout(() => { retryTimer = undefined; connect(); }, 3000); };
    connect();
    return () => { disposed = true; if (retryTimer) window.clearTimeout(retryTimer); client.close(); };
  }, []);

  function applySessions(next: CameraSession[]) {
    const indexed = indexLatestBy(next, "camera_id");
    setDetections(current => {
      const retained = {...current};
      for (const cameraId of CAMERA_IDS) {
        const previous = sessionsRef.current[cameraId];
        const incoming = indexed[cameraId];
        if (!incoming || incoming.status === "ERROR" || previous?.id !== incoming.id) delete retained[cameraId];
      }
      return retained;
    });
    setEnded(current => {
      const nextEnded = {...current};
      for (const cameraId of CAMERA_IDS) if (sessionsRef.current[cameraId]?.id !== indexed[cameraId]?.id) delete nextEnded[cameraId];
      return nextEnded;
    });
    sessionsRef.current = indexed;
    setSessions(indexed);
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

  function showReview(result: CameraInferenceResult | null) {
    pendingReviewRef.current = result;
    setPendingReview(result);
    setReviewStartedAt(result ? Date.now() : null);
  }

  async function review(status: ReviewStatus) {
    const pending = pendingReviewRef.current;
    if (!pending) return;
    const configuration = configurations[pending.camera_id];
    setReviewSaving(true);
    setError("");
    try {
      const payloads = pending.people.flatMap(person => {
        const newViolations = person.active_violations?.filter(violation => violation.is_new) ?? [];
        if (!newViolations.length) return [];
        const zoneId = newViolations.find(violation => violation.zone_id)?.zone_id ?? pending.rule.zone_id;
        const zone = configuration?.zones.find(item => item.zone_id === zoneId);
        const inference = {
          ...pending,
          type: "inference_result",
          people: [{...person, active_violations: newViolations}],
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
      await Promise.all(payloads.map(saveReviewedEvent));
      showReview(reviewQueueRef.current.shift() ?? null);
    } catch (reason) {
      setError(errorText(reason));
    } finally {
      setReviewSaving(false);
    }
  }

  const reviewTimer = useReviewTimer(reviewStartedAt);
  const violationKeys = pendingReview?.people.flatMap(person => person.active_violations
    ?.filter(violation => violation.is_new)
    .map(violation => violation.rule_key) ?? []) ?? [];
  const hasRestricted = violationKeys.some(key => key.startsWith("restricted_area_person"));
  const hasZone = violationKeys.some(key => key.startsWith("zone_intrusion"));
  const hasPpe = violationKeys.some(key => key.startsWith("missing_ppe"));
  const titles: string[] = [];
  if (hasRestricted) titles.push("Phát hiện người trong phạm vi hạn chế");
  if (hasZone) titles.push("Phát hiện xâm nhập vùng nguy hiểm");
  if (hasPpe) titles.push("Phát hiện thiếu PPE");
  const reviewTitle = titles.length > 0 ? titles.join(" & ") : "Phát hiện vi phạm an toàn";

  if (loading) return <div className="stream-empty-state" role="status"><strong>Đang tải Live Monitor</strong></div>;

  return <div className="monitor-stream-shell">
    <div className="monitor-actions"><div>{canConfigure && <p className="monitor-config-hint">Đã upload video? Bấm vào camera, sau đó bấm vào camera thêm một lần nữa để mở cấu hình.</p>}</div>{canConfigure && <button className="inference-btn" disabled={running || !Object.values(configurations).some(item => item.asset_id)} onClick={() => void run()}>{running ? "Đang khởi động…" : "Chạy mô phỏng"}</button>}</div>
    {error && <p className="stream-config-error" role="alert">{error}</p>}
    <div className="monitor-camera-grid">{CAMERA_IDS.map((cameraId, index) => {
      const configuration = configurations[cameraId];
      const asset = configuration?.asset_id ? assets[configuration.asset_id] : undefined;
      const session = sessions[cameraId];
      const detection = session && detections[cameraId]?.session_id === session.id ? detections[cameraId] : undefined;
      const replayVisible = asset?.media_type === "video" && (ended[cameraId] || session?.status === "COMPLETED");
      return <article className={`active-stream-view ${canConfigure ? "configurable" : ""}`} key={cameraId} role={canConfigure ? "button" : undefined} tabIndex={canConfigure ? 0 : undefined} aria-label={canConfigure ? `Cấu hình Camera ${index + 1}` : undefined} onClick={() => canConfigure && onConfigure(cameraId)} onKeyDown={event => { if (canConfigure && (event.key === "Enter" || event.key === " ")) onConfigure(cameraId); }}>
        <h3>Camera {index + 1}</h3>
        {asset ? <><AuthenticatedMedia assetId={asset.id} mediaType={asset.media_type} label={`Media Camera ${index + 1}`} playing={Boolean(playbackRequested[cameraId]) || session?.status === "STARTING" || session?.status === "RUNNING"} playbackKey={session?.id} onEnded={() => { setPlaybackRequested(current => ({...current, [cameraId]: false})); setEnded(current => ({...current, [cameraId]: true})); }} /><DetectionOverlay result={detection} />
          {session && <div className={`stream-badge ${session.status.toLowerCase()}`}>{session.status}</div>}
          {session?.inference_fps != null && <div className="inference-fps">FPS infer <strong>{session.inference_fps.toFixed(1)}</strong></div>}
          {session?.status === "ERROR" && <div className="session-error">{session.error_code || "Phiên mô phỏng gặp lỗi."}</div>}
          {replayVisible && <button className="camera-replay" aria-label={`Replay Camera ${index + 1}`} disabled={Boolean(replaying)} onClick={event => { event.stopPropagation(); void replay(cameraId); }}>↻ <span>Replay</span></button>}
        </> : <div className="stream-empty-state"><strong>{canConfigure ? "Bấm vào đây để cấu hình" : "Camera chưa được cấu hình"}</strong><span>Camera {index + 1}</span></div>}
      </article>;
    })}</div>
    <ReviewModal
      isOpen={pendingReview !== null}
      onClose={() => undefined}
      snapshot={pendingReview?.snapshot_data}
      people={pendingReview?.people}
      detections={pendingReview?.detections}
      zones={pendingReview ? configurations[pendingReview.camera_id]?.zones : undefined}
      timer={reviewTimer}
      reviewSaving={reviewSaving}
      alertTitle={reviewTitle}
      alertSummary={pendingReview ? `${pendingReview.camera_id} · ${pendingReview.video_time.toFixed(1)}s` : ""}
      onReview={status => void review(status)}
      closeable={false}
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
