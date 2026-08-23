import {useEffect, useState} from "react";
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

  useEffect(() => {
    void getCurrentUser().then(currentUser => {
      if (currentUser) handleAuthenticated(currentUser);
    }).catch(() => undefined).finally(() => setCheckingSession(false));
  }, []);

  function handleAuthenticated(authenticatedUser: AuthenticatedUser) {
    setUser(authenticatedUser);
    setPage(authenticatedUser.role === "area_manager" ? "area" : authenticatedUser.role === "system_admin" ? "media-library" : "monitor");
  }
  async function handleLogout() {
    try {
      await logout();
    } finally {
      setUser(undefined);
      setPage("monitor");
    }
  }

  if (checkingSession) return null;
  if (!user) return <LoginPage onAuthenticated={handleAuthenticated} />;
  if (user.must_change_password) return <ForcedPasswordChangePage user={user} onChanged={handleLogout} />;

  return (
    <AppShell page={page} onNavigate={setPage} user={user} onLogout={() => void handleLogout()}>
      {page === "monitor" && user.role === "safety_manager" && <MonitorPage role={user.role} onConfigure={cameraId => { setSelectedCameraId(cameraId); setPage("camera-config"); }} />}
      {page === "camera-config" && user.role === "safety_manager" && selectedCameraId && <CameraConfigurationPage cameraId={selectedCameraId} onBack={() => setPage("monitor")} onSaved={() => setPage("monitor")} />}
      {page === "media-library" && user.role === "system_admin" && <MediaLibraryPage />}
      <EventLogPage active={page === "events"} />
      <OperationalMetricsPage active={page === "operations"} />
      {page === "area" && user.role !== "safety_manager" && <AreaManagerPage />}
      {page === "admin" && user.role === "system_admin" && <AdminUserPage currentUser={user} onLogout={() => void handleLogout()} />}
    </AppShell>
  );
}
