const SNAPSHOT_PRELOAD_TIMEOUT_MS = 5000;

export function preloadSnapshot(source: string, timeoutMs = SNAPSHOT_PRELOAD_TIMEOUT_MS): Promise<boolean> {
  return new Promise(resolve => {
    const image = new Image();
    let settled = false;
    const finish = (loaded: boolean) => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timer);
      image.onload = null;
      image.onerror = null;
      resolve(loaded);
    };
    const timer = window.setTimeout(() => finish(false), timeoutMs);
    image.onload = () => finish(true);
    image.onerror = () => finish(false);
    image.src = source;
    if (image.complete && image.naturalWidth > 0) finish(true);
  });
}
