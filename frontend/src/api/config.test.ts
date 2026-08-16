import {afterEach, describe, expect, it} from "vitest";
import {apiUrl, assetUrl, inferenceWebSocketUrls, resetBackendForTests} from "./config";

describe("API configuration", () => {
  afterEach(() => resetBackendForTests());

  it("uses same-origin relative REST paths by default", () => {
    expect(apiUrl("/events")).toBe("/api/v1/events");
  });

  it("resolves snapshots and WebSocket development fallbacks", () => {
    expect(assetUrl("/snapshots/event.jpg")).toBe("http://localhost:3000/snapshots/event.jpg");
    expect(inferenceWebSocketUrls()).toEqual([
      "ws://localhost:3000/api/v1/ws/inference",
      "ws://localhost:8000/api/v1/ws/inference"
    ]);
  });
});
