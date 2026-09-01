import {memo, type ReactNode, useState} from "react";
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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const title = page === "monitor" ? "Live Monitor" : page === "events" ? "Nhật ký vi phạm" : page === "operations" ? "Quan sát hệ thống" : page === "area" ? "Dashboard khu vực" : page === "media-library" ? "Thư viện media" : page === "camera-config" ? `Cấu hình Camera ${cameraNumber(selectedCameraId)}` : "Quản trị hệ thống";
  const initials = user.full_name.split(" ").filter(Boolean).slice(-2).map(part => part[0]).join("").toUpperCase();

  return <>
    <aside className={`sidebar ${sidebarCollapsed ? "collapsed" : ""}`}>
      <a className="brand" href="/"><span className="brand-mark">S</span><span>Sentinel<small>Safety intelligence</small></span></a>
      <button type="button" className="sidebar-toggle" aria-label={sidebarCollapsed ? "Mở rộng thanh điều hướng" : "Thu gọn thanh điều hướng"} aria-expanded={!sidebarCollapsed} onClick={() => setSidebarCollapsed(value => !value)}>{sidebarCollapsed ? "›" : "‹"}</button>
      <nav>
        {(user.role === "safety_manager" || user.role === "system_admin") && <button className={`nav-item ${page === "monitor" ? "active" : ""}`} onClick={() => onNavigate("monitor")}><NavIcon name="monitor" /> Live monitor</button>}
        {(user.role === "safety_manager" || user.role === "system_admin") && <button className={`nav-item ${page === "events" ? "active" : ""}`} onClick={() => onNavigate("events")}><NavIcon name="events" /> Nhật ký vi phạm</button>}
        {user.role === "system_admin" && <button className={`nav-item ${page === "operations" ? "active" : ""}`} onClick={() => onNavigate("operations")}><NavIcon name="operations" /> Quan sát hệ thống</button>}
        {user.role !== "safety_manager" && <button className={`nav-item ${page === "area" ? "active" : ""}`} onClick={() => onNavigate("area")}><NavIcon name="dashboard" /> Dashboard</button>}
         {user.role === "system_admin" && <button className={`nav-item ${page === "admin" ? "active" : ""}`} onClick={() => onNavigate("admin")}><NavIcon name="admin" /> Quản trị hệ thống</button>}
         {user.role === "system_admin" && <button className={`nav-item ${page === "media-library" ? "active" : ""}`} onClick={() => onNavigate("media-library")}><NavIcon name="media" /> Thư viện media</button>}
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
    <main className={`${sidebarCollapsed ? "sidebar-collapsed" : ""} ${page === "monitor" ? "monitor-main" : ""} ${page === "camera-config" ? "camera-config-main" : ""}`}>
      <header>
        <div><p className="eyebrow">TRUNG TÂM GIÁM SÁT</p><h1>{title}</h1></div>
        {page === "camera-config" && <button type="button" className="secondary-btn camera-config-header-back" onClick={() => onNavigate("monitor")}>← Quay lại</button>}
      </header>
      {children}
    </main>
</>;
});

function cameraNumber(cameraId?: string): string { return cameraId?.replace("cam_", "") || ""; }

type NavIconName = "monitor" | "events" | "operations" | "dashboard" | "admin" | "media";

function NavIcon({name}: {name: NavIconName}) {
  const paths: Record<NavIconName, ReactNode> = {
    monitor: <><rect x="3" y="4" width="18" height="14" rx="2"/><path d="M8 22h8M12 18v4M10 9l5 3-5 3z"/></>,
    events: <><path d="M9 5h6M9 3h6v4H9z"/><rect x="5" y="5" width="14" height="16" rx="2"/><path d="M9 12h6M9 16h4"/></>,
    operations: <><path d="M3 12h4l2-5 4 10 2-5h6"/><circle cx="12" cy="12" r="9"/></>,
    dashboard: <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
    admin: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H3v-4h.2a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6 1.7 1.7 0 0 0 10 3V3h4v.2a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1z"/></>,
    media: <><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9" r="1.5"/><path d="m3 16 5-5 4 4 2-2 7 7"/></>
  };

  return <svg className="nav-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">{paths[name]}</svg>;
}
