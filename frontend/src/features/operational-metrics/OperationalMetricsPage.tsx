import {memo, useCallback, useEffect, useState} from "react";
import {loadOperationalMetrics} from "../../api/operational-metrics";
import type {OperationalMetricsSummary} from "../../types";

interface OperationalMetricsPageProps {active: boolean}

const metricsCache = new Map<number, OperationalMetricsSummary>();

export const OperationalMetricsPage = memo(function OperationalMetricsPage({active}: OperationalMetricsPageProps) {
  const [windowMinutes, setWindowMinutes] = useState(60);
  const [metrics, setMetrics] = useState<OperationalMetricsSummary | undefined>(() => metricsCache.get(60));
  const [status, setStatus] = useState(() => metricsCache.get(60) ? "" : "Đang chờ dữ liệu metrics");

  const load = useCallback(async () => {
    const cached = metricsCache.get(windowMinutes);
    if (!cached) {
      setStatus("Đang tải metrics vận hành...");
    }
    try {
      const summary = await loadOperationalMetrics(windowMinutes);
      metricsCache.set(windowMinutes, summary);
      setMetrics(summary);
      setStatus("");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Không thể tải metrics vận hành");
    }
  }, [windowMinutes]);

  useEffect(() => { if (active) void load(); }, [active, load]);

  function handleWindowChange(nextMinutes: number) {
    setWindowMinutes(nextMinutes);
    const cached = metricsCache.get(nextMinutes);
    if (cached) {
      setMetrics(cached);
      setStatus("");
    } else {
      setMetrics(undefined);
      setStatus("Đang tải metrics vận hành...");
    }
  }
  const requests = metrics?.requests.reduce((total, item) => total + item.count, 0) ?? 0;
  const errors = metrics ? Object.values(metrics.errors_by_kind).reduce((total, count) => total + count, 0) : 0;

  return <section className={`page operations-page ${active ? "active" : ""}`}>
    <div className="operations-toolbar">
      <div><p className="eyebrow">Aggregate từ JSONL đã xoay file; không hiển thị raw log hoặc dữ liệu video.</p></div>
      <div className="operations-actions">
        <label>Khoảng thời gian<select value={windowMinutes} onChange={event => handleWindowChange(Number(event.target.value))}>
          <option value={5}>5 phút</option><option value={60}>1 giờ</option><option value={360}>6 giờ</option><option value={1440}>24 giờ</option>
        </select></label>
        <button className="secondary-btn" onClick={() => void load()}>↻ Làm mới</button>
      </div>
    </div>
    {status ? <div className="operations-status" role="status">{status}</div> : <>
      <div className="operations-kpis">
        <MetricCard label="Request" value={`${requests} requests`} detail={`${metrics?.records_scanned ?? 0} records đã quét`} />
        <MetricCard label="P95 latency" value={formatMs(maxP95(metrics))} detail="Theo từng route/method/status" />
        <MetricCard label="Lỗi" value={`${errors} lỗi`} detail="Phân loại theo error kind" />
        <MetricCard label="Inference" value={`${sum(metrics?.inference_outcomes)} kết quả`} detail="Normal, violate hoặc failure" />
      </div>
      {metrics?.partial && <p className="operations-warning" role="alert">Dữ liệu chưa đầy đủ: {metrics.partial_reasons.join(", ")}.</p>}
      <section className="operations-table-card"><h3>Request & latency</h3><table><thead><tr><th>Method</th><th>Route</th><th>Status</th><th>Count</th><th>P50</th><th>P95</th></tr></thead><tbody>
        {metrics?.requests.length ? metrics.requests.map(item => <tr key={`${item.method}-${item.route}-${item.status_class}`}><td>{item.method}</td><td>{item.route}</td><td>{item.status_class}</td><td>{item.count}</td><td>{formatMs(item.latency.p50_ms)}</td><td>{formatMs(item.latency.p95_ms)}</td></tr>) : <tr><td colSpan={6}>Chưa có request trong khoảng thời gian này.</td></tr>}
      </tbody></table></section>
      <section className="operations-table-card"><h3>WebSocket connections & inference latency</h3><table><thead><tr><th>Route</th><th>Opened</th><th>Closed</th><th>Inference P50</th><th>Inference P95</th></tr></thead><tbody>
        {metrics?.websocket_connections.length ? metrics.websocket_connections.map(item => <tr key={item.route}><td>{item.route}</td><td>{item.opened}</td><td>{item.closed}</td><td>{formatMs(item.inference_latency.p50_ms)}</td><td>{formatMs(item.inference_latency.p95_ms)}</td></tr>) : <tr><td colSpan={5}>Chưa có WebSocket connection trong khoảng thời gian này.</td></tr>}
      </tbody></table></section>
      <InferenceLatencyChart samples={metrics?.inference_latency_samples ?? []} />
      <section className="operations-breakdown"><Breakdown title="Inference outcomes" values={metrics?.inference_outcomes ?? {}} /><Breakdown title="Errors" values={metrics?.errors_by_kind ?? {}} /></section>
    </>}
  </section>;
});

function MetricCard({label, value, detail}: {label: string; value: string; detail: string}) { return <article className="operations-kpi"><small>{label}</small><strong>{value}</strong><span>{detail}</span></article>; }
function Breakdown({title, values}: {title: string; values: Record<string, number>}) { const rows = Object.entries(values); return <section className="operations-table-card"><h3>{title}</h3>{rows.length ? <ul>{rows.map(([key, value]) => <li key={key}><span>{key}</span><strong>{value}</strong></li>)}</ul> : <p>Chưa có dữ liệu.</p>}</section>; }
function sum(values: Record<string, number> | undefined): number { return Object.values(values ?? {}).reduce((total, value) => total + value, 0); }
function maxP95(metrics: OperationalMetricsSummary | undefined): number | null { return Math.max(...(metrics?.requests.map(item => item.latency.p95_ms ?? 0) ?? [0])) || null; }
function formatMs(value: number | null): string { return value === null ? "—" : `${value.toFixed(1)} ms`; }

function InferenceLatencyChart({samples}: {samples: OperationalMetricsSummary["inference_latency_samples"]}) {
  if (!samples.length) return <section className="operations-table-card"><h3>Inference latency theo frame</h3><p>Chưa có inference completed trong khoảng thời gian này.</p></section>;
  const maximum = Math.max(...samples.map(sample => sample.duration_ms));
  const minimum = Math.min(...samples.map(sample => sample.duration_ms));
  const points = samples.map((sample, index) => `${samples.length === 1 ? 50 : 4 + index * 92 / (samples.length - 1)},${maximum === minimum ? 50 : 94 - (sample.duration_ms - minimum) * 88 / (maximum - minimum)}`).join(" ");
  return <section className="operations-table-card latency-frame-chart"><div className="chart-heading"><div><h3>Inference latency theo frame</h3><p>{samples.length} inference gần nhất · backend processing time</p></div><strong>{formatMs(maximum)}</strong></div><svg viewBox="0 0 100 100" role="img" aria-label="Biểu đồ inference latency theo frame" preserveAspectRatio="none"><line x1="4" y1="94" x2="96" y2="94" /><line x1="4" y1="6" x2="4" y2="94" /><polyline points={points} /></svg><div className="chart-axis"><span>{formatMs(minimum)}</span><span>{formatMs(maximum)}</span></div></section>;
}
