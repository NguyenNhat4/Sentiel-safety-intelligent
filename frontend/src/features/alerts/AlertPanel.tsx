import type {ModelDetection, PersonDetection, ReviewStatus} from "../../types";
import type {MonitorView} from "../monitor/use-monitor";
import {getDetectionColor} from "../monitor/canvas";

interface AlertPanelProps {
  view: MonitorView;
  reviewPending: boolean;
  reviewSaving: boolean;
  people?: PersonDetection[];
  detections?: ModelDetection[];
  snapshot?: string;
  timer: string;
  onReview: (status: ReviewStatus) => void;
  onOpenModal?: () => void;
}

export function AlertPanel({
  view,
  reviewPending,
  reviewSaving,
  people = [],
  detections = [],
  snapshot,
  timer,
  onReview,
  onOpenModal,
}: AlertPanelProps) {
  const totalDetections = people.length + detections.length;

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

      <div className="detections-section">
        <div className="detections-header">
          <span>OBJECT DETECTIONS GROUPED BY PERSON ({totalDetections})</span>
        </div>
        {totalDetections === 0 ? (
          <p className="no-detections">Chưa phát hiện đối tượng trên khung hình</p>
        ) : (
          <div className="person-groups-container">
            {(() => {
              const personIndices = Array.from(
                new Set([
                  ...people.map((_, idx) => idx),
                  ...detections
                    .map(d => d.person_index)
                    .filter((idx): idx is number => idx !== null),
                ])
              ).sort((a, b) => a - b);

              return personIndices.map(pIdx => {
                const person = people[pIdx];
                const personColor = getDetectionColor("person", pIdx, person?.inside_zone);
                const associatedDetections = detections.filter(d => d.person_index === pIdx);
                return (
                  <div key={`person-group-${pIdx}`} className="person-group-card" style={{borderLeftColor: personColor}}>
                    <div className="person-group-header">
                      <span className="person-group-title" style={{color: personColor}}>
                        PERSON #{pIdx + 1}
                      </span>
                      {person && <span className="person-group-conf">{Math.round(person.confidence * 100)}%</span>}
                      {person && (
                        person.inside_zone ? (
                          <span className="detection-tag danger">TRONG ZONE</span>
                        ) : (
                          <span className="detection-tag safe">NGOÀI ZONE</span>
                        )
                      )}
                    </div>
                    {associatedDetections.length > 0 && (
                      <div className="person-items-list">
                        {associatedDetections.map((det, dIdx) => {
                          const itemColor = getDetectionColor(det.class_name, det.person_index);
                          return (
                            <div key={`person-${pIdx}-det-${dIdx}`} className="person-item-chip" style={{borderColor: itemColor}}>
                              <span className="detection-color-dot" style={{backgroundColor: itemColor}} />
                              <span className="detection-name">{det.class_name.toUpperCase()}</span>
                              <span className="detection-conf">{Math.round(det.confidence * 100)}%</span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              });
            })()}
            {(() => {
              const unassociated = detections.filter(d => d.person_index === null);
              if (!unassociated.length) return null;
              return (
                <div className="person-group-card unassociated-card">
                  <div className="person-group-header">
                    <span className="person-group-title">SCENE OBJECTS</span>
                    <span className="person-group-conf">{unassociated.length} vật thể</span>
                  </div>
                  <div className="person-items-list">
                    {unassociated.map((det, uIdx) => {
                      const itemColor = getDetectionColor(det.class_name, null);
                      return (
                        <div key={`unassoc-${uIdx}`} className="person-item-chip" style={{borderColor: itemColor}}>
                          <span className="detection-color-dot" style={{backgroundColor: itemColor}} />
                          <span className="detection-name">{det.class_name.toUpperCase()}</span>
                          <span className="detection-conf">{Math.round(det.confidence * 100)}%</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })()}
          </div>
        )}
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
        <>
          <div className="review-popup-trigger" onClick={onOpenModal}>
            <div className="trigger-badge">⚠ CÓ SỰ KIỆN CẦN XÁC MINH</div>
            <p>Nhấp vào đây để mở Pop-up xác minh <strong>Vi phạm</strong> hay <strong>Normal</strong></p>
            <button className="open-modal-btn" type="button" onClick={e => { e.stopPropagation(); onOpenModal?.(); }}>
              🔍 Mở Pop-up xác minh →
            </button>
          </div>

          <div className="alert-actions">
            <button className="ack" disabled={reviewSaving} onClick={() => onReview("acknowledged")}>✓ Vi phạm thực tế</button>
            <button className="false" disabled={reviewSaving} onClick={() => onReview("false_alarm")}>Bình thường / báo sai</button>
          </div>
        </>
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
