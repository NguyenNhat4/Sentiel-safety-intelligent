import {useEffect, useMemo, useState} from "react";
import {getHlsAccessToken} from "../../api/auth";
import {mediaUrl} from "../../api/config";
import {loadMonitoringZones, saveMonitoringZones} from "../../api/monitoring-zones";
import {getStreamConfiguration} from "../../api/stream-config";
import type {MonitoringZone, StreamMapping, ZonePoint} from "../../types";
import {HlsVideo} from "../monitor/HlsVideo";
import {createZoneDraft, zoneGeometryConflict} from "../monitor/zone-editor";
import {PpeRequirementsPanel} from "../rules/PpeRequirementsPanel";
import "./camera-config.css";

export function CameraConfigurationPage() {
  const [mappings, setMappings] = useState<StreamMapping[]>([]);
  const [cameraId, setCameraId] = useState("");
  const [hlsToken, setHlsToken] = useState("");
  const [revision, setRevision] = useState(0);
  const [savedZones, setSavedZones] = useState<MonitoringZone[]>([]);
  const [zones, setZones] = useState<MonitoringZone[]>([]);
  const [selectedZoneId, setSelectedZoneId] = useState("");
  const [dragging, setDragging] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void Promise.all([getStreamConfiguration(), getHlsAccessToken()])
      .then(([configuration, access]) => {
        if (!active) return;
        setMappings(configuration.mappings);
        setCameraId(current => current || configuration.mappings[0]?.camera_id || "");
        setHlsToken(access.access_token);
      })
      .catch(reason => active && setError(errorText(reason, "Không thể tải camera")))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!cameraId) return;
    let active = true;
    setLoading(true);
    setError("");
    setMessage("");
    void loadMonitoringZones(cameraId)
      .then(collection => {
        if (!active) return;
        const visible = collection.zones.filter(zone => zone.enabled);
        setRevision(collection.revision);
        setSavedZones(visible);
        setZones(visible);
        setSelectedZoneId(visible[0]?.zone_id || "");
      })
      .catch(reason => active && setError(errorText(reason, "Không thể tải vùng")))
      .finally(() => active && setLoading(false));
    return () => { active = false; };
  }, [cameraId]);

  const mapping = mappings.find(item => item.camera_id === cameraId);
  const selectedZone = zones.find(zone => zone.zone_id === selectedZoneId);
  const dirty = JSON.stringify(zones) !== JSON.stringify(savedZones);
  const conflict = zoneGeometryConflict(zones);
  const hasIncompleteZone = zones.some(zone => zone.points.length !== 4);

  function createZone() {
    if (hasIncompleteZone) return;
    const next = createZoneDraft(zones);
    setZones(current => [...current, next]);
    setSelectedZoneId(next.zone_id);
    setMessage("Bấm bốn điểm trên video để hoàn thành vùng.");
  }

  function updateSelected(update: Partial<MonitoringZone>) {
    setZones(current => current.map(zone => zone.zone_id === selectedZoneId ? {...zone, ...update} : zone));
    setMessage("");
  }

  function pointFromEvent(event: React.PointerEvent<SVGSVGElement>): ZonePoint | null {
    const rect = event.currentTarget.getBoundingClientRect();
    if (!rect.width || !rect.height || !Number.isFinite(event.clientX) || !Number.isFinite(event.clientY)) return null;
    return {
      x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
      y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)),
    };
  }

  function addPoint(event: React.PointerEvent<SVGSVGElement>) {
    if (!selectedZone || selectedZone.points.length >= 4 || dragging !== null) return;
    const point = pointFromEvent(event);
    if (point) updateSelected({points: [...selectedZone.points, point]});
  }

  function movePoint(event: React.PointerEvent<SVGSVGElement>) {
    if (!selectedZone || dragging === null) return;
    const point = pointFromEvent(event);
    if (!point) return;
    const points = [...selectedZone.points];
    points[dragging] = point;
    updateSelected({points});
  }

  async function saveZones() {
    if (!cameraId || hasIncompleteZone || conflict) return;
    setSaving(true);
    setError("");
    try {
      const saved = await saveMonitoringZones(cameraId, revision, zones.map((zone, order) => ({...zone, order})));
      const visible = saved.zones.filter(zone => zone.enabled);
      setRevision(saved.revision);
      setSavedZones(visible);
      setZones(visible);
      setSelectedZoneId(current => visible.some(zone => zone.zone_id === current) ? current : visible[0]?.zone_id || "");
      setMessage("Đã lưu vùng camera.");
    } catch (reason) {
      setError(errorText(reason, "Không thể lưu vùng"));
    } finally {
      setSaving(false);
    }
  }

  const title = useMemo(() => mapping ? `${mapping.camera_id} — ${mapping.stream_camera_id}` : cameraId, [cameraId, mapping]);
  if (loading && !mappings.length) return <section className="camera-config-page page active" role="status">Đang tải cấu hình camera…</section>;

  return <section className="camera-config-page page active">
    <div className="camera-config-toolbar">
      <div><p className="eyebrow">CAMERA · ZONE · RULE</p><h2>Cấu hình camera</h2><p>Chọn một camera, vẽ vùng và lưu rule riêng cho vùng đó.</p></div>
      <label>Chọn camera<select aria-label="Chọn camera" value={cameraId} onChange={event => setCameraId(event.target.value)}>
        {mappings.map((item, index) => <option key={item.camera_id} value={item.camera_id}>{`Camera ${index + 1} — ${item.stream_camera_id}`}</option>)}
      </select></label>
    </div>
    {!mapping ? <div className="camera-config-empty">Chưa có camera nào được kết nối trong Live Monitor.</div> : <>
      <div className="camera-config-media">
        {hlsToken && <HlsVideo src={mediaUrl(`/hls/cameras/${encodeURIComponent(mapping.stream_camera_id)}/index.m3u8`)} accessToken={hlsToken} label={`Cấu hình Camera ${mappings.indexOf(mapping) + 1}`} />}
        <svg className="zone-config-overlay" viewBox="0 0 1 1" preserveAspectRatio="none" onPointerDown={addPoint} onPointerMove={movePoint} onPointerUp={() => setDragging(null)} onPointerLeave={() => setDragging(null)}>
          {zones.map(zone => <g key={zone.zone_id} className={zone.zone_id === selectedZoneId ? "selected" : ""}>
            {zone.points.length > 1 && <polyline points={zone.points.map(point => `${point.x},${point.y}`).join(" ")} />}
            {zone.points.length === 4 && <polygon points={zone.points.map(point => `${point.x},${point.y}`).join(" ")} />}
            {zone.points.map((point, index) => <circle key={index} cx={point.x} cy={point.y} r="0.012" onPointerDown={event => { event.stopPropagation(); setSelectedZoneId(zone.zone_id); setDragging(index); }} />)}
          </g>)}
        </svg>
        <strong className="camera-config-title">{title}</strong>
      </div>
      <div className="zone-config-panel">
        <div className="zone-config-actions">
          <label>Vùng<select aria-label="Chọn vùng" value={selectedZoneId} onChange={event => setSelectedZoneId(event.target.value)}>
            {!zones.length && <option value="">Chưa có vùng nào</option>}
            {zones.map(zone => <option key={zone.zone_id} value={zone.zone_id}>{zone.display_name}</option>)}
          </select></label>
          <button type="button" onClick={createZone} disabled={hasIncompleteZone}>Tạo vùng</button>
          {selectedZone && <button type="button" className="danger-link" onClick={() => { setZones(current => current.filter(zone => zone.zone_id !== selectedZoneId)); setSelectedZoneId(""); }}>Xóa vùng</button>}
        </div>
        {selectedZone && <label className="zone-name-field">Tên vùng<input aria-label="Tên vùng" value={selectedZone.display_name} onChange={event => updateSelected({display_name: event.target.value})} /></label>}
        {conflict && <p role="alert">Các vùng đang giao, chạm hoặc chứa nhau: {conflict.join(", ")}.</p>}
        {error && <p role="alert">{error}</p>}
        {!error && message && <p role="status">{message}</p>}
        <div className="zone-save-actions"><button type="button" className="secondary-btn" disabled={!dirty || saving} onClick={() => { setZones(savedZones); setSelectedZoneId(savedZones[0]?.zone_id || ""); }}>Hủy</button><button type="button" className="ppe-save-button" disabled={!dirty || saving || hasIncompleteZone || Boolean(conflict)} onClick={() => void saveZones()}>{saving ? "Đang lưu…" : "Lưu vùng"}</button></div>
      </div>
      {selectedZone?.points.length === 4 && <PpeRequirementsPanel cameraId={cameraId} zoneId={selectedZone.zone_id} />}
    </>}
  </section>;
}

function errorText(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback;
}
