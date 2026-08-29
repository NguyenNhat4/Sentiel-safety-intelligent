import type {SafetyEvent} from "../../types";
import {cameraLabel, isZoneAlert, missingPpeLabel, zoneLabel} from "./pending-violation";

export function PendingViolationList({alerts, onOpen}: {alerts: SafetyEvent[]; onOpen: (alert: SafetyEvent) => void}) {
  return <section className="pending-alerts" aria-labelledby="pending-alerts-title">
    <div className="pending-alerts-heading">
      <div><small>HUMAN IN THE LOOP</small><h2 id="pending-alerts-title">Cảnh báo chờ xử lý</h2></div>
      <strong aria-label={`${alerts.length} cảnh báo chưa xử lý`}>{alerts.length}</strong>
    </div>
    {alerts.length === 0 ? <p className="pending-alerts-empty">Không có cảnh báo chờ xử lý.</p> : <div className="pending-alert-list">
      {alerts.map(alert => <button type="button" className="pending-alert-row" key={alert.id} onClick={() => onOpen(alert)}>
        <span className={`pending-alert-kind ${isZoneAlert(alert) ? "zone" : "ppe"}`}>{isZoneAlert(alert) ? "VÙNG CẤM" : "PPE"}</span>
        <span><strong>{cameraLabel(alert.camera_id)}</strong><small>{isZoneAlert(alert) ? zoneLabel(alert) : missingPpeLabel(alert)}</small></span>
        <time dateTime={alert.timestamp}>{formatTime(alert.timestamp)}</time>
        <b>Chưa xử lý</b>
      </button>)}
    </div>}
  </section>;
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("vi-VN", {dateStyle: "short", timeStyle: "medium"}).format(new Date(value));
}
