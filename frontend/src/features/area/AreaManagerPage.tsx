import {useCallback, useEffect, useState} from "react";
import {loadAcknowledgedEvents} from "../../api/events";
import {loadStatisticsSummary} from "../../api/statistics";
import type {SafetyEvent, StatisticsSummary} from "../../types";
import "./area-manager.css";

export function AreaManagerPage() {
  const [summary, setSummary] = useState<StatisticsSummary>();
  const [events, setEvents] = useState<SafetyEvent[]>([]);
  const [status, setStatus] = useState("Đang tải dữ liệu khu vực...");

  const load = useCallback(async () => {
    setStatus("Đang tải dữ liệu khu vực...");
    try {
      const [nextSummary, nextEvents] = await Promise.all([loadStatisticsSummary(), loadAcknowledgedEvents()]);
      setSummary(nextSummary);
      setEvents(nextEvents);
      setStatus("");
    } catch (reason) {
      setStatus(reason instanceof Error ? reason.message : "Không thể tải dữ liệu khu vực");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return <section className="page active area-page">
    <div className="area-heading">
      <div><p className="eyebrow">AREA MANAGEMENT</p><h2>Dashboard khu vực</h2><p>Theo dõi mức tuân thủ và sự kiện an toàn theo khu vực phụ trách.</p></div>
      <button className="secondary-btn" onClick={() => void load()}>↻ Làm mới</button>
    </div>
    {status && <div className="log-status">{status}</div>}
    {summary && <>
      <div className="area-kpis">
        <article><small>TỔNG SỰ KIỆN</small><strong>{summary.total_events}</strong></article>
        <article><small>CHƯA XÁC NHẬN</small><strong>{summary.unacknowledged_events}</strong></article>
        <article><small>TUÂN THỦ CHUNG</small><strong>{summary.overall_compliance_rate}%</strong></article>
      </div>
      <div className="area-grid">
        <article className="area-card"><h3>Tuân thủ theo khu vực</h3>{summary.zone_stats.map(zone => <div className="zone-row" key={zone.zone_id}><div><strong>{zone.zone_name}</strong><small>{zone.total_violations} vi phạm / {zone.total_detections} lượt phát hiện</small></div><span>{zone.compliance_rate}%</span></div>)}</article>
        <article className="area-card"><h3>Sự kiện xác nhận gần đây</h3>{events.length ? events.slice(0, 8).map(event => <div className="area-event" key={event.id}><div><strong>#{event.id} · {event.zone_id}</strong><small>{new Date(event.timestamp).toLocaleString("vi-VN", {hour12: false})}</small></div><span>{event.severity}</span></div>) : <p>Chưa có sự kiện được xác nhận.</p>}</article>
      </div>
    </>}
  </section>;
}
