import {memo, useCallback, useEffect, useState} from "react";
import {loadAreaEvents, updateAreaEvent} from "../../api/events";
import {assetUrl} from "../../api/config";
import {loadStatisticsSummary} from "../../api/statistics";
import {listCameraConfigurations} from "../../api/camera-configurations";
import {listMediaAssets} from "../../api/media-assets";
import type {CameraConfiguration, MediaAsset} from "../../types";
import type {SafetyEvent, StatisticsSummary} from "../../types";
import {EventDetailDialog} from "../events/EventDetailDialog";
import "./area-manager.css";

interface AreaManagerPageProps {
  active?: boolean;
}

let areaCache: { summary: StatisticsSummary; events: SafetyEvent[]; configurations: CameraConfiguration[]; assets: MediaAsset[] } | null = null;

export const AreaManagerPage = memo(function AreaManagerPage({active = true}: AreaManagerPageProps) {
  const [summary, setSummary] = useState<StatisticsSummary | undefined>(() => areaCache?.summary);
  const [events, setEvents] = useState<SafetyEvent[]>(() => areaCache?.events ?? []);
  const [configurations, setConfigurations] = useState<CameraConfiguration[]>(() => areaCache?.configurations ?? []);
  const [assets, setAssets] = useState<MediaAsset[]>(() => areaCache?.assets ?? []);
  const [selectedEvent, setSelectedEvent] = useState<SafetyEvent | undefined>(() => areaCache?.events[0]);
  const [updatingEventId, setUpdatingEventId] = useState<number>();
  const [status, setStatus] = useState(() => areaCache ? "" : "Đang tải dữ liệu khu vực...");
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);

  const load = useCallback(async () => {
    if (!areaCache) {
      setStatus("Đang tải dữ liệu khu vực...");
    }
    try {
      const [nextSummary, nextEvents, nextConfigurations, nextAssets] = await Promise.all([loadStatisticsSummary(), loadAreaEvents(), listCameraConfigurations(), listMediaAssets()]);
      areaCache = { summary: nextSummary, events: nextEvents, configurations: nextConfigurations, assets: nextAssets };
      setSummary(nextSummary);
      setEvents(nextEvents);
      setConfigurations(nextConfigurations);
      setAssets(nextAssets);
      setSelectedEvent(current => nextEvents.find(event => event.id === current?.id) ?? nextEvents[0]);
      setStatus("");
    } catch (reason) {
      setStatus(reason instanceof Error ? reason.message : "Không thể tải dữ liệu khu vực");
    }
  }, []);

  useEffect(() => {
    if (active) void load();
  }, [active, load]);

  async function setEventOutcome(event: SafetyEvent, outcome: "resolved" | "false_alarm") {
    setUpdatingEventId(event.id);
    try {
      const updated = await updateAreaEvent(event.id, outcome);
      setEvents(current => current.map(item => item.id === updated.id ? updated : item));
      setSelectedEvent(updated);
      setStatus("");
    } catch (reason) {
      setStatus(reason instanceof Error ? reason.message : "Không thể cập nhật log");
    } finally {
      setUpdatingEventId(undefined);
    }
  }

  return <section className={`page area-page ${active ? "active" : ""}`}>
    <div className="area-heading"><p>Theo dõi mức tuân thủ và log an toàn của khu vực phụ trách.</p><button className="secondary-btn" onClick={() => void load()}>↻ Làm mới</button></div>
    {status && <div className="log-status">{status}</div>}
    {summary && <>
      <div className="area-kpis">
        <article><small>VI PHẠM CHÍNH THỨC</small><strong>{summary.total_events}</strong></article>
        <article><small>CHƯA XÁC NHẬN</small><strong>{summary.unacknowledged_events}</strong></article>
        <article><small>TUÂN THỦ CHUNG</small><strong>{summary.overall_compliance_rate}%</strong></article>
      </div>
      <div className="area-grid">
        <article className="area-card"><h3>Tuân thủ theo khu vực</h3>{cameraIds.map((cameraId, index) => { const configuration = configurations.find(item => item.camera_id === cameraId); const asset = assets.find(item => item.id === configuration?.asset_id); const stats = summary.zone_stats[index]; return <div className="zone-row" key={cameraId}><div><strong>{asset?.display_name ?? `Camera ${index + 1} · Chưa gán media`}</strong><small>{stats ? `${stats.total_violations} vi phạm / ${stats.total_detections} lượt phát hiện` : "Chưa có dữ liệu phát hiện"}</small></div><span>{stats ? `${stats.compliance_rate}%` : "—"}</span></div>; })}</article>
        <article className="area-card area-log-card"><h3>Kết quả xác minh gần đây</h3>{events.length ? events.map(event => <button type="button" className={`area-event ${selectedEvent?.id === event.id ? "selected" : ""}`} aria-label={`Xem audit sự kiện #${event.id}`} key={event.id} onClick={() => { setSelectedEvent(event); setSelectedEventId(event.id); }}><div><strong>#{event.id} · {event.zone_id}</strong><small>{new Date(event.timestamp).toLocaleString("vi-VN", {hour12: false})}</small></div><span className={event.status === "false_alarm" ? "false-alarm" : ""}>{statusLabel(event.status)}</span></button>) : <p>Chưa có kết quả xác minh.</p>}</article>
      </div>
      {selectedEvent && <EventDetail event={selectedEvent} saving={updatingEventId === selectedEvent.id} onOutcome={setEventOutcome} />}
    </>}
    <EventDetailDialog eventId={selectedEventId} onClose={() => setSelectedEventId(null)} />
  </section>;
});

const cameraIds = ["cam_1", "cam_2", "cam_3", "cam_4"];

function EventDetail({event, saving, onOutcome}: {event: SafetyEvent; saving: boolean; onOutcome: (event: SafetyEvent, outcome: "resolved" | "false_alarm") => void}) {
  const canUpdate = event.status === "acknowledged" || event.status === "unacknowledged";
  const snapshot = assetUrl(event.snapshot_path);
  const people = event.details?.people?.length ?? 0;
  return <article className="area-card area-event-detail">
    <div><p className="eyebrow">CHI TIẾT LOG #{event.id}</p><h3>{event.event_type}</h3></div>
    <div className="area-detail-grid">
      {snapshot ? <img src={snapshot} alt={`Snapshot log ${event.id}`} /> : <div className="area-snapshot-empty">Không có snapshot</div>}
      <div><p><strong>Khu vực:</strong> {event.zone_id}</p><p><strong>Mức độ:</strong> {event.severity}</p><p><strong>Thời gian:</strong> {new Date(event.timestamp).toLocaleString("vi-VN", {hour12: false})}</p><p><strong>Phát hiện:</strong> {people} người</p><p><strong>Trạng thái:</strong> {statusLabel(event.status)}</p>
      {canUpdate && <div className="area-event-actions"><button className="secondary-btn" disabled={saving} onClick={() => onOutcome(event, "false_alarm")}>Không phải vi phạm</button><button className="ppe-save-button" disabled={saving} onClick={() => onOutcome(event, "resolved")}>{saving ? "Đang lưu..." : "Đã giải quyết"}</button></div>}</div>
    </div>
  </article>;
}

function statusLabel(status: SafetyEvent["status"]): string {
  return {acknowledged: "Chờ giải quyết", resolved: "Đã giải quyết", false_alarm: "Không phải vi phạm", unacknowledged: "Chưa xác nhận"}[status];
}
