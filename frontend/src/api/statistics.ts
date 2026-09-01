import type {StatisticsSummary} from "../types";
import {apiUrl} from "./config";
import {getAccessToken} from "./auth";
import {fetchQuery, peekQuery, revalidateQuery} from "./query-cache";

const SUMMARY_KEY = "statistics:summary";
const TTL_MS = 30_000;

export function getCachedStatisticsSummary(): StatisticsSummary | undefined {
  return peekQuery(SUMMARY_KEY);
}

export async function loadStatisticsSummary(options: {forceRefresh?: boolean} = {}): Promise<StatisticsSummary> {
  const loader = async () => {
    const token = getAccessToken();
    const response = await fetch(apiUrl("/statistics/summary"), {
      headers: token ? {Authorization: `Bearer ${token}`} : {},
    });
    if (!response.ok) throw new Error(`Không thể tải thống kê khu vực (HTTP ${response.status})`);
    return response.json() as Promise<StatisticsSummary>;
  };
  return options.forceRefresh ? revalidateQuery(SUMMARY_KEY, loader) : fetchQuery(SUMMARY_KEY, loader, TTL_MS);
}
