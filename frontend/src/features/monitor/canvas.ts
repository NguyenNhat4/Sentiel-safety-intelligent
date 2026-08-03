import type {PersonDetection, ZonePoint} from "../../types";

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

export function drawOverlay(
  canvas: HTMLCanvasElement,
  points: ZonePoint[],
  people: PersonDetection[],
  selectedPoint: number | null
): void {
  const context = canvas.getContext("2d");
  if (!context) return;
  context.clearRect(0, 0, canvas.width, canvas.height);
  drawZone(context, canvas, points, selectedPoint);
  people.forEach(person => drawPerson(context, person));
}

function drawZone(
  context: CanvasRenderingContext2D,
  canvas: HTMLCanvasElement,
  points: ZonePoint[],
  selectedPoint: number | null
): void {
  if (!points.length) return;
  context.beginPath();
  points.forEach((point, index) => {
    const x = point.x * canvas.width;
    const y = point.y * canvas.height;
    if (index === 0) context.moveTo(x, y); else context.lineTo(x, y);
  });
  if (points.length === 4) context.closePath();
  context.fillStyle = "rgba(247, 215, 77, .20)";
  context.strokeStyle = "#f4cc2f";
  context.lineWidth = 3;
  if (points.length === 4) context.fill();
  context.stroke();
  points.forEach((point, index) => drawZonePoint(context, canvas, point, index, selectedPoint));
}

function drawZonePoint(
  context: CanvasRenderingContext2D,
  canvas: HTMLCanvasElement,
  point: ZonePoint,
  index: number,
  selectedPoint: number | null
): void {
  const x = point.x * canvas.width;
  const y = point.y * canvas.height;
  context.beginPath();
  context.arc(x, y, 7, 0, Math.PI * 2);
  context.fillStyle = "#f4cc2f";
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

function drawPerson(context: CanvasRenderingContext2D, person: PersonDetection): void {
  const [x1, y1, x2, y2] = person.bbox;
  context.strokeStyle = person.inside_zone ? "#ff4940" : "#68e29a";
  context.lineWidth = 4;
  context.strokeRect(x1, y1, x2 - x1, y2 - y1);
  context.fillStyle = context.strokeStyle;
  context.font = "bold 16px Manrope";
  context.fillText(person.safety_shirt ? "PERSON · SHIRT" : "PERSON · NO SHIRT", x1, Math.max(18, y1 - 7));
  if (!person.foot_point) return;
  const [footX, footY] = person.foot_point;
  context.beginPath();
  context.arc(footX, footY, 7, 0, Math.PI * 2);
  context.fillStyle = person.inside_zone ? "#ff4940" : "#68e29a";
  context.fill();
  context.strokeStyle = "#fff";
  context.lineWidth = 2;
  context.stroke();
}
