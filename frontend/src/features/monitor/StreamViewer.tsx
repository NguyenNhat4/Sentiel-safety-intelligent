import {useCallback, useEffect, useState} from "react";
import {cameraStreamUrl, disconnectStream, getStreamConfiguration, listStreamerCameras, updateStreamConfiguration} from "../../api/stream-config";
import type {StreamMapping, UserRole} from "../../types";
import "./stream.css";

const CAMERA_IDS = ["cam_1", "cam_2", "cam_3", "cam_4"];

export function StreamViewer({role}: {role: UserRole}) {
  const isAdmin = role === "system_admin";
  const [cameras, setCameras] = useState<string[]>([]);
  const [mappings, setMappings] = useState<StreamMapping[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const load = useCallback(async () => { setLoading(true); setError(""); try { const configuration = await getStreamConfiguration(); setMappings(configuration.mappings ?? (configuration.active_camera_id ? [{camera_id: "cam_1", stream_camera_id: configuration.active_camera_id}] : [])); if (isAdmin) setCameras(await listStreamerCameras()); } catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể tải cấu hình stream."); } finally { setLoading(false); } }, [isAdmin]);
  useEffect(() => { void load(); }, [load]);
  async function selectStream(cameraId: string, streamCameraId: string) { setBusy(true); setError(""); try { if (mappings.some(mapping => mapping.stream_camera_id === streamCameraId && mapping.camera_id !== cameraId)) throw new Error("Stream này đã được gán cho camera khác."); setMappings((await updateStreamConfiguration([...mappings.filter(mapping => mapping.camera_id !== cameraId), {camera_id: cameraId, stream_camera_id: streamCameraId}])).mappings); } catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể kết nối stream."); } finally { setBusy(false); } }
  async function disconnect(cameraId: string) { setBusy(true); setError(""); try { setMappings((await disconnectStream(cameraId)).mappings); } catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể ngắt stream."); } finally { setBusy(false); } }
  if (loading) return <div className="stream-empty-state"><strong>Đang tải stream</strong><span>Đang kiểm tra camera active.</span></div>;
  const byCamera = new Map(mappings.map(mapping => [mapping.camera_id, mapping]));
  return <div className="monitor-stream-shell">{isAdmin && <div className="stream-config-panel"><div><p className="eyebrow">SYSTEM ADMIN · STREAM ROUTING</p><h2>Điều phối camera</h2><p>Chọn stream cho từng ô Live Monitor. Chỉ Quản trị hệ thống có thể thay đổi.</p></div><div className="stream-config-grid">{CAMERA_IDS.map(cameraId => { const mapping = byCamera.get(cameraId); return <label className="stream-config-item" key={cameraId}><span>{cameraId}</span><select aria-label={`Stream cho ${cameraId}`} value={mapping?.stream_camera_id ?? ""} disabled={busy} onChange={event => { if (event.target.value) void selectStream(cameraId, event.target.value); }}><option value="">Chọn stream</option>{cameras.map(camera => <option key={camera} value={camera} disabled={mappings.some(item => item.stream_camera_id === camera && item.camera_id !== cameraId)}>{camera}</option>)}</select>{mapping && <button type="button" disabled={busy} onClick={() => void disconnect(cameraId)}>Ngắt kết nối</button>}</label>; })}</div>{error && <p className="stream-config-error" role="alert">{error}</p>}</div>}{error && !isAdmin && <div className="stream-empty-state" role="alert"><strong>Không thể tải stream</strong><span>{error}</span><button className="secondary-btn" onClick={() => void load()}>Thử lại</button></div>}<div className="monitor-camera-grid">{CAMERA_IDS.map(cameraId => { const mapping = byCamera.get(cameraId); return <article className="active-stream-view" key={cameraId}><h3>{cameraId}</h3>{mapping ? <><img src={cameraStreamUrl(mapping.stream_camera_id)} alt={`Live stream ${cameraId}`} /><div className="stream-badge"><i className="live-dot" /> LIVE · {mapping.stream_camera_id}</div></> : <div className="stream-empty-state"><strong>Chưa kết nối</strong><span>Chưa có stream được gán.</span></div>}</article>; })}</div></div>;
}
