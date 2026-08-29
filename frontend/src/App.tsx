import {useCallback, useEffect, useState} from "react";
import {AppShell} from "./components/AppShell";
import type {Page} from "./components/AppShell";
import {LoginPage} from "./features/auth/LoginPage";
import {AdminUserPage} from "./features/auth/AdminUserPage";
import {ForcedPasswordChangePage} from "./features/auth/ForcedPasswordChangePage";
import {AreaManagerPage} from "./features/area/AreaManagerPage";
import {EventLogPage} from "./features/events/EventLogPage";
import {MonitorPage} from "./features/monitor/MonitorPage";
import {OperationalMetricsPage} from "./features/operational-metrics/OperationalMetricsPage";
import {CameraConfigurationPage} from "./features/camera-config/CameraConfigurationPage";
import {MediaLibraryPage} from "./features/media/MediaLibraryPage";
import type {AuthenticatedUser} from "./types";
import {getCurrentUser, logout} from "./api/auth";

export default function App() {
  const [user, setUser] = useState<AuthenticatedUser>();
  const [page, setPage] = useState<Page>("monitor");
  const [selectedCameraId, setSelectedCameraId] = useState("");
  const [checkingSession, setCheckingSession] = useState(true);
  const [cameraConfigDirty, setCameraConfigDirty] = useState(false);
  const [pendingNavigation, setPendingNavigation] = useState<Page | "logout">();

  const handleAuthenticated = useCallback((authenticatedUser: AuthenticatedUser) => {
    setUser(authenticatedUser);
    setPage(authenticatedUser.role === "area_manager" ? "area" : authenticatedUser.role === "system_admin" ? "media-library" : "monitor");
  }, []);

  useEffect(() => {
    void getCurrentUser().then(currentUser => {
      if (currentUser) handleAuthenticated(currentUser);
    }).catch(() => undefined).finally(() => setCheckingSession(false));
  }, [handleAuthenticated]);

  const handleLogout = useCallback(async () => {
    try {
      await logout();
    } finally {
      setUser(undefined);
      setPage("monitor");
    }
  }, []);

  const handleConfigureCamera = useCallback((cameraId: string) => {
    setSelectedCameraId(cameraId);
    setPage("camera-config");
  }, []);

  const handleNavigate = useCallback((nextPage: Page) => {
    if (page === "camera-config" && cameraConfigDirty && nextPage !== "camera-config") {
      setPendingNavigation(nextPage);
      return;
    }
    setCameraConfigDirty(false);
    setPage(nextPage);
  }, [cameraConfigDirty, page]);

  const handleBackToMonitor = useCallback(() => handleNavigate("monitor"), [handleNavigate]);

  const requestLogout = useCallback(() => {
    if (page === "camera-config" && cameraConfigDirty) {
      setPendingNavigation("logout");
      return;
    }
    void handleLogout();
  }, [cameraConfigDirty, handleLogout, page]);

  const discardChanges = useCallback(() => {
    const destination = pendingNavigation;
    setPendingNavigation(undefined);
    setCameraConfigDirty(false);
    if (destination === "logout") void handleLogout();
    else if (destination) setPage(destination);
  }, [handleLogout, pendingNavigation]);

  if (checkingSession) return null;
  if (!user) return <LoginPage onAuthenticated={handleAuthenticated} />;
  if (user.must_change_password) return <ForcedPasswordChangePage user={user} onChanged={handleLogout} />;

  return (
    <AppShell page={page} onNavigate={handleNavigate} user={user} selectedCameraId={selectedCameraId} onLogout={requestLogout}>
      {(user.role === "safety_manager" || user.role === "system_admin") && <MonitorPage active={page === "monitor"} role={user.role} onConfigure={handleConfigureCamera} />}
      {(user.role === "safety_manager" || user.role === "system_admin") && selectedCameraId && page === "camera-config" && <CameraConfigurationPage active={page === "camera-config"} cameraId={selectedCameraId} showTitle={false} onBack={handleBackToMonitor} onSaved={handleBackToMonitor} onDirtyChange={setCameraConfigDirty} />}
      {(user.role === "safety_manager" || user.role === "system_admin") && page === "events" && <EventLogPage active />}
      {user.role === "system_admin" && page === "operations" && <OperationalMetricsPage active />}
      {user.role !== "safety_manager" && page === "area" && <AreaManagerPage active />}
      {user.role === "system_admin" && page === "media-library" && <MediaLibraryPage active />}
      {user.role === "system_admin" && page === "admin" && <AdminUserPage active currentUser={user} onLogout={() => void handleLogout()} />}
      {pendingNavigation && <div className="unsaved-dialog-backdrop" role="presentation"><section className="unsaved-dialog" role="alertdialog" aria-modal="true" aria-labelledby="unsaved-dialog-title" aria-describedby="unsaved-dialog-description"><div className="unsaved-dialog-icon" aria-hidden="true">!</div><div className="unsaved-dialog-copy"><h2 id="unsaved-dialog-title">Bạn chưa lưu thay đổi</h2><p id="unsaved-dialog-description">Các thay đổi trong cấu hình Camera sẽ bị mất nếu bạn rời khỏi trang này.</p></div><div className="unsaved-dialog-actions"><button type="button" className="secondary-btn" autoFocus onClick={() => setPendingNavigation(undefined)}>Tiếp tục chỉnh sửa</button><button type="button" className="discard-changes-btn" onClick={discardChanges}>Bỏ thay đổi</button></div></section></div>}
    </AppShell>
  );
}
