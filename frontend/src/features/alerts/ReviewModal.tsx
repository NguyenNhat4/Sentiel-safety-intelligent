import {createPortal} from "react-dom";
import type {MonitoringZone, PersonDetection, ReviewStatus} from "../../types";
import {SnapshotZoneOverlay} from "./SnapshotZoneOverlay";

interface ReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  snapshot?: string;
  people?: PersonDetection[];
  zones?: MonitoringZone[];
  timer: string;
  reviewSaving: boolean;
  alertTitle: string;
  alertSummary: string;
  onReview: (status: ReviewStatus) => void;
  closeable?: boolean;
  compact?: boolean;
}

export function ReviewModal({
  isOpen,
  onClose,
  snapshot,
  people,
  zones,
  timer,
  reviewSaving,
  alertTitle,
  alertSummary,
  onReview,
  closeable = true,
  compact = false,
}: ReviewModalProps) {
  if (!isOpen) return null;
  const affectedZones = [...new Set(
    people?.flatMap(person => person.active_violations
      ?.filter(violation => violation.is_new && violation.zone_id && violation.zone_id !== "camera_wide")
      .map(violation => violation.zone_id as string) ?? []) ?? [],
  )];

  return createPortal(
    <div className={`modal-backdrop ${compact ? "camera-review-backdrop" : ""}`} onClick={closeable ? onClose : undefined} role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className="modal-card" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <span className="modal-warning-icon">⚠</span>
            <div>
              <small>HUMAN IN THE LOOP · REVIEW POP-UP</small>
              <h3 id="modal-title">{alertTitle}</h3>
            </div>
          </div>
          <div className="modal-timer-badge">
            <strong>{timer}</strong>
            <small>Chờ xác nhận</small>
          </div>
          {closeable && <button className="modal-close-btn" onClick={onClose} aria-label="Đóng pop-up">×</button>}
        </div>

        <div className="modal-body">
          <p className="modal-summary">{alertSummary}</p>
          {affectedZones.length > 0 && (
            <div className="review-zone-list" aria-label="Các vùng cần xác minh">
              <strong>{affectedZones.length} vùng trong lần xác minh này</strong>
              {affectedZones.map(zoneId => <span key={zoneId}>{zoneId}</span>)}
            </div>
          )}
          {snapshot ? (
            <div className="modal-snapshot-container">
              <SnapshotZoneOverlay snapshot={snapshot} alt="Khung hình vi phạm cần xác minh" zones={zones?.filter(zone => affectedZones.includes(zone.zone_id))} />
            </div>
          ) : (
            <div className="modal-snapshot-placeholder">Không có hình ảnh xem trước</div>
          )}
        </div>

        <div className="modal-footer">
          <button
            className="ack-btn"
            disabled={reviewSaving}
            onClick={() => onReview("acknowledged")}
          >
            ✓ Vi phạm thực tế (VIOLATE)
          </button>
          <button
            className="false-btn"
            disabled={reviewSaving}
            onClick={() => onReview("false_alarm")}
          >
            Bình thường / báo sai (NORMAL)
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
