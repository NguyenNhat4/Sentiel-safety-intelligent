import {useState} from "react";
import {AppShell} from "./components/AppShell";
import type {Page} from "./components/AppShell";
import {LoginPage} from "./features/auth/LoginPage";
import {EventLogPage} from "./features/events/EventLogPage";
import {MonitorPage} from "./features/monitor/MonitorPage";
import {StreamingPage} from "./features/streaming/StreamingPage";
import type {AuthenticatedUser} from "./types";
import {logout} from "./api/auth";

export default function App() {
  const [user, setUser] = useState<AuthenticatedUser>();
  const [page, setPage] = useState<Page>("monitor");
  async function handleLogout() {
    try {
      await logout();
    } finally {
      setUser(undefined);
      setPage("monitor");
    }
  }

  if (!user) return <LoginPage onAuthenticated={setUser} />;

  return (
    <AppShell page={page} onNavigate={setPage} user={user} onLogout={() => void handleLogout()}>
      {page === "monitor" && <MonitorPage />}
      {page === "streaming" && <StreamingPage onOpenMonitor={() => setPage("monitor")} />}
      <EventLogPage active={page === "events"} />
    </AppShell>
  );
}
