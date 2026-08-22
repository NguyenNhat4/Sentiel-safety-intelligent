import {useCallback, useEffect, useMemo, useRef, useState} from "react";
import {mediaUrl} from "../../api/config";
import {getAccessToken, getHlsAccessToken} from "../../api/auth";
import {CameraDetectionClient} from "../../api/camera-detection-client";
import {cameraStreamUrl, disconnectStream, getStreamConfiguration, listStreamerCameras, updateStreamConfiguration} from "../../api/stream-config";
import type {CameraInferenceResult, StreamMapping, UserRole} from "../../types";
import {DetectionOverlay} from "./DetectionOverlay";
import {HlsVideo, type HlsVideoState} from "./HlsVideo";
import {normalizeMappings, sameMappings} from "./stream-mapping";
import "./stream.css";

const CAMERA_IDS = ["cam_1", "cam_2", "cam_3", "cam_4"];
const cameraLabel = (index: number) => `Camera ${index + 1}`;
const POLL_INTERVAL_MS = 15_000;
const configuredTransport = (import.meta.env.VITE_STREAM_TRANSPORT || "hls") as "mjpeg" | "hls";

export function StreamViewer({role}: {role: UserRole}) {
  const isAdmin = role === "system_admin";
  const [cameras, setCameras] = useState<string[]>([]);
  const [mappings, setMappings] = useState<StreamMapping[]>([]);
  const [states, setStates] = useState<Record<string, HlsVideoState>>({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [hlsToken, setHlsToken] = useState("");
  const [detections, setDetections] = useState<Record<string, CameraInferenceResult>>({});
  const mappingsRef = useRef(mappings);
  mappingsRef.current = mappings;

  useEffect(() => {
    let disposed = false;
    let timer: number | undefined;
    const refresh = async () => {
      try {
        const access = await getHlsAccessToken();
        if (disposed) return;
        setHlsToken(access.access_token);
        timer = window.setTimeout(refresh, Math.max(60_000, (access.expires_in - 120) * 1000));
        if (isAdmin) {
          try { setCameras(await listStreamerCameras(access.access_token)); }
          catch (reason) { if (!disposed) setError(reason instanceof Error ? reason.message : "Không thể tải camera."); }
        }
      } catch (reason) {
        if (!disposed) setError(reason instanceof Error ? reason.message : "Phiên xem HLS đã hết hạn.");
      }
    };
    if (configuredTransport === "hls") void refresh();
    return () => { disposed = true; if (timer) window.clearTimeout(timer); };
  }, [isAdmin]);

  const applyConfiguration = useCallback((next: StreamMapping[]) => {
    if (!sameMappings(mappingsRef.current, next)) setMappings(next);
  }, []);

  useEffect(() => {
    let disposed = false;
    let timer: number | undefined;
    let controller: AbortController | undefined;
    let failures = 0;
    const schedule = () => {
      if (disposed || document.visibilityState === "hidden") return;
      const backoff = Math.min(POLL_INTERVAL_MS * 2 ** failures, 60_000);
      timer = window.setTimeout(poll, backoff * (0.8 + Math.random() * 0.4));
    };
    const poll = async () => {
      controller?.abort();
      controller = new AbortController();
      try {
        applyConfiguration(normalizeMappings(await getStreamConfiguration(controller.signal)));
        failures = 0;
        setError("");
      } catch (reason) {
        if ((reason as Error).name !== "AbortError") {
          failures += 1;
          setError(reason instanceof Error ? reason.message : "Không thể tải cấu hình stream.");
        }
      } finally {
        if (!disposed) setLoading(false);
        schedule();
      }
    };
    const visibilityChanged = () => {
      if (timer) window.clearTimeout(timer);
      if (document.visibilityState === "hidden") controller?.abort();
      else void poll();
    };
    void poll();
    if (isAdmin && configuredTransport === "mjpeg") void listStreamerCameras("").then(setCameras).catch(() => undefined);
    document.addEventListener("visibilitychange", visibilityChanged);
    return () => {
      disposed = true;
      controller?.abort();
      if (timer) window.clearTimeout(timer);
      document.removeEventListener("visibilitychange", visibilityChanged);
    };
  }, [applyConfiguration, isAdmin]);

  const byCamera = useMemo(() => new Map(mappings.map(mapping => [mapping.camera_id, mapping])), [mappings]);

  useEffect(() => {
    const accessToken = getAccessToken();
    if (!accessToken || configuredTransport !== "hls" || mappings.length === 0) return;
    let disposed = false;
    let retryTimer: number | undefined;
    let retryAttempt = 0;
    const scheduleRetry = () => {
      if (disposed || retryTimer) return;
      const delay = Math.min(1000 * 2 ** retryAttempt++, 30_000);
      retryTimer = window.setTimeout(() => { retryTimer = undefined; void connect(); }, delay);
    };
    const client = new CameraDetectionClient({
      accessToken,
      cameraIds: mappings.map(mapping => mapping.camera_id),
      onResult: result => {
        const current = mappingsRef.current.find(mapping => mapping.camera_id === result.camera_id);
        if (current?.stream_camera_id !== result.stream_camera_id) return;
        setDetections(values => ({...values, [result.camera_id]: result}));
      },
      onFailure: message => { setError(message); scheduleRetry(); },
    });
    const connect = async () => {
      try { await client.connect(); retryAttempt = 0; }
      catch (reason) { if (!disposed) { setError(reason instanceof Error ? reason.message : "Không thể nhận detection camera."); scheduleRetry(); } }
    };
    void connect();
    return () => { disposed = true; if (retryTimer) window.clearTimeout(retryTimer); client.close(); };
  }, [mappings]);
  async function selectStream(cameraId: string, streamCameraId: string) {
    setBusy(true); setError("");
    try {
      if (mappings.some(mapping => mapping.stream_camera_id === streamCameraId && mapping.camera_id !== cameraId)) throw new Error("Stream này đã được gán cho camera khác.");
      applyConfiguration((await updateStreamConfiguration([...mappings.filter(mapping => mapping.camera_id !== cameraId), {camera_id: cameraId, stream_camera_id: streamCameraId, machine_state: "stopped"}])).mappings);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể kết nối stream."); }
    finally { setBusy(false); }
  }
  async function disconnect(cameraId: string) {
    setBusy(true); setError("");
    try { applyConfiguration((await disconnectStream(cameraId)).mappings); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể ngắt stream."); }
    finally { setBusy(false); }
  }
  if (loading) return <div className="stream-empty-state"><strong>Đang tải stream</strong><span>Đang kiểm tra camera active.</span></div>;

  return <div className="monitor-stream-shell">
    {isAdmin && <div className="stream-config-panel"><div><p className="eyebrow">SYSTEM ADMIN · STREAM ROUTING</p><h2>Điều phối camera</h2><p>Chọn stream cho từng ô Live Monitor. Chỉ Quản trị hệ thống có thể thay đổi.</p></div><div className="stream-config-grid">{CAMERA_IDS.map((cameraId, index) => { const mapping = byCamera.get(cameraId); const label = cameraLabel(index); return <label className="stream-config-item" key={cameraId}><span>{label}</span><select aria-label={`Stream cho ${label}`} value={mapping?.stream_camera_id ?? ""} disabled={busy} onChange={event => { if (event.target.value) void selectStream(cameraId, event.target.value); }}><option value="">Chọn stream</option>{cameras.map(camera => <option key={camera} value={camera} disabled={mappings.some(item => item.stream_camera_id === camera && item.camera_id !== cameraId)}>{camera}</option>)}</select>{mapping && <button type="button" disabled={busy} onClick={() => void disconnect(cameraId)}>Ngắt kết nối</button>}</label>; })}</div>{error && <p className="stream-config-error" role="alert">{error}</p>}</div>}
    {error && !isAdmin && <div className="stream-empty-state" role="alert"><strong>Không thể tải stream</strong><span>{error}</span></div>}
    <div className="monitor-camera-grid">{CAMERA_IDS.map((cameraId, index) => { const mapping = byCamera.get(cameraId); const state = states[cameraId]; const label = cameraLabel(index); const detection = detections[cameraId]?.stream_camera_id === mapping?.stream_camera_id ? detections[cameraId] : undefined; return <article className="active-stream-view" key={cameraId}><h3>{label}</h3>{mapping ? <>{configuredTransport === "hls" ? (hlsToken ? <><HlsVideo src={mediaUrl(`/hls/cameras/${encodeURIComponent(mapping.stream_camera_id)}/index.m3u8`)} accessToken={hlsToken} label={`Live stream ${label}`} onStateChange={next => setStates(current => current[cameraId] === next ? current : {...current, [cameraId]: next})} /><DetectionOverlay result={detection} /></> : <div className="stream-empty-state"><strong>Đang cấp quyền HLS</strong><span>Đang xác thực phiên xem camera.</span></div>) : <img src={cameraStreamUrl(mapping.stream_camera_id)} alt={`Live stream ${label}`} />}{(configuredTransport === "mjpeg" || state === "live") && <div className="stream-badge"><i className="live-dot" /> LIVE</div>}{configuredTransport === "hls" && hlsToken && state !== "live" && <div className="stream-badge">{state === "paused_hidden" ? "PAUSED" : state === "failed" ? "FAILED" : "CONNECTING"}</div>}</> : <div className="stream-empty-state"><strong>Chưa kết nối</strong><span>Chưa có stream được gán.</span></div>}</article>; })}</div>
  </div>;
}
