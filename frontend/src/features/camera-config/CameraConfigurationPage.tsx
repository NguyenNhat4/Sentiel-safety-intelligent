import {useEffect, useRef, useState} from "react";
import {loadCameraConfiguration, saveCameraConfiguration} from "../../api/camera-configurations";
import {listMediaAssets} from "../../api/media-assets";
import type {CameraConfiguration, CameraConfigurationZone, MediaAsset, PpeRequirementUpdate, ZonePoint} from "../../types";
import {AuthenticatedMedia} from "../media/AuthenticatedMedia";
import {createZoneDraft, zoneGeometryConflict} from "../monitor/zone-editor";
import "./camera-config.css";

interface CameraConfigurationPageProps { cameraId: string; active?: boolean; showTitle?: boolean; onBack: () => void; onSaved: () => void; }

const EMPTY_RULES: PpeRequirementUpdate = {profile: "hat_vest_v1", hat_required: false, vest_required: false, restricted_area_detection_enabled: false, zone_intrusion_enabled: true};

export function CameraConfigurationPage({cameraId, active = true, showTitle = true, onBack, onSaved}: CameraConfigurationPageProps) {
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [saved, setSaved] = useState<CameraConfiguration>();
  const [draft, setDraft] = useState<CameraConfiguration>();
  const [pendingRules, setPendingRules] = useState<PpeRequirementUpdate>(EMPTY_RULES);
  const [selectedZoneId, setSelectedZoneId] = useState("");
  const [dragging, setDragging] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const savingRef = useRef(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError("");
    void Promise.all([loadCameraConfiguration(cameraId, controller.signal), listMediaAssets()])
      .then(([configuration, inventory]) => {
        const initial = configuration;
        setSaved(configuration); setDraft(initial);
        setSelectedZoneId(initial.zones[0]?.zone_id || "");
        setPendingRules(initial.zones[0]?.ppe_requirements ?? EMPTY_RULES);
        setAssets(inventory.filter(asset => asset.status === "READY"));
      })
      .catch(reason => { if (!controller.signal.aborted) setError(errorText(reason, "Không thể tải cấu hình camera.")); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [cameraId]);

  if (loading || !draft || !saved) return <section className={`camera-config-page page ${active ? "active" : ""}`} role="status">{error || `Đang tải cấu hình Camera ${cameraNumber(cameraId)}…`}</section>;

  const selectedZone = draft.zones.find(zone => zone.zone_id === selectedZoneId);
  const rules = selectedZone?.ppe_requirements ?? pendingRules;
  const selectedAsset = assets.find(asset => asset.id === draft.asset_id);
  const conflict = zoneGeometryConflict(draft.zones);
  const incomplete = draft.zones.some(zone => zone.points.length !== 4);
  const dirty = JSON.stringify(draft) !== JSON.stringify(saved);

  function updateDraft(update: Partial<CameraConfiguration>) {
    setDraft(current => current ? {...current, ...update} : current);
    setError(""); setMessage("");
  }
  function updateSelected(update: Partial<CameraConfigurationZone>) { updateDraft({zones: draft!.zones.map(zone => zone.zone_id === selectedZoneId ? {...zone, ...update} : zone)}); }
  function updateRules(update: Partial<PpeRequirementUpdate>) {
    if (selectedZone) updateSelected({ppe_requirements: {...rules, ...update}});
    else setPendingRules(current => ({...current, ...update}));
  }
  function createZone() {
    if (incomplete) return;
    const zone = {...createZoneDraft(draft!.zones), ppe_requirements: pendingRules};
    updateDraft({zones: [...draft!.zones, zone]}); setSelectedZoneId(zone.zone_id);
    setMessage("Bấm bốn điểm trên media để hoàn thành vùng.");
  }
  function pointFromEvent(event: React.PointerEvent<SVGSVGElement>): ZonePoint | null {
    const rect = event.currentTarget.getBoundingClientRect();
    if (!rect.width || !rect.height || !Number.isFinite(event.clientX) || !Number.isFinite(event.clientY)) return null;
    return {x: clamp((event.clientX - rect.left) / rect.width), y: clamp((event.clientY - rect.top) / rect.height)};
  }
  function addPoint(event: React.PointerEvent<SVGSVGElement>) {
    if (!selectedZone || selectedZone.points.length >= 4 || dragging !== null) return;
    const point = pointFromEvent(event); if (point) updateSelected({points: [...selectedZone.points, point]});
  }
  function movePoint(event: React.PointerEvent<SVGSVGElement>) {
    if (!selectedZone || dragging === null) return;
    const point = pointFromEvent(event); if (!point) return;
    const points = [...selectedZone.points]; points[dragging] = point; updateSelected({points});
  }
  async function save() {
    const currentDraft = draft;
    if (savingRef.current || !currentDraft || incomplete || conflict) return;
    savingRef.current = true; setSaving(true); setError(""); setMessage("");
    try {
      await saveCameraConfiguration(cameraId, {expected_revision: currentDraft.revision, asset_id: currentDraft.asset_id, machine_state: currentDraft.machine_state, zones: currentDraft.zones.map((zone, order) => ({...zone, order}))});
      onSaved();
    } catch (reason) { setError(errorText(reason, "Không thể lưu cấu hình camera.")); }
    finally { savingRef.current = false; setSaving(false); }
  }

  return <section className={`camera-config-page page ${active ? "active" : ""}`}>
    <div className="camera-config-toolbar"><div><p className="eyebrow">CAMERA {cameraNumber(cameraId)} · CONTROLLED DRAFT</p>{showTitle && <h2>Cấu hình Camera {cameraNumber(cameraId)}</h2>}<p>Media, trạng thái máy, vùng và PPE chỉ được áp dụng trong một lần lưu.</p></div><button type="button" className="secondary-btn" onClick={onBack}>Quay lại Live Monitor</button></div>
    <div className="camera-config-section asset-config-section">
      <div className="camera-config-section-heading"><div><span className="camera-config-section-kicker">01 · NGUỒN</span><strong>Nguồn media</strong></div><small>Chọn video hoặc hình ảnh để cấu hình vùng.</small></div>
      <div className="asset-select-field-group">
        <label className="asset-select-field">Nguồn media<select aria-label="Nguồn media" value={draft.asset_id ?? ""} onChange={event => updateDraft({asset_id: event.target.value || null})}><option value="">Chọn media đã sẵn sàng</option>{assets.map(asset => <option key={asset.id} value={asset.id} disabled={Boolean(asset.assigned_camera_id && asset.assigned_camera_id !== cameraId)}>{asset.display_name} · {asset.media_type === "video" ? "Video" : "Hình ảnh"}</option>)}</select></label>
        {draft.asset_id && <div className="asset-actions"><button type="button" className="secondary-btn disconnect-asset-btn" aria-label="Ngắt kết nối nguồn media" onClick={() => updateDraft({asset_id: null})}>Ngắt kết nối nguồn</button></div>}
      </div>
    </div>
    <div className="camera-config-media">
      {selectedAsset ? <AuthenticatedMedia assetId={selectedAsset.id} mediaType={selectedAsset.media_type} label={`Preview Camera ${cameraNumber(cameraId)}`} playing /> : <div className="camera-config-empty">Chọn media để xem preview và vẽ vùng.</div>}
      <svg className="zone-config-overlay" viewBox="0 0 1 1" preserveAspectRatio="none" onPointerDown={addPoint} onPointerMove={movePoint} onPointerUp={() => setDragging(null)} onPointerLeave={() => setDragging(null)}>{draft.zones.map(zone => <g key={zone.zone_id} className={zone.zone_id === selectedZoneId ? "selected" : ""}>{zone.points.length > 1 && <polyline points={zone.points.map(point => `${point.x},${point.y}`).join(" ")} />}{zone.points.length === 4 && <polygon points={zone.points.map(point => `${point.x},${point.y}`).join(" ")} />}{zone.points.map((point, index) => <circle key={index} cx={point.x} cy={point.y} r="0.012" onPointerDown={event => { event.stopPropagation(); setSelectedZoneId(zone.zone_id); setDragging(index); }} />)}</g>)}</svg>
      <strong className="camera-config-title">Camera {cameraNumber(cameraId)}</strong>
    </div>
    <div className="zone-config-panel camera-config-section">
      <div className="camera-config-section-heading"><div><span className="camera-config-section-kicker">02 · KHU VỰC & LUẬT</span><strong>Cấu hình vùng an toàn</strong></div><small>Chọn vùng, trạng thái máy và yêu cầu PPE.</small></div>
      <div className="machine-state-control"><div><strong>Trạng thái máy</strong><small>{draft.machine_state === "running" ? "Máy đang chạy · kiểm tra PPE" : "Máy đã dừng · bỏ qua PPE"}</small></div><button type="button" role="switch" aria-checked={draft.machine_state === "running"} aria-label="Trạng thái máy" onClick={() => updateDraft({machine_state: draft.machine_state === "running" ? "stopped" : "running"})}>{draft.machine_state === "running" ? "Đang chạy" : "Đã dừng"}</button></div>
      <div className="zone-config-actions"><label>Vùng<select aria-label="Chọn vùng" value={selectedZoneId} onChange={event => setSelectedZoneId(event.target.value)}>{draft.zones.map(zone => <option key={zone.zone_id} value={zone.zone_id}>{zone.display_name}</option>)}</select></label><div className="zone-actions"><button type="button" onClick={createZone} disabled={incomplete}>Tạo vùng</button>{selectedZone && <button type="button" className="danger-link" onClick={() => { const next = draft.zones.filter(zone => zone.zone_id !== selectedZoneId); updateDraft({zones: next}); setSelectedZoneId(next[0]?.zone_id || ""); }}>Xóa vùng</button>}</div></div>
      {selectedZone && <label className="zone-name-field">Tên vùng<input aria-label="Tên vùng" value={selectedZone.display_name} onChange={event => updateSelected({display_name: event.target.value})} /></label>}
      <div className="ppe-requirement-switches camera-rule-switches"><RuleSwitch label="Yêu cầu mũ bảo hộ" checked={rules.hat_required} onChange={value => updateRules({hat_required: value})} /><RuleSwitch label="Yêu cầu áo phản quang" checked={rules.vest_required} onChange={value => updateRules({vest_required: value})} /></div>
      {!selectedZone && <p>Hãy tạo một vùng để cấu hình yêu cầu PPE.</p>}
      {conflict && <p role="alert">Các vùng đang giao, chạm hoặc chứa nhau: {conflict.join(", ")}.</p>}{error && <p role="alert">{error}</p>}{!error && message && <p role="status">{message}</p>}
      <div className="camera-config-section-footer"><div><span className="camera-config-section-kicker">03 · HOÀN TẤT</span><small>{dirty ? "Bạn có thay đổi chưa lưu." : "Cấu hình đã đồng bộ."}</small></div><div className="zone-save-actions"><button type="button" className="secondary-btn" onClick={onBack}>Quay lại</button><button type="button" className="ppe-save-button" disabled={!dirty || saving || incomplete || Boolean(conflict)} onClick={() => void save()}>{saving ? "Đang lưu…" : "Lưu cấu hình"}</button></div></div>
    </div>
  </section>;
}

function RuleSwitch({label, checked, onChange}: {label: string; checked: boolean; onChange: (value: boolean) => void}) { return <label className="ppe-switch-row"><span>{label}</span><input type="checkbox" aria-label={label} checked={checked} onChange={event => onChange(event.target.checked)} /><i aria-hidden="true"><b /></i><em>{checked ? "ON" : "OFF"}</em></label>; }
function cameraNumber(cameraId: string): string { return cameraId.replace("cam_", ""); }
function clamp(value: number): number { return Math.max(0, Math.min(1, value)); }
function errorText(reason: unknown, fallback: string): string { return reason instanceof Error ? reason.message : fallback; }
