import type {StatisticsSummary} from "../types";
import {apiUrl} from "./config";

export async function loadStatisticsSummary(): Promise<StatisticsSummary> {
  const response = await fetch(apiUrl("/statistics/summary"));
  if (!response.ok) throw new Error(`Không thể tải thống kê khu vực (HTTP ${response.status})`);
  return response.json() as Promise<StatisticsSummary>;
}
