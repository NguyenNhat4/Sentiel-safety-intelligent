import type {ReviewStatus} from "../../types";
import type {MonitorView} from "../monitor/use-monitor";

interface AlertPanelProps {
  view: MonitorView;
  reviewPending: boolean;
  reviewSaving: boolean;
  snapshot?: string;
  timer: string;
  onReview: (status: ReviewStatus) => void;
}

export function AlertPanel({view, reviewPending, reviewSaving, snapshot, timer, onReview}: AlertPanelProps) {
  return (
    <aside className={`alert-panel ${view.violation ? "violation" : ""}`} id="alert-panel">
      <div className="alert-top">
        <span className="critical-icon">!</span>
        <div><small>KẾT QUẢ QUY TẮC</small><h2>{view.alertTitle}</h2></div>
        <span className="severity">{view.severity}</span>
      </div>
      <p className="alert-summary">{view.alertSummary}</p>

      <div className="rule-chain">
        <RuleRow order="01" label="VỊ TRÍ" {...view.zoneRule} />
        <RuleRow order="02" label="TRẠNG THÁI MÁY" {...view.machineRule} />
        <RuleRow order="03" label="PPE" {...view.ppeRule} />
      </div>

      <div className="confidence">
        <div><span>Trạng thái inference</span><strong>{view.confidenceLabel}</strong></div>
        <div className="confidence-bar"><span style={{width: view.confidenceWidth}} /></div>
        <small>Rule PPE theo cấu hình đã lưu</small>
      </div>

      {snapshot && <img className="snapshot visible" src={snapshot} alt="Khung hình cần xác minh" />}

      <div className="escalation">
        <div><span>⌁</span><p><small>HUMAN IN THE LOOP</small><strong>{view.reviewMessage}</strong></p></div>
        <div className="timer"><strong>{timer}</strong><small>Chờ xác nhận</small></div>
      </div>

      {reviewPending && (
        <div className="alert-actions">
          <button className="ack" disabled={reviewSaving} onClick={() => onReview("acknowledged")}>✓ Vi phạm thực tế</button>
          <button className="false" disabled={reviewSaving} onClick={() => onReview("false_alarm")}>Bình thường / báo sai</button>
        </div>
      )}
      <p className="event-id">{view.eventStatus}</p>
    </aside>
  );
}

interface RuleRowProps {
  order: string;
  label: string;
  yes: boolean | null;
  text: string;
  badge: string;
}

function RuleRow({order, label, yes, text, badge}: RuleRowProps) {
  const stateClass = yes === null ? "" : yes ? "yes" : "no";
  return (
    <div className={`rule ${stateClass}`}>
      <span>{order}</span><p><small>{label}</small><strong>{text}</strong></p><b>{badge}</b>
    </div>
  );
}
