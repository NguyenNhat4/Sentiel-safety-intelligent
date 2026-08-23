import {useEffect, useState} from "react";
import {loadMediaSource} from "../../api/media-assets";
import type {MediaType} from "../../types";

interface AuthenticatedMediaProps {
  assetId: string;
  mediaType: MediaType;
  label: string;
  playing?: boolean;
  playbackKey?: string;
  onEnded?: () => void;
}

export function AuthenticatedMedia({assetId, mediaType, label, playing = false, playbackKey = "", onEnded}: AuthenticatedMediaProps) {
  const [source, setSource] = useState("");
  const [error, setError] = useState("");

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

  if (error) return <div className="stream-empty-state" role="alert"><strong>Không thể tải media</strong><span>{error}</span></div>;
  if (!source) return <div className="stream-empty-state" role="status"><strong>Đang tải media</strong></div>;
  if (mediaType === "image") return <img src={source} alt={label} />;
  return <video key={playbackKey} src={source} aria-label={label} muted autoPlay={playing} playsInline onEnded={onEnded} />;
}
