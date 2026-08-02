import {dom} from "./dom.js";
import {state} from "./state.js";

export function drawOverlay() {
  const context = dom.overlay.getContext("2d");
  context.clearRect(0, 0, dom.overlay.width, dom.overlay.height);
  drawZone(context);
  state.latestPeople.forEach(person => drawPerson(context, person));
}

function drawZone(context) {
  if (!state.zonePoints.length) return;
  context.beginPath();
  state.zonePoints.forEach((point, index) => {
    const x = point.x * dom.overlay.width;
    const y = point.y * dom.overlay.height;
    if (index === 0) context.moveTo(x, y); else context.lineTo(x, y);
  });
  if (state.zonePoints.length === 4) context.closePath();
  context.fillStyle = "rgba(247, 215, 77, .20)";
  context.strokeStyle = "#f4cc2f";
  context.lineWidth = 3;
  if (state.zonePoints.length === 4) context.fill();
  context.stroke();
  state.zonePoints.forEach((point, index) => drawZonePoint(context, point, index));
}

function drawZonePoint(context, point, index) {
  context.beginPath();
  context.arc(point.x * dom.overlay.width, point.y * dom.overlay.height, 7, 0, Math.PI * 2);
  context.fillStyle = "#f4cc2f";
  context.fill();
  if (state.selectedPoint === index) {
    context.strokeStyle = "#fff";
    context.lineWidth = 3;
    context.stroke();
  }
  context.fillStyle = "#17231f";
  context.font = "bold 11px Manrope";
  context.fillText(String(index + 1), point.x * dom.overlay.width - 3, point.y * dom.overlay.height + 4);
}

function drawPerson(context, person) {
  const [x1, y1, x2, y2] = person.bbox;
  context.strokeStyle = person.inside_zone ? "#ff4940" : "#68e29a";
  context.lineWidth = 4;
  context.strokeRect(x1, y1, x2 - x1, y2 - y1);
  context.fillStyle = context.strokeStyle;
  context.font = "bold 16px Manrope";
  context.fillText(person.safety_shirt ? "PERSON · SHIRT" : "PERSON · NO SHIRT", x1, Math.max(18, y1 - 7));
  if (person.foot_point?.length !== 2) return;
  const [footX, footY] = person.foot_point;
  context.beginPath();
  context.arc(footX, footY, 7, 0, Math.PI * 2);
  context.fillStyle = person.inside_zone ? "#ff4940" : "#68e29a";
  context.fill();
  context.strokeStyle = "#ffffff";
  context.lineWidth = 2;
  context.stroke();
}

export function normalizedPointerPosition(event) {
  const rect = dom.overlay.getBoundingClientRect();
  return {
    x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
    y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height))
  };
}

export function findPointAt(position) {
  const rect = dom.overlay.getBoundingClientRect();
  const index = state.zonePoints.findIndex(point => {
    const dx = (point.x - position.x) * rect.width;
    const dy = (point.y - position.y) * rect.height;
    return Math.hypot(dx, dy) <= 18;
  });
  return index === -1 ? null : index;
}

export function positionDeleteButton() {
  const point = state.zonePoints[state.selectedPoint];
  if (state.selectedPoint === null || !point) {
    dom.deletePointButton.hidden = true;
    return;
  }
  dom.deletePointButton.style.left = `${point.x * 100}%`;
  dom.deletePointButton.style.top = `${point.y * 100}%`;
  dom.deletePointButton.hidden = false;
}
