import type {ModelDetection, PersonDetection, ReviewStatus} from "../../types";
import {SnapshotOverlay} from "./SnapshotOverlay";

interface ReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  snapshot?: string;
  people?: PersonDetection[];
  detections?: ModelDetection[];
  timer: string;
  reviewSaving: boolean;
  alertTitle: string;
  alertSummary: string;
  onReview: (status: ReviewStatus) => void;
}

export function ReviewModal({
  isOpen,
  onClose,
  snapshot,
  people,
  detections,
  timer,
  reviewSaving,
  alertTitle,
  alertSummary,
  onReview,
}: ReviewModalProps) {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="modal-title">
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
          <button className="modal-close-btn" onClick={onClose} aria-label="Đóng pop-up">
            ×
          </button>
        </div>

        <div className="modal-body">
          <p className="modal-summary">{alertSummary}</p>
          {snapshot ? (
            <div className="modal-snapshot-container">
              <SnapshotOverlay snapshot={snapshot} people={people} detections={detections} />
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
    </div>
  );
}
