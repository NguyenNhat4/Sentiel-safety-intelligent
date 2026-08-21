import Hls from "hls.js";
import {useCallback, useEffect, useRef, useState} from "react";
import type {MutableRefObject} from "react";

export type HlsVideoState = "connecting" | "live" | "retrying" | "paused_hidden" | "failed";

interface HlsVideoProps {
  src: string;
  label: string;
  accessToken?: string;
  hiddenGraceMs?: number;
  onStateChange?: (state: HlsVideoState) => void;
}

const MAX_RETRY_DELAY_MS = 30_000;

export function HlsVideo({src, label, accessToken = "", hiddenGraceMs = 5_000, onStateChange}: HlsVideoProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);
  const retryTimer = useRef<number | null>(null);
  const hiddenTimer = useRef<number | null>(null);
  const retryAttempt = useRef(0);
  const [generation, setGeneration] = useState(0);

  const updateState = useCallback((state: HlsVideoState) => onStateChange?.(state), [onStateChange]);
  const clearTimer = (timer: MutableRefObject<number | null>) => {
    if (timer.current !== null) window.clearTimeout(timer.current);
    timer.current = null;
  };

  const dispose = useCallback(() => {
    clearTimer(retryTimer);
    hlsRef.current?.destroy();
    hlsRef.current = null;
    const video = videoRef.current;
    if (video) {
      video.pause();
      video.removeAttribute("src");
      video.load();
    }
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || document.visibilityState === "hidden") return;
    let active = true;
    updateState(retryAttempt.current ? "retrying" : "connecting");

    const live = () => {
      if (!active) return;
      retryAttempt.current = 0;
      updateState("live");
      void video.play().catch(() => updateState("failed"));
    };
    const scheduleRetry = () => {
      if (!active) return;
      dispose();
      updateState("retrying");
      const base = Math.min(1000 * 2 ** retryAttempt.current++, MAX_RETRY_DELAY_MS);
      const jitter = base * (0.8 + Math.random() * 0.4);
      retryTimer.current = window.setTimeout(() => setGeneration(value => value + 1), jitter);
    };

    if (!accessToken && video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = src;
      video.addEventListener("loadeddata", live, {once: true});
      video.addEventListener("error", scheduleRetry, {once: true});
    } else if (Hls.isSupported()) {
      const hls = new Hls({
        maxBufferLength: 12,
        maxMaxBufferLength: 20,
        backBufferLength: 6,
        xhrSetup: xhr => xhr.setRequestHeader("Authorization", `Bearer ${accessToken}`),
      });
      hlsRef.current = hls;
      hls.attachMedia(video);
      hls.loadSource(src);
      hls.on(Hls.Events.MANIFEST_PARSED, live);
      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) scheduleRetry();
      });
    } else {
      updateState("failed");
    }

    return () => {
      active = false;
      video.removeEventListener("loadeddata", live);
      video.removeEventListener("error", scheduleRetry);
      clearTimer(retryTimer);
      hlsRef.current?.destroy();
      hlsRef.current = null;
      video.pause();
      video.removeAttribute("src");
      video.load();
    };
  }, [accessToken, dispose, generation, src, updateState]);

  useEffect(() => {
    const visibilityChanged = () => {
      clearTimer(hiddenTimer);
      if (document.visibilityState === "hidden") {
        hiddenTimer.current = window.setTimeout(() => {
          dispose();
          updateState("paused_hidden");
        }, hiddenGraceMs);
      } else {
        retryAttempt.current = 0;
        setGeneration(value => value + 1);
      }
    };
    document.addEventListener("visibilitychange", visibilityChanged);
    return () => {
      document.removeEventListener("visibilitychange", visibilityChanged);
      clearTimer(hiddenTimer);
    };
  }, [dispose, hiddenGraceMs, updateState]);

  return <video ref={videoRef} aria-label={label} muted autoPlay playsInline />;
}
