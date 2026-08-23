import {memo} from "react";
import {StreamViewer} from "./StreamViewer";
import type {UserRole} from "../../types";

export const MonitorPage = memo(function MonitorPage({active = true, role = "safety_manager", onConfigure}: {active?: boolean; role?: UserRole; onConfigure: (cameraId: string) => void}) {
  return <section className={`page ${active ? "active" : ""} camera-monitor-page`} id="monitor"><StreamViewer role={role} onConfigure={onConfigure} /></section>;
});
