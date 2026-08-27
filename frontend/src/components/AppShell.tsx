import {memo, type ReactNode} from "react";
import type {AuthenticatedUser} from "../types";

export type Page = "monitor" | "events" | "operations" | "area" | "admin" | "media-library" | "camera-config";

interface AppShellProps {
  page: Page;
  onNavigate: (page: Page) => void;
  user: AuthenticatedUser;
  onLogout: () => void;
  children: ReactNode;
  selectedCameraId?: string;
}

export const AppShell = memo(function AppShell({page, onNavigate, user, onLogout, children, selectedCameraId}: AppShellProps) {
  const title = page === "monitor" ? "Live Monitor" : page === "events" ? "Nhật ký vi phạm" : page === "operations" ? "Quan sát hệ thống" : page === "area" ? "Dashboard khu vực" : page === "media-library" ? "Thư viện media" : page === "camera-config" ? `Cấu hình Camera ${cameraNumber(selectedCameraId)}` : "Quản trị hệ thống";
  const initials = user.full_name.split(" ").filter(Boolean).slice(-2).map(part => part[0]).join("").toUpperCase();

  return <>
    <aside className="sidebar">
      <a className="brand" href="/"><span className="brand-mark">S</span><span>Sentinel<small>Safety intelligence</small></span></a>
      <nav>
        {(user.role === "safety_manager" || user.role === "system_admin") && <button className={`nav-item ${page === "monitor" ? "active" : ""}`} onClick={() => onNavigate("monitor")}><span>◉</span> Live monitor</button>}
        {(user.role === "safety_manager" || user.role === "system_admin") && <button className={`nav-item ${page === "events" ? "active" : ""}`} onClick={() => onNavigate("events")}><span>▤</span> Nhật ký vi phạm</button>}
        {user.role === "system_admin" && <button className={`nav-item ${page === "operations" ? "active" : ""}`} onClick={() => onNavigate("operations")}><span>⌁</span> Quan sát hệ thống</button>}
        {user.role !== "safety_manager" && <button className={`nav-item ${page === "area" ? "active" : ""}`} onClick={() => onNavigate("area")}><span>⌁</span> Dashboard</button>}
         {user.role === "system_admin" && <button className={`nav-item ${page === "admin" ? "active" : ""}`} onClick={() => onNavigate("admin")}><span>⚙</span> Quản trị hệ thống</button>}
         {user.role === "system_admin" && <button className={`nav-item ${page === "media-library" ? "active" : ""}`} onClick={() => onNavigate("media-library")}><span>▣</span> Thư viện media</button>}
      </nav>
      <div className="system-card">
        <div><span className="pulse" /> Hệ thống hoạt động</div>
        <p>Video và AI engine đã sẵn sàng.</p>
        <div className="system-meta"><span>Rule</span><strong>Zone + Machine + Shirt</strong></div>
        <div className="system-meta"><span>Model</span><strong>YOLO Person</strong></div>
      </div>
      <div className="profile">
        <div className="avatar">{initials}</div>
        <div><strong>{user.full_name}</strong><small>{user.role_label}</small></div>
        <button className="logout-button" aria-label="Đăng xuất" onClick={onLogout}>Đăng xuất</button>
      </div>
    </aside>
    <main>
      <header>
        <div><p className="eyebrow">TRUNG TÂM GIÁM SÁT</p><h1>{title}</h1></div>
      </header>
      {children}
    </main>
</>;
});

function cameraNumber(cameraId?: string): string { return cameraId?.replace("cam_", "") || ""; }
