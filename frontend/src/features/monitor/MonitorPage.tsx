import {StreamViewer} from "./StreamViewer";
import type {UserRole} from "../../types";

export function MonitorPage({role = "safety_manager", onConfigure}: {role?: UserRole; onConfigure: (cameraId: string) => void}) {
  return <section className="page active camera-monitor-page" id="monitor"><StreamViewer role={role} onConfigure={onConfigure} /></section>;
}
