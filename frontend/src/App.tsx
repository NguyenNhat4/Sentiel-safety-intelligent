import {useState} from "react";
import {AppShell} from "./components/AppShell";
import type {Page} from "./components/AppShell";
import {EventLogPage} from "./features/events/EventLogPage";
import {MonitorPage} from "./features/monitor/MonitorPage";
import {OperationalMetricsPage} from "./features/operational-metrics/OperationalMetricsPage";

export default function App() {
  const [page, setPage] = useState<Page>("monitor");
  return (
    <AppShell page={page} onNavigate={setPage}>
      {page === "monitor" && <MonitorPage />}
      <EventLogPage active={page === "events"} />
      <OperationalMetricsPage active={page === "operations"} />
    </AppShell>
  );
}
