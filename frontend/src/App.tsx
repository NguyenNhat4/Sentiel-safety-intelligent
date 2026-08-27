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

  const handleBackToMonitor = useCallback(() => {
    setPage("monitor");
  }, []);

  if (checkingSession) return null;
  if (!user) return <LoginPage onAuthenticated={handleAuthenticated} />;
  if (user.must_change_password) return <ForcedPasswordChangePage user={user} onChanged={handleLogout} />;

  return (
    <AppShell page={page} onNavigate={setPage} user={user} selectedCameraId={selectedCameraId} onLogout={() => void handleLogout()}>
      {user.role === "safety_manager" && <MonitorPage active={page === "monitor"} role={user.role} onConfigure={handleConfigureCamera} />}
      {user.role === "safety_manager" && selectedCameraId && page === "camera-config" && <CameraConfigurationPage active={page === "camera-config"} cameraId={selectedCameraId} showTitle={false} onBack={handleBackToMonitor} onSaved={handleBackToMonitor} />}
      {user.role === "safety_manager" && page === "events" && <EventLogPage active />}
      {user.role === "system_admin" && page === "operations" && <OperationalMetricsPage active />}
      {user.role !== "safety_manager" && page === "area" && <AreaManagerPage active />}
      {user.role === "system_admin" && page === "media-library" && <MediaLibraryPage active />}
      {user.role === "system_admin" && page === "admin" && <AdminUserPage active currentUser={user} onLogout={() => void handleLogout()} />}
    </AppShell>
  );
}
