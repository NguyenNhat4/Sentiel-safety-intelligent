import {act, render, screen} from "@testing-library/react";
import {afterEach, beforeEach, describe, expect, it, vi} from "vitest";

const hlsInstances: Array<{attachMedia: ReturnType<typeof vi.fn>; loadSource: ReturnType<typeof vi.fn>; destroy: ReturnType<typeof vi.fn>; on: ReturnType<typeof vi.fn>}> = [];
const hlsConfigs: Array<{xhrSetup?: (xhr: XMLHttpRequest) => void}> = [];

vi.mock("hls.js", () => {
  class MockHls {
    static isSupported() { return true; }
    static Events = {MANIFEST_PARSED: "manifestParsed", ERROR: "error"};
    static ErrorTypes = {NETWORK_ERROR: "networkError", MEDIA_ERROR: "mediaError"};
    attachMedia = vi.fn();
    loadSource = vi.fn();
    destroy = vi.fn();
    on = vi.fn();
    startLoad = vi.fn();
    recoverMediaError = vi.fn();
    constructor(config: {xhrSetup?: (xhr: XMLHttpRequest) => void}) { hlsInstances.push(this); hlsConfigs.push(config); }
  }
  return {default: MockHls};
});

import {HlsVideo} from "./HlsVideo";

describe("HlsVideo", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    hlsInstances.length = 0;
    hlsConfigs.length = 0;
    vi.spyOn(HTMLMediaElement.prototype, "canPlayType").mockReturnValue("");
    vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
    vi.spyOn(HTMLMediaElement.prototype, "pause").mockImplementation(() => undefined);
    vi.spyOn(HTMLMediaElement.prototype, "load").mockImplementation(() => undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("uses native HLS when the browser supports it and clears the source on unmount", () => {
    vi.mocked(HTMLMediaElement.prototype.canPlayType).mockReturnValue("probably");
    const {unmount} = render(<HlsVideo src="http://media/cameras/cam_1/index.m3u8" label="cam_1" />);
    const video = screen.getByLabelText("cam_1") as HTMLVideoElement;

    expect(video.src).toContain("/cameras/cam_1/index.m3u8");
    expect(hlsInstances).toHaveLength(0);
    unmount();
    expect(HTMLMediaElement.prototype.pause).toHaveBeenCalled();
    expect(video.getAttribute("src")).toBeNull();
    expect(HTMLMediaElement.prototype.load).toHaveBeenCalled();
  });

  it("uses hls.js on MSE browsers and destroys it on source change", () => {
    const {rerender} = render(<HlsVideo src="http://media/cameras/cam_1/index.m3u8" label="cam_1" />);
    expect(hlsInstances[0].loadSource).toHaveBeenCalledWith("http://media/cameras/cam_1/index.m3u8");

    rerender(<HlsVideo src="http://media/cameras/cam_2/index.m3u8" label="cam_1" />);

    expect(hlsInstances[0].destroy).toHaveBeenCalledOnce();
    expect(hlsInstances[1].loadSource).toHaveBeenCalledWith("http://media/cameras/cam_2/index.m3u8");
  });

  it("adds the short-lived HLS bearer token to every hls.js request", () => {
    render(<HlsVideo src="http://media/hls/cameras/cam_1/index.m3u8" accessToken="hls-token" label="cam_1" />);
    const xhr = {setRequestHeader: vi.fn()} as unknown as XMLHttpRequest;

    hlsConfigs[0].xhrSetup?.(xhr);

    expect(xhr.setRequestHeader).toHaveBeenCalledWith("Authorization", "Bearer hls-token");
  });

  it("disconnects while hidden and reconnects when visible", () => {
    Object.defineProperty(document, "visibilityState", {configurable: true, value: "visible"});
    render(<HlsVideo src="http://media/cameras/cam_1/index.m3u8" label="cam_1" hiddenGraceMs={1000} />);

    Object.defineProperty(document, "visibilityState", {configurable: true, value: "hidden"});
    document.dispatchEvent(new Event("visibilitychange"));
    act(() => vi.advanceTimersByTime(1000));
    expect(hlsInstances[0].destroy).toHaveBeenCalledOnce();

    Object.defineProperty(document, "visibilityState", {configurable: true, value: "visible"});
    act(() => document.dispatchEvent(new Event("visibilitychange")));
    expect(hlsInstances).toHaveLength(2);
  });
});
