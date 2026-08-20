import {StreamViewer} from "./StreamViewer";
import type {UserRole} from "../../types";

export function MonitorPage({role = "system_admin"}: {role?: UserRole}) {
  return <section className="page active camera-monitor-page" id="monitor"><StreamViewer role={role} /></section>;
}
