import {apiUrl} from "./config";
import type {OperationalMetricsSummary} from "../types";
import {fetchQuery, peekQuery, revalidateQuery} from "./query-cache";

const TTL_MS = 15_000;

export function getCachedOperationalMetrics(windowMinutes: number): OperationalMetricsSummary | undefined {
  return peekQuery(metricsKey(windowMinutes));
}

export async function loadOperationalMetrics(windowMinutes: number, options: {forceRefresh?: boolean} = {}): Promise<OperationalMetricsSummary> {
  const key = metricsKey(windowMinutes);
  const loader = async () => {
    const response = await fetch(apiUrl(`/operational-metrics?window_minutes=${windowMinutes}`));
    if (!response.ok) throw new Error(`Không thể tải metrics vận hành (HTTP ${response.status})`);
    return response.json() as Promise<OperationalMetricsSummary>;
  };
  return options.forceRefresh ? revalidateQuery(key, loader) : fetchQuery(key, loader, TTL_MS);
}

function metricsKey(windowMinutes: number): string {
  return `operational-metrics:${windowMinutes}`;
}
