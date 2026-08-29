import {afterEach, beforeEach, expect, it, vi} from "vitest";
import {loadMediaSource} from "./media-assets";

beforeEach(() => {
  sessionStorage.setItem("sentinel.auth.access_token", "test-token");
  vi.stubGlobal("fetch", vi.fn());
  vi.stubGlobal("URL", {...URL, createObjectURL: vi.fn(() => "blob:local-media")});
});

afterEach(() => {
  sessionStorage.clear();
  vi.unstubAllGlobals();
});

it("loads filesystem media directly without probing playback-url", async () => {
  vi.mocked(fetch).mockResolvedValue(new Response(new Blob(["media"]), {status: 200}));

  await expect(loadMediaSource("asset-1", "filesystem")).resolves.toEqual({url: "blob:local-media", revoke: true});

  expect(fetch).toHaveBeenCalledTimes(1);
  expect(vi.mocked(fetch).mock.calls[0][0]).toContain("/media-assets/asset-1/content");
});

it("keeps presigned playback for s3 media", async () => {
  vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({url: "https://bucket.example/video?signed=1"}), {
    status: 200,
    headers: {"Content-Type": "application/json"},
  }));

  await expect(loadMediaSource("asset-2", "s3")).resolves.toEqual({url: "https://bucket.example/video?signed=1", revoke: false});

  expect(fetch).toHaveBeenCalledTimes(1);
  expect(vi.mocked(fetch).mock.calls[0][0]).toContain("/media-assets/asset-2/playback-url");
});
