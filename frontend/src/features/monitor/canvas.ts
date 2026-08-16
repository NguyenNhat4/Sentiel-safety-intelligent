import type {ModelDetection, MonitoringZone, PersonDetection, PpeRequirementUpdate, ZonePoint} from "../../types";

type PpeBadgeTone = "present" | "missing" | "unknown";

interface PpeBadge {
  label: string;
  tone: PpeBadgeTone;
}

const DISPLAYED_PPE_CLASS_NAMES = new Set(["hat", "vest"]);

/**
 * Returns whether a hat/vest model detection belongs in operator-facing PPE displays.
 * Person boxes are rendered from the typed people collection to avoid duplicates.
 */
export function isDisplayedPpeDetection(className: string): boolean {
  return DISPLAYED_PPE_CLASS_NAMES.has(className.toLowerCase().trim());
}

export function normalizedPointerPosition(
  clientX: number,
  clientY: number,
  rect: Pick<DOMRect, "left" | "top" | "width" | "height">
): ZonePoint {
  return {
    x: Math.max(0, Math.min(1, (clientX - rect.left) / rect.width)),
    y: Math.max(0, Math.min(1, (clientY - rect.top) / rect.height))
  };
}

export function findPointAt(
  points: ZonePoint[],
  position: ZonePoint,
  size: Pick<DOMRect, "width" | "height">
): number | null {
  const index = points.findIndex(point => {
    const dx = (point.x - position.x) * size.width;
    const dy = (point.y - position.y) * size.height;
    return Math.hypot(dx, dy) <= 18;
  });
  return index === -1 ? null : index;
}

export function getDetectionColor(className: string, personIndex?: number | null, insideZone?: boolean): string {
  const name = className.toLowerCase().trim();
  if (name === "person") {
    return insideZone ? "#ff4940" : "#22c55e";
  }
  switch (name) {
    case "hat":
      return "#f59e0b";
    case "vest":
      return "#ec4899";
    default:
      return personIndex !== null && personIndex !== undefined ? "#a855f7" : "#3b82f6";
  }
}

export function drawOverlay(
  canvas: HTMLCanvasElement,
  zones: MonitoringZone[],
  people: PersonDetection[],
  detections: ModelDetection[],
  selectedZoneId: string | null,
  selectedPoint: number | null,
  ppeRequirements: PpeRequirementUpdate
): void {
  const context = canvas.getContext("2d");
  if (!context) return;
  context.clearRect(0, 0, canvas.width, canvas.height);
  zones.forEach((zone, index) => drawZone(
    context,
    canvas,
    zone,
    index,
    zone.zone_id === selectedZoneId ? selectedPoint : null,
  ));
  people.forEach((person, index) => drawPerson(context, person, ppeRequirements, index));
  detections.filter(detection => isDisplayedPpeDetection(detection.class_name)).forEach(detection => drawDetection(context, detection));
}

export function detectionLabel(detection: ModelDetection): string {
  return `${detection.class_name.toUpperCase()} · ${Math.round(detection.confidence * 100)}%`;
}

function drawDetection(context: CanvasRenderingContext2D, detection: ModelDetection): void {
  const [x1, y1, x2, y2] = detection.bbox;
  const color = getDetectionColor(detection.class_name, detection.person_index);
  context.strokeStyle = color;
  context.lineWidth = 2;
  context.strokeRect(x1, y1, x2 - x1, y2 - y1);
  context.fillStyle = color;
  context.font = "bold 11px Manrope";
  context.fillText(detectionLabel(detection), x1, Math.max(13, y1 - 4));
}

function drawZone(
  context: CanvasRenderingContext2D,
  canvas: HTMLCanvasElement,
  zone: MonitoringZone,
  zoneIndex: number,
  selectedPoint: number | null
): void {
  const points = zone.points;
  if (!points.length) return;
  const colors = ["#f4cc2f", "#48bfe3", "#f28482", "#90be6d", "#c77dff", "#ff9f1c"];
  const color = colors[zoneIndex % colors.length];
  context.beginPath();
  points.forEach((point, index) => {
    const x = point.x * canvas.width;
    const y = point.y * canvas.height;
    if (index === 0) context.moveTo(x, y); else context.lineTo(x, y);
  });
  if (points.length === 4) context.closePath();
  context.fillStyle = `${color}33`;
  context.strokeStyle = color;
  context.lineWidth = 3;
  context.setLineDash(zone.machine_state === "running" ? [] : [9, 6]);
  context.globalAlpha = zone.enabled ? 1 : 0.45;
  if (points.length === 4) context.fill();
  context.stroke();
  points.forEach((point, index) => drawZonePoint(context, canvas, point, index, selectedPoint, color));
  const anchor = points[0];
  context.fillStyle = color;
  context.font = "bold 13px Manrope";
  context.fillText(zone.display_name, anchor.x * canvas.width, Math.max(15, anchor.y * canvas.height - 10));
  context.setLineDash([]);
  context.globalAlpha = 1;
}

function drawZonePoint(
  context: CanvasRenderingContext2D,
  canvas: HTMLCanvasElement,
  point: ZonePoint,
  index: number,
  selectedPoint: number | null,
  color: string,
): void {
  const x = point.x * canvas.width;
  const y = point.y * canvas.height;
  context.beginPath();
  context.arc(x, y, 7, 0, Math.PI * 2);
  context.fillStyle = color;
  context.fill();
  if (selectedPoint === index) {
    context.strokeStyle = "#fff";
    context.lineWidth = 3;
    context.stroke();
  }
  context.fillStyle = "#17231f";
  context.font = "bold 11px Manrope";
  context.fillText(String(index + 1), x - 3, y + 4);
}

export function requiredPpeBadges(
  person: PersonDetection,
  requirements: PpeRequirementUpdate,
): PpeBadge[] {
  const ppe = [
    ["hat_required", "hat", "MŨ"],
    ["vest_required", "vest", "ÁO"],
  ] as const;

  const badges: PpeBadge[] = [];
  for (const [requirement, item, label] of ppe) {
    if (!requirements[requirement]) continue;
    const status = person.ppe[item].status;
    if (status === "present") badges.push({label: `✓ ${label}`, tone: "present"});
    else if (status === "missing") badges.push({label: `✕ ${label}`, tone: "missing"});
    else badges.push({label: `? ${label}`, tone: "unknown"});
  }
  return badges;
}

function drawPerson(
  context: CanvasRenderingContext2D,
  person: PersonDetection,
  ppeRequirements: PpeRequirementUpdate,
  personIndex?: number,
): void {
  const [x1, y1, x2, y2] = person.bbox;
  const color = getDetectionColor("person", personIndex, person.inside_zone);
  context.strokeStyle = color;
  context.lineWidth = 3;
  context.strokeRect(x1, y1, x2 - x1, y2 - y1);
  const badges = requiredPpeBadges(person, ppeRequirements);
  drawPpeBadges(context, badges, x1, y1);
  context.fillStyle = color;
  context.font = "bold 16px Manrope";
  const personLabel = person.track_id === undefined
    ? `PERSON ${personIndex !== undefined ? `#${personIndex + 1}` : ""}`
    : `TRACK #${person.track_id}`;
  context.fillText(personLabel, x1, Math.max(16, y1 - 6));
  if (!person.foot_point) return;
  const [footX, footY] = person.foot_point;
  context.beginPath();
  context.arc(footX, footY, 6, 0, Math.PI * 2);
  context.fillStyle = color;
  context.fill();
  context.strokeStyle = "#fff";
  context.lineWidth = 2;
  context.stroke();
}

function drawPpeBadges(
  context: CanvasRenderingContext2D,
  badges: PpeBadge[],
  x: number,
  y: number,
): void {
  const colors: Record<PpeBadgeTone, {background: string; text: string}> = {
    present: {background: "#1e7057", text: "#ffffff"},
    missing: {background: "#db3d35", text: "#ffffff"},
    unknown: {background: "#59645f", text: "#ffffff"},
  };
  context.font = "bold 12px Manrope";
  badges.forEach((badge, index) => {
    const badgeY = Math.max(16, y - 28 - (badges.length - index - 1) * 20);
    const width = context.measureText(badge.label).width + 14;
    context.fillStyle = colors[badge.tone].background;
    context.fillRect(x, badgeY - 13, width, 17);
    context.fillStyle = colors[badge.tone].text;
    context.fillText(badge.label, x + 7, badgeY);
  });
}
