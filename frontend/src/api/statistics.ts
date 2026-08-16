import type {StatisticsSummary} from "../types";
import {apiUrl} from "./config";
import {getAccessToken} from "./auth";

export async function loadStatisticsSummary(): Promise<StatisticsSummary> {
  const token = getAccessToken();
  const response = await fetch(apiUrl("/statistics/summary"), {
    headers: token ? {Authorization: `Bearer ${token}`} : {},
  });
  if (!response.ok) throw new Error(`Không thể tải thống kê khu vực (HTTP ${response.status})`);
  return response.json() as Promise<StatisticsSummary>;
}
