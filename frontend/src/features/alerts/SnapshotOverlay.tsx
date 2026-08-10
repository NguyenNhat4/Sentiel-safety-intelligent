import {useState} from "react";
import type {ModelDetection, PersonDetection} from "../../types";
import {getDetectionColor} from "../monitor/canvas";

interface SnapshotOverlayProps {
  snapshot: string;
  people?: PersonDetection[];
  detections?: ModelDetection[];
}

export function SnapshotOverlay({snapshot, people = [], detections = []}: SnapshotOverlayProps) {
  const [imageSize, setImageSize] = useState<{width: number; height: number} | null>(null);

  return (
    <div className="snapshot-overlay" data-testid="snapshot-overlay">
      <img
        className="modal-snapshot"
        src={snapshot}
        alt="Khung hình vi phạm cần xác minh"
        onLoad={event => {
          const {naturalWidth: width, naturalHeight: height} = event.currentTarget;
          setImageSize(width > 0 && height > 0 ? {width, height} : null);
        }}
      />
      {imageSize && (
        <svg
          aria-label="Bounding box của khung hình review"
          className="snapshot-overlay-boxes"
          preserveAspectRatio="xMidYMid meet"
          viewBox={`0 0 ${imageSize.width} ${imageSize.height}`}
        >
          {people.map((person, index) => (
            <SnapshotBox
              key={`person-${index}`}
              bbox={person.bbox}
              color={getDetectionColor("person", index, person.inside_zone)}
              label={`PERSON #${index + 1} · ${Math.round(person.confidence * 100)}%`}
              thickness={3}
            />
          ))}
          {detections.filter(detection => detection.class_name.toLowerCase() !== "person").map((detection, index) => (
            <SnapshotBox
              key={`detection-${index}`}
              bbox={detection.bbox}
              color={getDetectionColor(detection.class_name, detection.person_index)}
              label={`${detection.class_name.toUpperCase()} · ${Math.round(detection.confidence * 100)}%`}
            />
          ))}
        </svg>
      )}
    </div>
  );
}

function SnapshotBox({
  bbox,
  color,
  label,
  thickness = 2,
}: {
  bbox: [number, number, number, number];
  color: string;
  label: string;
  thickness?: number;
}) {
  const [x1, y1, x2, y2] = bbox;
  return (
    <g data-testid="snapshot-box">
      <rect fill="none" height={y2 - y1} stroke={color} strokeWidth={thickness} width={x2 - x1} x={x1} y={y1} />
      <text fill={color} fontSize="11" fontWeight="700" x={x1} y={Math.max(12, y1 - 4)}>{label}</text>
    </g>
  );
}
