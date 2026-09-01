import {afterEach, describe, expect, it, vi} from "vitest";
import {clearQueryCache, fetchQuery, invalidateQueries, peekQuery, revalidateQuery, setQueryData} from "./query-cache";

afterEach(() => {
  clearQueryCache();
  vi.useRealTimers();
});

describe("query cache", () => {
  it("stores a miss and serves the fresh value without another request", async () => {
    const loader = vi.fn(async () => ["camera-1"]);
    await expect(fetchQuery("cameras:list", loader, 60_000)).resolves.toEqual(["camera-1"]);
    await expect(fetchQuery("cameras:list", loader, 60_000)).resolves.toEqual(["camera-1"]);
    expect(loader).toHaveBeenCalledTimes(1);
    expect(peekQuery("cameras:list")).toEqual(["camera-1"]);
  });

  it("keeps stale data visible while fetching a replacement", async () => {
    vi.useFakeTimers();
    setQueryData("events:list", ["old"], 10);
    vi.advanceTimersByTime(11);
    let resolve!: (value: string[]) => void;
    const refresh = fetchQuery("events:list", () => new Promise(result => { resolve = result; }), 10);
    expect(peekQuery("events:list")).toEqual(["old"]);
    resolve(["new"]);
    await expect(refresh).resolves.toEqual(["new"]);
    expect(peekQuery("events:list")).toEqual(["new"]);
  });

  it("deduplicates concurrent fetch and forced revalidation calls", async () => {
    let resolve!: (value: number) => void;
    const loader = vi.fn(() => new Promise<number>(result => { resolve = result; }));
    const first = fetchQuery("sessions:list", loader, 3_000);
    const second = revalidateQuery("sessions:list", loader);
    expect(loader).toHaveBeenCalledTimes(1);
    resolve(2);
    await expect(Promise.all([first, second])).resolves.toEqual([2, 2]);
  });

  it("invalidates only matching prefixes", async () => {
    const cameraLoader = vi.fn(async () => "fresh-camera");
    const mediaLoader = vi.fn(async () => "fresh-media");
    setQueryData("camera:one", "cached-camera", 60_000);
    setQueryData("media:list", "cached-media", 60_000);
    invalidateQueries("camera:");
    await expect(fetchQuery("camera:one", cameraLoader, 60_000)).resolves.toBe("fresh-camera");
    await expect(fetchQuery("media:list", mediaLoader, 60_000)).resolves.toBe("cached-media");
    expect(cameraLoader).toHaveBeenCalledOnce();
    expect(mediaLoader).not.toHaveBeenCalled();
  });

  it("does not let an older request overwrite mutation data", async () => {
    let resolve!: (value: string) => void;
    const pending = fetchQuery("camera:one", () => new Promise(result => { resolve = result; }), 60_000);
    setQueryData("camera:one", "saved", 60_000);
    resolve("stale");
    await expect(pending).resolves.toBe("stale");
    expect(peekQuery("camera:one")).toBe("saved");
  });

  it("clears every cached value", () => {
    setQueryData("camera:list", [1]);
    setQueryData("events:list", [2]);
    clearQueryCache();
    expect(peekQuery("camera:list")).toBeUndefined();
    expect(peekQuery("events:list")).toBeUndefined();
  });
});
