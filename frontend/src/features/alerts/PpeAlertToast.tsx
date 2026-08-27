import {useEffect, useRef} from "react";
import type {SafetyEvent} from "../../types";
import {cameraLabel, missingPpeLabel} from "./pending-violation";

export function PpeAlertToast({alert, onOpen, onClose}: {alert: SafetyEvent | null; onOpen: () => void; onClose: () => void}) {
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  useEffect(() => {
    if (!alert) return;
    const timeout = window.setTimeout(() => onCloseRef.current(), 3000);
    return () => window.clearTimeout(timeout);
  }, [alert]);

  if (!alert) return null;
  return <aside className="ppe-alert-toast" role="status" aria-label="Cảnh báo PPE mới">
    <button type="button" className="ppe-toast-content" onClick={onOpen}>
      <span>⚠</span><span><small>{cameraLabel(alert.camera_id)} · Cảnh báo PPE</small><strong>{missingPpeLabel(alert)}</strong><em>Bấm để xác minh</em></span>
    </button>
    <button type="button" className="ppe-toast-close" aria-label="Đóng thông báo PPE" onClick={onClose}>×</button>
  </aside>;
}
