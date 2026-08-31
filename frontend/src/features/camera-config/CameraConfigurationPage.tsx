import {useEffect, useRef, useState} from "react";
import {loadCameraConfiguration, saveCameraConfiguration} from "../../api/camera-configurations";
import {listMediaAssets} from "../../api/media-assets";
import type {CameraConfiguration, CameraConfigurationZone, MediaAsset, PpeRequirementUpdate, ZonePoint} from "../../types";
import {AuthenticatedMedia} from "../media/AuthenticatedMedia";
import {CameraViolationLog} from "./CameraViolationLog";
import {createZoneDraft, zoneGeometryConflict} from "../monitor/zone-editor";
import "./camera-config.css";

interface CameraConfigurationPageProps { cameraId: string; active?: boolean; showTitle?: boolean; onBack: () => void; onSaved: () => void; onDirtyChange?: (dirty: boolean) => void; }

const EMPTY_RULES: PpeRequirementUpdate = {profile: "hat_vest_v1", hat_required: false, vest_required: false, restricted_area_detection_enabled: false, zone_intrusion_enabled: true};

export function CameraConfigurationPage({cameraId, active = true, showTitle = true, onBack, onDirtyChange}: CameraConfigurationPageProps) {
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [saved, setSaved] = useState<CameraConfiguration>();
  const [draft, setDraft] = useState<CameraConfiguration>();
  const [selectedZoneId, setSelectedZoneId] = useState("");
  const [dragging, setDragging] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const savingRef = useRef(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [saveNotice, setSaveNotice] = useState("");
  const dirty = Boolean(draft && saved && JSON.stringify(draft) !== JSON.stringify(saved));

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError("");
    void Promise.all([loadCameraConfiguration(cameraId, controller.signal), listMediaAssets()])
      .then(([configuration, inventory]) => {
        const initial = configuration;
        setSaved(configuration); setDraft(initial);
        setSelectedZoneId(initial.zones[0]?.zone_id || "");
        setAssets(inventory.filter(asset => asset.status === "READY"));
      })
      .catch(reason => { if (!controller.signal.aborted) setError(errorText(reason, "Không thể tải cấu hình camera.")); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [cameraId]);

  useEffect(() => {
    onDirtyChange?.(dirty);
    const warnBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!dirty) return;
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", warnBeforeUnload);
      onDirtyChange?.(false);
    };
  }, [dirty, onDirtyChange]);

  useEffect(() => {
    if (!saveNotice) return;
    const timer = window.setTimeout(() => setSaveNotice(""), 3000);
    return () => window.clearTimeout(timer);
  }, [saveNotice]);

  if (loading || !draft || !saved) return <section className={`camera-config-page page ${active ? "active" : ""}`} role="status">{error || `Đang tải cấu hình Camera ${cameraNumber(cameraId)}…`}</section>;

  const selectedZone = draft.zones.find(zone => zone.zone_id === selectedZoneId);
  const rules = draft.ppe_requirements ?? EMPTY_RULES;
  const selectedAsset = assets.find(asset => asset.id === draft.asset_id);
  const conflict = zoneGeometryConflict(draft.zones);
  const incomplete = draft.zones.some(zone => zone.points.length !== 4);
  const selectedPointCount = selectedZone?.points.length ?? 0;
  const saveBlocker = conflict
    ? "Các vùng đang giao nhau. Điều chỉnh polygon trước khi lưu."
    : incomplete
      ? `Vùng đang chọn cần đủ 4 điểm (${selectedPointCount}/4).`
      : !dirty
        ? "Không có thay đổi mới."
        : "Sẵn sàng lưu cấu hình.";

  function updateDraft(update: Partial<CameraConfiguration>) {
    setDraft(current => current ? {...current, ...update} : current);
    setError(""); setMessage(""); setSaveNotice("");
  }
  function updateSelected(update: Partial<CameraConfigurationZone>) { updateDraft({zones: draft!.zones.map(zone => zone.zone_id === selectedZoneId ? {...zone, ...update} : zone)}); }
  function updateRules(update: Partial<PpeRequirementUpdate>) {
    const ppeRequirements = {...rules, ...update};
    updateDraft({
      ppe_requirements: ppeRequirements,
      zones: draft!.zones.map(zone => ({
        ...zone,
        ppe_requirements: {...zone.ppe_requirements, hat_required: ppeRequirements.hat_required, vest_required: ppeRequirements.vest_required},
      })),
    });
  }
  function createZone() {
    if (incomplete) return;
    const zone = {...createZoneDraft(draft!.zones), ppe_requirements: rules};
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
      const persisted = await saveCameraConfiguration(cameraId, configurationUpdate(currentDraft));
      setSaved(persisted); setDraft(persisted); setSaveNotice("Đã lưu");
    } catch (reason) { setError(errorText(reason, "Không thể lưu cấu hình camera.")); }
    finally { savingRef.current = false; setSaving(false); }
  }

  return <section className={`camera-config-page page ${active ? "active" : ""}`}>
    {showTitle && <div className="camera-config-toolbar"><div><p className="eyebrow">CAMERA {cameraNumber(cameraId)} · CONTROLLED DRAFT</p><h2>Cấu hình Camera {cameraNumber(cameraId)}</h2><p>Media, trạng thái máy, vùng và PPE chỉ được áp dụng trong một lần lưu.</p></div><button type="button" className="secondary-btn" onClick={onBack}>Quay lại Live Monitor</button></div>}
    <div className="camera-detail-layout">
      <div className="camera-config-workspace">
      <section className="camera-preview-panel" aria-label={`Màn hình Camera ${cameraNumber(cameraId)}`}>
        <div className="camera-config-media">
          {selectedAsset ? <AuthenticatedMedia assetId={selectedAsset.id} mediaType={selectedAsset.media_type} storageBackend={selectedAsset.storage_backend} label={`Preview Camera ${cameraNumber(cameraId)}`} playing /> : <div className="camera-config-empty">Chọn media để xem preview và vẽ vùng.</div>}
          <svg className="zone-config-overlay" viewBox="0 0 1 1" preserveAspectRatio="none" onPointerDown={addPoint} onPointerMove={movePoint} onPointerUp={() => setDragging(null)} onPointerLeave={() => setDragging(null)}>{draft.zones.map(zone => <g key={zone.zone_id} className={zone.zone_id === selectedZoneId ? "selected" : ""}>{zone.points.length > 1 && <polyline points={zone.points.map(point => `${point.x},${point.y}`).join(" ")} />}{zone.points.length === 4 && <polygon points={zone.points.map(point => `${point.x},${point.y}`).join(" ")} />}{zone.points.map((point, index) => <circle key={index} cx={point.x} cy={point.y} r="0.012" onPointerDown={event => { event.stopPropagation(); setSelectedZoneId(zone.zone_id); setDragging(index); }} />)}</g>)}</svg>
          <strong className="camera-config-title">Camera {cameraNumber(cameraId)}</strong>
          <span className={`camera-config-live-state ${selectedAsset ? "is-connected" : ""}`}><i />{selectedAsset ? "Camera đã kết nối" : "Chưa kết nối camera"}</span>
        </div>
      </section>
      <aside className="camera-config-controls" aria-label={`Thiết lập Camera ${cameraNumber(cameraId)}`}>
        <div className="settings-panel-heading"><div><span className="camera-config-section-kicker">THIẾT LẬP</span><h3>Kiểm soát camera</h3></div><small>Nguồn phát, trạng thái máy, vùng cấm và PPE.</small></div>
        <div className="camera-config-section asset-config-section">
          <div className="camera-config-card-heading"><div><strong>Nguồn camera</strong><small>Media dùng cho preview và inference.</small></div></div>
          <div className="asset-select-field-group">
            <label className="asset-select-field">MEDIA ĐANG DÙNG<select aria-label="Nguồn media" value={draft.asset_id ?? ""} onChange={event => updateDraft({asset_id: event.target.value || null})}><option value="">Chọn media đã sẵn sàng</option>{assets.map(asset => <option key={asset.id} value={asset.id} disabled={Boolean(asset.assigned_camera_id && asset.assigned_camera_id !== cameraId)}>{asset.display_name} · {asset.media_type === "video" ? "Video" : "Hình ảnh"}</option>)}</select></label>
            {draft.asset_id && <div className="asset-actions"><button type="button" className="secondary-btn disconnect-asset-btn" aria-label="Ngắt kết nối nguồn media" onClick={() => updateDraft({asset_id: null})}>Ngắt kết nối</button></div>}
          </div>
        </div>
        <div className="zone-config-panel camera-config-section machine-card">
          <div className="camera-config-card-heading"><div><strong>Vận hành &amp; PPE</strong><small>Trạng thái máy quyết định thời điểm áp dụng quy tắc bảo hộ.</small></div></div>
          <div className="operation-ppe-layout">
            <div className="operation-setting"><span className="setting-subtitle">TRẠNG THÁI MÁY</span><div className="machine-state-control">
              <div className="machine-state-options" role="group" aria-label="Trạng thái máy">
                <button type="button" aria-pressed={draft.machine_state === "running"} onClick={() => updateDraft({machine_state: "running"})}><i aria-hidden="true" />BẬT</button>
                <button type="button" aria-pressed={draft.machine_state === "stopped"} onClick={() => updateDraft({machine_state: "stopped"})}><i aria-hidden="true" />TẮT</button>
              </div>
              <p className="machine-state-description">{draft.machine_state === "running" ? "Hệ thống tự động kiểm tra mũ bảo hiểm và áo phản quang." : "Máy đã dừng, quy tắc PPE tạm thời không được kiểm tra."}</p>
            </div>
            </div>
            <div className="ppe-setting"><span className="setting-subtitle">YÊU CẦU BẢO HỘ</span><div className="ppe-requirement-switches camera-rule-switches"><RuleSwitch label="Mũ bảo hiểm" checked={rules.hat_required} onChange={value => updateRules({hat_required: value})} /><RuleSwitch label="Áo phản quang" checked={rules.vest_required} onChange={value => updateRules({vest_required: value})} /></div>{!selectedZone && <p className="ppe-scope-note">PPE áp dụng toàn bộ khung hình; không cần tạo vùng.</p>}</div>
          </div>
        </div>
        <div className="zone-config-panel camera-config-section zone-card">
          <div className="camera-config-card-heading"><div><strong>Vùng cấm</strong><small>Vùng được vẽ là vùng cấm, sẽ ghi cảnh báo khi có người bước vào.</small></div>{selectedZone && <span className={`zone-progress ${selectedPointCount === 4 ? "is-complete" : ""}`}>{selectedPointCount}/4 điểm</span>}</div>
          <div className="zone-config-actions"><label>CHỌN VÙNG<select aria-label="Chọn vùng" value={selectedZoneId} onChange={event => setSelectedZoneId(event.target.value)}>{draft.zones.map(zone => <option key={zone.zone_id} value={zone.zone_id}>{zone.display_name}</option>)}</select></label><div className="zone-actions"><button type="button" aria-label="Tạo vùng" onClick={createZone} disabled={incomplete}>{incomplete ? `Đang vẽ vùng · ${selectedPointCount}/4` : "+ Vẽ vùng cấm mới"}</button>{selectedZone && <button type="button" className="danger-link" onClick={() => { const next = draft.zones.filter(zone => zone.zone_id !== selectedZoneId); updateDraft({zones: next}); setSelectedZoneId(next[0]?.zone_id || ""); }}>Xóa vùng</button>}</div></div>
          {incomplete && <p className="zone-drawing-help" role="status">Bấm lần lượt 4 điểm trên khung camera để khép vùng.</p>}
          {selectedZone && <label className="zone-name-field">Tên vùng<input aria-label="Tên vùng" value={selectedZone.display_name} onChange={event => updateSelected({display_name: event.target.value})} /></label>}
        </div>
        {conflict && <p role="alert">Các vùng đang giao, chạm hoặc chứa nhau: {conflict.join(", ")}.</p>}{error && <p role="alert">{error}</p>}{!error && message && <p role="status">{message}</p>}
        <div className="camera-config-footer"><div className={`camera-save-state ${dirty && !incomplete && !conflict ? "is-ready" : ""}`}><strong>{dirty ? "Cấu hình chưa lưu" : "Cấu hình đã đồng bộ"}</strong><small>{saveBlocker}</small></div><div className="zone-save-actions"><button type="button" className="ppe-save-button" disabled={!dirty || saving || incomplete || Boolean(conflict)} onClick={() => void save()}>{saving ? "Đang lưu…" : "Lưu cấu hình"}</button></div></div>
      </aside>
      </div>
      <CameraViolationLog cameraId={cameraId} configuration={saved} />
    </div>
    {saveNotice && <aside className="toast show camera-config-save-toast" role="status" aria-live="polite"><span aria-hidden="true">✓</span><div><strong>{saveNotice}</strong></div></aside>}
  </section>;
}

function RuleSwitch({label, checked, onChange}: {label: string; checked: boolean; onChange: (value: boolean) => void}) { const accessibleLabel = label === "Mũ bảo hiểm" ? "Yêu cầu mũ bảo hộ" : label === "Áo phản quang" ? "Yêu cầu áo phản quang" : label; return <label className="ppe-switch-row"><span>{label}</span><input type="checkbox" aria-label={accessibleLabel} checked={checked} onChange={event => onChange(event.target.checked)} /><i aria-hidden="true"><b /></i></label>; }
function cameraNumber(cameraId: string): string { return cameraId.replace("cam_", ""); }
function clamp(value: number): number { return Math.max(0, Math.min(1, value)); }
function errorText(reason: unknown, fallback: string): string { return reason instanceof Error ? reason.message : fallback; }
function configurationUpdate(configuration: CameraConfiguration) {
  return {expected_revision: configuration.revision, asset_id: configuration.asset_id, machine_state: configuration.machine_state, ppe_requirements: configuration.ppe_requirements, zones: configuration.zones.map((zone, order) => ({...zone, order}))};
}
