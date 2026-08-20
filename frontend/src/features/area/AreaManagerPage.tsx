import {useCallback, useEffect, useState} from "react";
import {loadAreaEvents, updateAreaEvent} from "../../api/events";
import {assetUrl} from "../../api/config";
import {loadStatisticsSummary} from "../../api/statistics";
import type {SafetyEvent, StatisticsSummary} from "../../types";
import {EventDetailDialog} from "../events/EventDetailDialog";
import "./area-manager.css";

export function AreaManagerPage() {
  const [summary, setSummary] = useState<StatisticsSummary>();
  const [events, setEvents] = useState<SafetyEvent[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<SafetyEvent>();
  const [updatingEventId, setUpdatingEventId] = useState<number>();
  const [status, setStatus] = useState("Đang tải dữ liệu khu vực...");
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setStatus("Đang tải dữ liệu khu vực...");
    try {
      const [nextSummary, nextEvents] = await Promise.all([loadStatisticsSummary(), loadAreaEvents()]);
      setSummary(nextSummary);
      setEvents(nextEvents);
      setSelectedEvent(current => nextEvents.find(event => event.id === current?.id) ?? nextEvents[0]);
      setStatus("");
    } catch (reason) {
      setStatus(reason instanceof Error ? reason.message : "Không thể tải dữ liệu khu vực");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

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

  return <section className="page active area-page">
    <div className="area-heading">
      <div><p className="eyebrow">AREA MANAGEMENT</p><h2>Dashboard khu vực</h2><p>Theo dõi mức tuân thủ và log an toàn của khu vực phụ trách.</p></div>
      <button className="secondary-btn" onClick={() => void load()}>↻ Làm mới</button>
    </div>
    {status && <div className="log-status">{status}</div>}
    {summary && <>
      <div className="area-kpis">
        <article><small>VI PHẠM CHÍNH THỨC</small><strong>{summary.total_events}</strong></article>
        <article><small>CHƯA XÁC NHẬN</small><strong>{summary.unacknowledged_events}</strong></article>
        <article><small>TUÂN THỦ CHUNG</small><strong>{summary.overall_compliance_rate}%</strong></article>
      </div>
      <div className="area-grid">
        <article className="area-card"><h3>Tuân thủ theo khu vực</h3>{summary.zone_stats.map(zone => <div className="zone-row" key={zone.zone_id}><div><strong>{zone.zone_name}</strong><small>{zone.total_violations} vi phạm / {zone.total_detections} lượt phát hiện</small></div><span>{zone.compliance_rate}%</span></div>)}</article>
        <article className="area-card area-log-card"><h3>Kết quả xác minh gần đây</h3>{events.length ? events.map(event => <button type="button" className={`area-event ${selectedEvent?.id === event.id ? "selected" : ""}`} aria-label={`Xem audit sự kiện #${event.id}`} key={event.id} onClick={() => { setSelectedEvent(event); setSelectedEventId(event.id); }}><div><strong>#{event.id} · {event.zone_id}</strong><small>{new Date(event.timestamp).toLocaleString("vi-VN", {hour12: false})}</small></div><span className={event.status === "false_alarm" ? "false-alarm" : ""}>{statusLabel(event.status)}</span></button>) : <p>Chưa có kết quả xác minh.</p>}</article>
      </div>
      {selectedEvent && <EventDetail event={selectedEvent} saving={updatingEventId === selectedEvent.id} onOutcome={setEventOutcome} />}
    </>}
    <EventDetailDialog eventId={selectedEventId} onClose={() => setSelectedEventId(null)} />
  </section>;
}

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
