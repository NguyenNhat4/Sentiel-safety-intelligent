import {useEffect, useRef, useState} from "react";
import {assetUrl} from "../../api/config";
import {getCachedEventDetail, loadEventDetail, subscribeToSafetyEventUpdates} from "../../api/events";
import type {EventDetail, StoredDecisionContext} from "../../types";
import {SnapshotZoneOverlay} from "../alerts/SnapshotZoneOverlay";
import {violationRuleItemLabel} from "../alerts/violation-copy";
import "./event-detail.css";

interface EventDetailDialogProps {
  eventId: number | null;
  onClose: () => void;
}

export function EventDetailDialog({eventId, onClose}: EventDetailDialogProps) {
  const [detail, setDetail] = useState<EventDetail>();
  const [error, setError] = useState("");
  const dialogRef = useRef<HTMLDialogElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (eventId === null) return;
    let active = true;
    setDetail(getCachedEventDetail(eventId));
    setError("");
    void loadEventDetail(eventId)
      .then(event => { if (active) setDetail(event); })
      .catch(reason => {
        if (active) setError(reason instanceof Error ? reason.message : "Không thể tải chi tiết sự kiện");
      });
    return () => { active = false; };
  }, [eventId]);

  useEffect(() => {
    if (eventId === null) return;
    let active = true;
    const unsubscribe = subscribeToSafetyEventUpdates(update => {
      if (!update.eventIds.includes(eventId)) return;
      setError("");
      void loadEventDetail(eventId, {forceRefresh: true})
        .then(event => { if (active) setDetail(event); })
        .catch(reason => {
          if (active) setError(reason instanceof Error ? reason.message : "Không thể tải chi tiết sự kiện");
        });
    });
    return () => {
      active = false;
      unsubscribe();
    };
  }, [eventId]);

  useEffect(() => {
    if (!detail && !error) return;
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) {
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "");
    }
    closeRef.current?.focus();
  }, [detail, error]);

  if (eventId === null) return null;
  if (!detail && !error) return <div className="event-detail-loading" role="status">Đang tải chi tiết sự kiện...</div>;

  const headingId = `event-detail-title-${eventId}`;
  return (
    <dialog
      ref={dialogRef}
      className="event-detail-dialog"
      aria-modal="true"
      aria-labelledby={headingId}
      onCancel={event => { event.preventDefault(); onClose(); }}
      onKeyDown={event => { if (event.key === "Escape") onClose(); }}
    >
      <div className="event-detail-header">
        <div>
          <p className="eyebrow">DECISION AUDIT</p>
          <h2 id={headingId}>Chi tiết sự kiện #{eventId}</h2>
        </div>
        <button ref={closeRef} className="event-detail-close" aria-label="Đóng chi tiết sự kiện" onClick={onClose}>×</button>
      </div>
      {error ? <div className="event-detail-error" role="alert">{error}</div> : detail && <EventDetailContent detail={detail} />}
    </dialog>
  );
}

function EventDetailContent({detail}: {detail: EventDetail}) {
  const context = detail.decision_context;
  const snapshot = assetUrl(detail.snapshot_path);
  return <>
    <section className="event-summary-block" aria-labelledby="event-summary-heading">
      <div>
        <h3 id="event-summary-heading">Tóm tắt sự việc</h3>
        <span>Nguồn: {detail.summary.source === "llm" ? "AI có kiểm soát" : "Mẫu xác định"}</span>
      </div>
      <p>{renderHighlightedSummary(detail.summary.text, context?.human_review.actor_name)}</p>
    </section>
    {snapshot ? (
      <div className="event-detail-snapshot event-detail-snapshot-overlay">
        <SnapshotZoneOverlay snapshot={snapshot} alt={`Snapshot đã làm mờ của sự kiện ${detail.id}`} zones={context?.scene.zone_points.length === 4 ? [{zone_id: context.scene.zone_id, display_name: context.scene.zone_name, points: context.scene.zone_points, enabled: true, order: 0}] : []} />
      </div>
    ) : null}
    {context ? <AuditChain context={context} /> : <section className="event-limited-audit">
      <h3>Audit hạn chế</h3>
      <p>Sự kiện này được tạo bởi phiên bản hệ thống cũ nên không có decision context đầy đủ. Hệ thống không tự suy diễn dữ liệu lịch sử còn thiếu.</p>
    </section>}
  </>;
}

function renderHighlightedSummary(summary: string, reviewerName?: string) {
  const terms = ["xâm nhập vùng", reviewerName].filter((term): term is string => Boolean(term));
  if (!terms.length) return summary;
  const escapedTerms = terms.map(term => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`(${escapedTerms.join("|")})`, "gi");
  return summary.split(pattern).map((part, index) =>
    terms.some(term => part.localeCompare(term, undefined, {sensitivity: "accent"}) === 0)
      ? <strong key={`${part}-${index}`}>{part}</strong>
      : <span key={`${part}-${index}`}>{part}</span>,
  );
}

function AuditChain({context}: {context: StoredDecisionContext}) {
  const people = context.scene.people;
  const maxConfidence = people.length ? Math.max(...people.map(person => person.confidence)) : null;
  return <div className="event-audit-chain">
    <section>
      <h3 className="audit-step-title"><span aria-hidden="true">1</span> AI quan sát</h3>
      <p>{people.length} người được ghi nhận{maxConfidence === null ? "" : ` · Confidence cao nhất ${formatPercent(maxConfidence)}`}.</p>
      <div className="audit-facts">
        <span>Frame #{context.scene.frame_id}</span>
        <span>Video {context.scene.video_timestamp_seconds.toFixed(1)}s</span>
        <span>{context.scene.detections.length} detection PPE</span>
      </div>
    </section>
    <section>
      <h3 className="audit-step-title"><span aria-hidden="true">2</span> Rule quyết định</h3>
      <p>{context.system_decision.result === "violate" ? "Hệ thống yêu cầu review" : "Hệ thống đánh giá bình thường"} · Mức độ {context.system_decision.severity}.</p>
      <div className="audit-facts">
        <span>{context.rule.rule_version}</span>
        <span>{context.rule.ppe_profile}</span>
        <span>{context.scene.machine_state === "running" ? "Máy đang chạy" : "Máy đã dừng"}</span>
        <span>{context.scene.zone_name}</span>
      </div>
      <ul>{context.rule.triggered_rule_keys.map(rule => <li key={rule}>{violationRuleItemLabel(rule)}</li>)}</ul>
    </section>
    <section>
      <h3 className="audit-step-title"><span aria-hidden="true">3</span> Human review</h3>
      <p><strong>{context.human_review.actor_name}</strong> xác nhận: {context.human_review.outcome === "actual_violation" ? "Vi phạm thực tế" : "Báo sai"}.</p>
      <time>{new Date(context.human_review.reviewed_at).toLocaleString("vi-VN", {hour12: false})}</time>
    </section>
  </div>;
}

function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}
