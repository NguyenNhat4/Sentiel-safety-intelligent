import {useState} from "react";
import type {MonitoringZone} from "../../types";

interface SnapshotZoneOverlayProps {
  snapshot: string;
  zones?: MonitoringZone[];
  alt: string;
}

export function SnapshotZoneOverlay({snapshot, zones = [], alt}: SnapshotZoneOverlayProps) {
  const [imageSize, setImageSize] = useState<{width: number; height: number} | null>(null);
  const visibleZones = zones.filter(zone => zone.enabled && zone.points.length === 4);

  return <div className="snapshot-zone-overlay" data-testid="snapshot-zone-overlay">
    <img className="modal-snapshot" src={snapshot} alt={alt} onLoad={event => {
      const {naturalWidth: width, naturalHeight: height} = event.currentTarget;
      setImageSize(width > 0 && height > 0 ? {width, height} : null);
    }} />
    {imageSize && visibleZones.length > 0 && <svg aria-label="Vùng cấm của khung hình" className="snapshot-zone-boxes" preserveAspectRatio="xMidYMid meet" viewBox={`0 0 ${imageSize.width} ${imageSize.height}`}>
      {visibleZones.map(zone => <g key={zone.zone_id} data-testid="snapshot-zone">
        <polygon aria-label={`Vùng ${zone.display_name}`} fill="#f4cc2f33" points={zone.points.map(point => `${point.x * imageSize.width},${point.y * imageSize.height}`).join(" ")} stroke="#f4cc2f" strokeWidth={Math.max(2, imageSize.width * 0.004)} />
        <text fill="#f4cc2f" fontSize={Math.max(12, imageSize.width * 0.018)} fontWeight="700" x={zone.points[0].x * imageSize.width} y={Math.max(16, zone.points[0].y * imageSize.height - 6)}>{zone.display_name}</text>
      </g>)}
    </svg>}
  </div>;
}
