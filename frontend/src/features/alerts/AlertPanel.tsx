import type {ModelDetection, PersonDetection} from "../../types";
import type {HitlLogEntry, MonitorView} from "../monitor/use-monitor";
import {isDisplayedPpeDetection} from "../monitor/canvas";

interface AlertPanelProps {
  view: MonitorView;
  reviewPending?: boolean;
  hitlLogs?: HitlLogEntry[];
  people?: PersonDetection[];
  detections?: ModelDetection[];
  timer?: string;
  onOpenModal?: (logId: string) => void;
}

export function AlertPanel({view, hitlLogs = [], people = [], detections = [], onOpenModal}: AlertPanelProps) {
  const ppeDetections = detections.filter(item => isDisplayedPpeDetection(item.class_name));
  const count = people.length + ppeDetections.length;
  const pendingLogCount = hitlLogs.filter(log => log.reviewStatus === "pending").length;

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

      <section className="hitl-log-section" aria-label="Nhật ký cảnh báo Human in the Loop">
        <div className="hitl-log-heading"><small>HUMAN IN THE LOOP · LOG CẦN REVIEW</small><strong>{pendingLogCount}</strong></div>
        {hitlLogs.length === 0 ? <p>Chưa có cảnh báo cần xác minh.</p> : <div className="hitl-log-list">
          {hitlLogs.map(log => <button type="button" className={`hitl-log ${log.tone}`} key={log.id} onClick={() => onOpenModal?.(log.id)}>
            <span>{log.tone === "critical" ? "!" : "⚠"}</span><div><strong>{log.title}</strong><small>{log.detail} · {log.reviewStatus === "pending" ? "chờ review" : "đã review"}</small></div>
          </button>)}
        </div>}
      </section>

      <div className="detections-section">
        <div className="detections-header"><span>OBJECT DETECTIONS GROUPED BY PERSON ({count})</span></div>
        {count === 0 ? <p className="no-detections">Chưa phát hiện đối tượng trên khung hình</p> : <div className="person-groups-container">
          {people.map((person, index) => <div className="person-group-card" key={`person-${person.track_id ?? index}`}>
            <div className="person-group-header"><span className="person-group-title">PERSON #{person.track_id ?? index + 1}</span><span className="person-group-conf">{Math.round(person.confidence * 100)}%</span></div>
          </div>)}
          {ppeDetections.map((item, index) => <div className="person-item-chip" key={`ppe-${index}`}>
            <span className="detection-name">{item.class_name.toUpperCase()}</span><span className="detection-conf">{Math.round(item.confidence * 100)}%</span>
          </div>)}
        </div>}
      </div>

      <div className="confidence">
        <div><span>Trạng thái inference</span><strong>{view.confidenceLabel}</strong></div>
        <div className="confidence-bar"><span style={{width: view.confidenceWidth}} /></div>
        <small>Rule PPE theo cấu hình đã lưu</small>
      </div>
    </aside>
  );
}

interface RuleRowProps { order: string; label: string; yes: boolean | null; text: string; badge: string; }

function RuleRow({order, label, yes, text, badge}: RuleRowProps) {
  const state = yes === null ? "" : yes ? "yes" : "no";
  return <div className={`rule ${state}`}><span>{order}</span><p><small>{label}</small><strong>{text}</strong></p><b>{badge}</b></div>;
}
