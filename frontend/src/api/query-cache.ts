interface QueryEntry<T> {
  data?: T;
  hasData: boolean;
  updatedAt: number;
  ttlMs: number;
  invalidated: boolean;
  generation: number;
  promise?: Promise<T>;
}

const queries = new Map<string, QueryEntry<unknown>>();

export function peekQuery<T>(key: string): T | undefined {
  const entry = queries.get(key) as QueryEntry<T> | undefined;
  return entry?.hasData ? entry.data : undefined;
}

export function fetchQuery<T>(key: string, loader: () => Promise<T>, ttlMs: number): Promise<T> {
  const entry = getEntry<T>(key, ttlMs);
  const fresh = entry.hasData && !entry.invalidated && Date.now() - entry.updatedAt < entry.ttlMs;
  if (fresh) return Promise.resolve(entry.data as T);
  return runQuery(key, entry, loader, ttlMs);
}

export function revalidateQuery<T>(key: string, loader: () => Promise<T>): Promise<T> {
  const entry = getEntry<T>(key, 0);
  return runQuery(key, entry, loader, entry.ttlMs);
}

export function setQueryData<T>(key: string, value: T, ttlMs?: number): void {
  const entry = getEntry<T>(key, ttlMs ?? 0);
  entry.generation += 1;
  entry.data = value;
  entry.hasData = true;
  entry.updatedAt = Date.now();
  entry.invalidated = false;
  entry.promise = undefined;
  if (ttlMs !== undefined) entry.ttlMs = ttlMs;
}

export function invalidateQueries(prefix: string): void {
  for (const [key, rawEntry] of queries) {
    if (!key.startsWith(prefix)) continue;
    const entry = rawEntry as QueryEntry<unknown>;
    entry.generation += 1;
    entry.invalidated = true;
    entry.updatedAt = 0;
    entry.promise = undefined;
  }
}

export function clearQueryCache(): void {
  queries.clear();
}

function getEntry<T>(key: string, ttlMs: number): QueryEntry<T> {
  const current = queries.get(key) as QueryEntry<T> | undefined;
  if (current) {
    if (ttlMs > 0) current.ttlMs = ttlMs;
    return current;
  }
  const entry: QueryEntry<T> = {
    hasData: false,
    updatedAt: 0,
    ttlMs,
    invalidated: false,
    generation: 0,
  };
  queries.set(key, entry as QueryEntry<unknown>);
  return entry;
}

function runQuery<T>(key: string, entry: QueryEntry<T>, loader: () => Promise<T>, ttlMs: number): Promise<T> {
  if (entry.promise) return entry.promise;
  const generation = entry.generation;
  const promise = loader().then(data => {
    const current = queries.get(key);
    if (current === entry && entry.generation === generation && entry.promise === promise) {
      entry.data = data;
      entry.hasData = true;
      entry.updatedAt = Date.now();
      entry.ttlMs = ttlMs;
      entry.invalidated = false;
    }
    return data;
  }).finally(() => {
    if (queries.get(key) === entry && entry.promise === promise) entry.promise = undefined;
  });
  entry.promise = promise;
  return promise;
}
