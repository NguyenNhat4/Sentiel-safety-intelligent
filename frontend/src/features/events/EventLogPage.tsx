import {memo, useCallback, useEffect, useState} from "react";
import {assetUrl} from "../../api/config";
import {loadReviewedEvents, subscribeToSafetyEventUpdates} from "../../api/events";
import type {ReviewStatus, SafetyEvent} from "../../types";
import {EventDetailDialog} from "./EventDetailDialog";
import {violationRuleLabel} from "../alerts/violation-copy";

interface EventLogPageProps {active: boolean}

const eventCache = new Map<ReviewStatus, SafetyEvent[]>();

export const EventLogPage = memo(function EventLogPage({active}: EventLogPageProps) {
  const [reviewStatus, setReviewStatus] = useState<ReviewStatus>("acknowledged");
  const [events, setEvents] = useState<SafetyEvent[]>(() => eventCache.get("acknowledged") ?? []);
  const [status, setStatus] = useState(() => {
    const cached = eventCache.get("acknowledged");
    if (!cached) return "Đang chờ dữ liệu";
    return cached.length ? "" : emptyState("acknowledged");
  });
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);

  const loadEvents = useCallback(async () => {
    const cached = eventCache.get(reviewStatus);
    if (!cached) {
      setStatus("Đang tải nhật ký vi phạm...");
    }
    try {
      const loaded = await loadReviewedEvents(reviewStatus);
      eventCache.set(reviewStatus, loaded);
      setEvents(loaded);
      setStatus(loaded.length ? "" : emptyState(reviewStatus));
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Không thể tải nhật ký vi phạm");
    }
  }, [reviewStatus]);

  useEffect(() => {
    if (active) void loadEvents();
  }, [active, loadEvents]);

  useEffect(() => {
    if (!active) return;
    return subscribeToSafetyEventUpdates(() => {
      void loadEvents();
    });
  }, [active, loadEvents]);

  function handleSelectStatus(nextStatus: ReviewStatus) {
    setReviewStatus(nextStatus);
    const cached = eventCache.get(nextStatus);
    if (cached) {
      setEvents(cached);
      setStatus(cached.length ? "" : emptyState(nextStatus));
    } else {
      setEvents([]);
      setStatus("Đang tải nhật ký vi phạm...");
    }
  }

  return (
    <section className={`page ${active ? "active" : ""}`} id="violation-log">
      <div className="log-toolbar">
        <div>
          <p className="eyebrow">SAFETY RECORDS</p>
          <p>Tách riêng vi phạm thực tế và báo sai, nhưng giữ cả hai để truy vết quyết định.</p>
        </div>
        <button className="secondary-btn" onClick={() => void loadEvents()}>↻ Làm mới</button>
      </div>
      <div className="event-log-tabs" role="tablist" aria-label="Lọc kết quả xác minh">
        <FilterTab current={reviewStatus} value="acknowledged" onSelect={handleSelectStatus}>Vi phạm đã xác nhận</FilterTab>
        <FilterTab current={reviewStatus} value="false_alarm" onSelect={handleSelectStatus}>Báo sai</FilterTab>
      </div>
      {status && <div className="log-status">{status}</div>}
      <div className="event-log-list">{events.map(event => <EventCard key={event.id} event={event} onOpen={() => setSelectedEventId(event.id)} />)}</div>
      <EventDetailDialog eventId={selectedEventId} onClose={() => setSelectedEventId(null)} />
    </section>
  );
});

function FilterTab({children, current, value, onSelect}: {
  children: string;
  current: ReviewStatus;
  value: ReviewStatus;
  onSelect: (status: ReviewStatus) => void;
}) {
  return <button
    type="button"
    role="tab"
    aria-selected={current === value}
    className={current === value ? "active" : ""}
    onClick={() => onSelect(value)}
  >{children}</button>;
}

function EventCard({event, onOpen}: {event: SafetyEvent; onOpen: () => void}) {
  const snapshot = assetUrl(event.snapshot_path);
  const people = Array.isArray(event.details?.people) ? event.details.people.length : 0;
  const timestamp = Number(event.details?.video_timestamp_seconds || 0).toFixed(1);
  return (
    <article className="event-card">
      {snapshot ? <img src={snapshot} alt={`Snapshot sự kiện ${event.id}`} /> : <div className="log-status">Không có snapshot</div>}
      <div className="event-card-body">
        <div className="event-card-head">
          <div><small>EVENT #{event.id}</small><h3>{eventTypeLabel(event)}</h3><time>{formatTimestamp(event.timestamp)}</time></div>
          <span className={`event-badge ${event.status === "false_alarm" ? "false-alarm" : ""}`}>{event.status === "false_alarm" ? "BÁO SAI" : "ĐÃ XÁC NHẬN"}</span>
        </div>
        <div className="event-meta">
          <span>Vùng: {event.decision_context?.scene.zone_name ?? event.zone_id}</span><span>Camera: {event.camera_name ?? event.camera_id}</span>
          <span>Mức độ: {event.severity}</span><span>Xác nhận: {event.acknowledged_by || "Safety Officer"}</span>
        </div>
        <p className="event-details">Phát hiện {people} người · Video {timestamp}s · {event.details?.review_result || "actual_violation"}</p>
        <button type="button" className="event-audit-button" aria-label={`Xem audit sự kiện #${event.id}`} onClick={onOpen}>Xem chuỗi quyết định →</button>
      </div>
    </article>
  );
}

function emptyState(status: ReviewStatus): string {
  return status === "false_alarm" ? "Chưa có cảnh báo nào được đánh dấu báo sai." : "Chưa có vi phạm nào được xác nhận.";
}

function eventTypeLabel(event: SafetyEvent): string {
  const ruleKeys = event.decision_context?.rule.triggered_rule_keys ?? [];
  if (ruleKeys.length) return violationRuleLabel(ruleKeys);
  if (event.event_type === "missing_ppe_and_intrusion") return "Thiếu PPE trong vùng cấm";
  if (event.event_type === "zone_intrusion") return "Có người vào vùng cấm";
  return "Vi phạm an toàn";
}

function formatTimestamp(timestamp: string): string {
  return new Date(timestamp).toLocaleString("vi-VN", {hour12: false});
}
