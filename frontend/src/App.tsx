import {useState} from "react";
import {AppShell} from "./components/AppShell";
import type {Page} from "./components/AppShell";
import {LoginPage} from "./features/auth/LoginPage";
import {EventLogPage} from "./features/events/EventLogPage";
import {MonitorPage} from "./features/monitor/MonitorPage";
import type {AuthenticatedUser} from "./types";

export default function App() {
  const [user, setUser] = useState<AuthenticatedUser>();
  const [page, setPage] = useState<Page>("monitor");

  if (!user) return <LoginPage onAuthenticated={setUser} />;

  return (
    <AppShell page={page} onNavigate={setPage}>
      {page === "monitor" && <MonitorPage />}
      <EventLogPage active={page === "events"} />
    </AppShell>
  );
}
