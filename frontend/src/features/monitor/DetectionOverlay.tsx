import type {CameraInferenceResult} from "../../types";

export function DetectionOverlay({result}: {result?: CameraInferenceResult}) {
  if (!result || result.frame_width <= 0 || result.frame_height <= 0) return null;
  return <svg
    className="camera-detection-overlay"
    viewBox={`0 0 ${result.frame_width} ${result.frame_height}`}
    preserveAspectRatio="xMidYMid meet"
    aria-label={`Detection overlay frame ${result.frame_id}`}
  >
    {(result.detections ?? []).map((detection, index) => {
      const [x1, y1, x2, y2] = detection.bbox;
      return <g key={`${detection.class_name}-${index}`}>
        <rect x={x1} y={y1} width={Math.max(0, x2 - x1)} height={Math.max(0, y2 - y1)} />
        <text x={x1} y={Math.max(14, y1 - 5)}>{detection.class_name} {Math.round(detection.confidence * 100)}%</text>
      </g>;
    })}
  </svg>;
}
