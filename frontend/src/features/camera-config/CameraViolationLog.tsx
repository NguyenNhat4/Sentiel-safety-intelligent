import {useCallback, useEffect, useState} from "react";
import {loadCameraEvents} from "../../api/events";
import type {EventStatus, SafetyEvent} from "../../types";
import {EventDetailDialog} from "../events/EventDetailDialog";

interface CameraViolationLogProps {
  cameraId: string;
}

export function CameraViolationLog({cameraId}: CameraViolationLogProps) {
  const [events, setEvents] = useState<SafetyEvent[]>([]);
  const [status, setStatus] = useState("Đang tải log vi phạm...");
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setStatus("Đang tải log vi phạm...");
    try {
      const loaded = await loadCameraEvents(cameraId);
      setEvents(loaded);
      setStatus(loaded.length ? "" : "Camera này chưa có log vi phạm.");
    } catch (reason) {
      setStatus(reason instanceof Error ? reason.message : "Không thể tải log vi phạm của camera.");
    }
  }, [cameraId]);

  useEffect(() => {
    void load();
  }, [load]);

  const openCount = events.filter(event => event.status === "unacknowledged" || event.status === "acknowledged").length;

  return <section className="camera-config-section camera-violation-log" aria-labelledby="camera-violation-log-heading">
    <div className="camera-config-section-heading">
      <div className="camera-log-heading-copy"><span className="camera-config-section-kicker">04 · LỊCH SỬ</span><strong id="camera-violation-log-heading">Nhật ký vi phạm Camera {cameraNumber(cameraId)}</strong><small>Event được ghi nhận riêng cho camera này.</small></div>
      <button type="button" className="secondary-btn" onClick={() => void load()}>↻ Làm mới</button>
    </div>
    <div className="camera-log-summary" aria-label="Tổng quan log vi phạm">
      <div><span>TỔNG LOG</span><strong>{events.length}</strong></div>
      <div><span>ĐANG XỬ LÝ</span><strong>{openCount}</strong></div>
      <div><span>ĐÃ ĐÓNG</span><strong>{Math.max(events.length - openCount, 0)}</strong></div>
    </div>
    {status && <p className="camera-violation-log-status" role="status">{status}</p>}
    {events.length > 0 && <div className="camera-violation-list" role="list" aria-label={`Danh sách log Camera ${cameraNumber(cameraId)}`}>
      {events.map(event => <CameraViolationRow key={event.id} event={event} onOpen={() => setSelectedEventId(event.id)} />)}
    </div>}
    <EventDetailDialog eventId={selectedEventId} onClose={() => setSelectedEventId(null)} />
  </section>;
}

function CameraViolationRow({event, onOpen}: {event: SafetyEvent; onOpen: () => void}) {
  return <article className="camera-violation-row" role="listitem">
    <div>
      <strong>#{event.id} · {violationLabel(event)}</strong>
      <small>{new Date(event.timestamp).toLocaleString("vi-VN", {hour12: false})} · Vùng {event.zone_id} · <b>{event.severity.toUpperCase()}</b></small>
    </div>
    <div className="camera-violation-row-meta">
      <span className={`camera-event-status ${event.status}`}>{statusLabel(event.status)}</span>
      <button type="button" className="event-audit-button" aria-label={`Xem chi tiết vi phạm #${event.id}`} onClick={onOpen}>Xem chi tiết →</button>
    </div>
  </article>;
}

function violationLabel(event: SafetyEvent): string {
  if (event.event_type === "zone_intrusion") return "Xâm nhập vùng";
  if (event.event_type === "missing_ppe_and_intrusion") return "Thiếu PPE và xâm nhập vùng";
  if (event.event_type === "missing_ppe") return "Thiếu PPE";
  return "Vi phạm an toàn";
}

function statusLabel(status: EventStatus): string {
  return {acknowledged: "Đã xác nhận", resolved: "Đã xử lý", false_alarm: "Báo sai", unacknowledged: "Chưa xác nhận"}[status];
}

function cameraNumber(cameraId: string): string {
  return cameraId.replace("cam_", "");
}
