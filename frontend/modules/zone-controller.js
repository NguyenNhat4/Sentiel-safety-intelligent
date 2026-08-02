import {dom} from "./dom.js";
import {
  drawOverlay,
  findPointAt,
  normalizedPointerPosition,
  positionDeleteButton
} from "./overlay-renderer.js";
import {state} from "./state.js";
import {setZoneEditing, updateZoneHint} from "./ui.js";

export function initializeZoneController({stopRealtimeInference, stopPreviewPlayback}) {
  dom.zoneButton.addEventListener("click", () => {
    if (!dom.video.paused) stopPreviewPlayback();
    setZoneEditing(!state.selectingZone);
    updateZoneHint();
  });

  dom.resetZoneButton.addEventListener("click", () => {
    stopRealtimeInference();
    state.zonePoints = [];
    state.selectedPoint = null;
    dom.deletePointButton.hidden = true;
    setZoneEditing(true);
    dom.flowStatus.textContent = "Chờ cấu hình vùng";
    updateZoneHint();
    drawOverlay();
  });

  dom.overlay.addEventListener("pointerdown", event => {
    if (!state.selectingZone || !dom.video.videoWidth || !dom.video.paused) return;
    const position = normalizedPointerPosition(event);
    const hit = findPointAt(position);
    if (hit !== null) {
      state.selectedPoint = hit;
      state.draggingPoint = hit;
      dom.overlay.setPointerCapture?.(event.pointerId);
    } else if (state.zonePoints.length < 4) {
      state.zonePoints.push(position);
      state.selectedPoint = state.zonePoints.length - 1;
    } else {
      state.selectedPoint = null;
    }
    syncZoneState();
  });

  dom.overlay.addEventListener("pointermove", event => {
    if (state.draggingPoint === null) return;
    state.zonePoints[state.draggingPoint] = normalizedPointerPosition(event);
    syncZoneState();
  });

  dom.overlay.addEventListener("pointerup", event => {
    if (state.draggingPoint !== null) dom.overlay.releasePointerCapture?.(event.pointerId);
    state.draggingPoint = null;
  });

  dom.deletePointButton.addEventListener("click", event => {
    event.stopPropagation();
    if (state.selectedPoint === null) return;
    state.zonePoints.splice(state.selectedPoint, 1);
    state.selectedPoint = null;
    dom.deletePointButton.hidden = true;
    setZoneEditing(true);
    syncZoneState();
  });
}

function syncZoneState() {
  dom.flowStatus.textContent = state.zonePoints.length === 4
    ? "Sẵn sàng inference realtime · nhấn Phát video"
    : "Chờ đủ 4 điểm";
  updateZoneHint();
  drawOverlay();
  positionDeleteButton();
}
