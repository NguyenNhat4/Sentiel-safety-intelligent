import {useEffect, useRef, useState} from "react";
import {loadMediaSource} from "../../api/media-assets";
import type {MediaType} from "../../types";

interface AuthenticatedMediaProps {
  assetId: string;
  mediaType: MediaType;
  label: string;
  playing?: boolean;
  playbackKey?: string;
  onPlaybackTime?: (time: number) => void;
  onEnded?: () => void;
}

type VideoFrameElement = HTMLVideoElement & {
  requestVideoFrameCallback?: (callback: (now: number, metadata: {mediaTime: number}) => void) => number;
  cancelVideoFrameCallback?: (handle: number) => void;
};

export function AuthenticatedMedia({assetId, mediaType, label, playing = false, playbackKey = "", onPlaybackTime, onEnded}: AuthenticatedMediaProps) {
  const [source, setSource] = useState("");
  const [error, setError] = useState("");
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const playbackTimeCallbackRef = useRef(onPlaybackTime);
  playbackTimeCallbackRef.current = onPlaybackTime;

  useEffect(() => {
    const controller = new AbortController();
    let revocableUrl = "";
    setSource("");
    setError("");
    void loadMediaSource(assetId, controller.signal)
      .then(mediaSource => {
        if (controller.signal.aborted) return;
        if (mediaSource.revoke) revocableUrl = mediaSource.url;
        setSource(mediaSource.url);
      })
      .catch(reason => {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Không thể tải media.");
      });
    return () => {
      controller.abort();
      if (revocableUrl) URL.revokeObjectURL(revocableUrl);
    };
  }, [assetId, playbackKey]);

  useEffect(() => {
    if (!source || mediaType !== "video") return;
    const video = videoRef.current as VideoFrameElement | null;
    if (!video) return;
    let cancelled = false;
    let frameCallbackHandle: number | undefined;

    const notify = (time: number) => playbackTimeCallbackRef.current?.(time);
    if (video.requestVideoFrameCallback) {
      const onVideoFrame = (_now: number, metadata: {mediaTime: number}) => {
        if (cancelled) return;
        notify(metadata.mediaTime);
        frameCallbackHandle = video.requestVideoFrameCallback?.(onVideoFrame);
      };
      frameCallbackHandle = video.requestVideoFrameCallback(onVideoFrame);
      return () => {
        cancelled = true;
        if (frameCallbackHandle !== undefined) video.cancelVideoFrameCallback?.(frameCallbackHandle);
      };
    }

    const onTimeUpdate = () => notify(video.currentTime);
    video.addEventListener("loadedmetadata", onTimeUpdate);
    video.addEventListener("seeked", onTimeUpdate);
    video.addEventListener("timeupdate", onTimeUpdate);
    return () => {
      video.removeEventListener("loadedmetadata", onTimeUpdate);
      video.removeEventListener("seeked", onTimeUpdate);
      video.removeEventListener("timeupdate", onTimeUpdate);
    };
  }, [mediaType, playbackKey, source]);

  if (error) return <div className="stream-empty-state" role="alert"><strong>Không thể tải media</strong><span>{error}</span></div>;
  if (!source) return <div className="stream-empty-state" role="status"><strong>Đang tải media</strong></div>;
  if (mediaType === "image") return <img src={source} alt={label} />;
  return <video ref={videoRef} key={playbackKey} src={source} aria-label={label} muted autoPlay={playing} playsInline onEnded={onEnded} />;
}
