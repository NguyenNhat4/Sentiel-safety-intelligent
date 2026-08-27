import {useState} from "react";
import type {ModelDetection, MonitoringZone, PersonDetection} from "../../types";
import {getDetectionColor, isDisplayedPpeDetection} from "../monitor/canvas";

interface SnapshotOverlayProps {
  snapshot: string;
  people?: PersonDetection[];
  detections?: ModelDetection[];
  zones?: MonitoringZone[];
}

export function SnapshotOverlay({snapshot, people = [], detections = [], zones = []}: SnapshotOverlayProps) {
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
          {zones.filter(zone => zone.enabled && zone.points.length === 4).map(zone => (
            <SnapshotZone key={zone.zone_id} zone={zone} imageSize={imageSize} />
          ))}
          {people.map((person, index) => (
            <SnapshotBox
              key={`person-${index}`}
              bbox={person.bbox}
              color={getDetectionColor("person", index, person.inside_zone)}
              label={`PERSON #${index + 1} · ${Math.round(person.confidence * 100)}%`}
              thickness={3}
            />
          ))}
          {detections.filter(detection => isDisplayedPpeDetection(detection.class_name)).map((detection, index) => (
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

function SnapshotZone({zone, imageSize}: {zone: MonitoringZone; imageSize: {width: number; height: number}}) {
  return (
    <g data-testid="snapshot-zone">
      <polygon
        aria-label={`Vùng ${zone.display_name}`}
        fill="#f4cc2f33"
        points={zone.points.map(point => `${point.x * imageSize.width},${point.y * imageSize.height}`).join(" ")}
        stroke="#f4cc2f"
        strokeWidth={Math.max(2, imageSize.width * 0.004)}
      />
      <text fill="#f4cc2f" fontSize={Math.max(12, imageSize.width * 0.018)} fontWeight="700" x={zone.points[0].x * imageSize.width} y={Math.max(16, zone.points[0].y * imageSize.height - 6)}>
        {zone.display_name}
      </text>
    </g>
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
  const labelTop = Math.max(0, y1 - 15);
  const labelWidth = Math.max(36, label.length * 6.4 + 10);

  return (
    <g data-testid="snapshot-box">
      <rect fill="none" height={y2 - y1} stroke={color} strokeWidth={thickness} width={x2 - x1} x={x1} y={y1} />
      <g data-testid="snapshot-box-label">
        <rect fill={color} height="15" rx="2" width={labelWidth} x={x1} y={labelTop} />
        <text fill="#ffffff" fontSize="11" fontWeight="700" x={x1 + 5} y={labelTop + 11}>{label}</text>
      </g>
    </g>
  );
}
