import {apiUrl} from "./config";
import type {OperationalMetricsSummary} from "../types";

export async function loadOperationalMetrics(windowMinutes: number): Promise<OperationalMetricsSummary> {
  const response = await fetch(apiUrl(`/operational-metrics?window_minutes=${windowMinutes}`));
  if (!response.ok) throw new Error(`Không thể tải metrics vận hành (HTTP ${response.status})`);
  return response.json() as Promise<OperationalMetricsSummary>;
}
