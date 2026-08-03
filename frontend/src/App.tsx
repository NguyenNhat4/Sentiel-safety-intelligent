import {useState} from "react";
import {AppShell} from "./components/AppShell";
import type {Page} from "./components/AppShell";
import {EventLogPage} from "./features/events/EventLogPage";
import {MonitorPage} from "./features/monitor/MonitorPage";

export default function App() {
  const [page, setPage] = useState<Page>("monitor");
  return (
    <AppShell page={page} onNavigate={setPage}>
      {page === "monitor" && <MonitorPage />}
      <EventLogPage active={page === "events"} />
    </AppShell>
  );
}
