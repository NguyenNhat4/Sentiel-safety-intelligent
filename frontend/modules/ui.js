import {dom} from "./dom.js";
import {state} from "./state.js";

export function updateRule(id, yes, text, badge) {
  const element = document.getElementById(id);
  element.className = `rule ${yes ? "yes" : "no"}`;
  element.querySelector("strong").textContent = text;
  element.querySelector("b").textContent = badge;
}

export function updateZoneHint() {
  dom.zoneHint.textContent = state.zonePoints.length === 4
    ? "Vùng đã sẵn sàng · Kéo điểm để điều chỉnh"
    : `Chọn 4 điểm · ${state.zonePoints.length}/4`;
}

export function resetAlert() {
  state.reviewStartedAt = null;
  dom.alertPanel.classList.remove("violation");
  dom.alertTitle.textContent = "Chưa có vi phạm";
  dom.severity.textContent = "NORMAL";
  dom.alertSummary.textContent = "Người trong vùng nguy hiểm phải mặc áo bảo hộ khi máy đang hoạt động.";
  dom.reviewMessage.textContent = "Khung hình vi phạm sẽ hiện tại đây";
  dom.eventStatus.textContent = "CHƯA CÓ SỰ KIỆN ĐƯỢC LƯU";
  dom.confidenceLabel.textContent = "READY";
  dom.confidenceBar.style.width = "12%";
  dom.timer.textContent = "00:00";
}

export function showToast(message) {
  dom.toastMessage.textContent = message;
  dom.toast.classList.add("show");
  setTimeout(() => dom.toast.classList.remove("show"), 3000);
}

export function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
}

export function setZoneEditing(active) {
  state.selectingZone = active;
  dom.zoneButton.textContent = active ? "✓ Xong cấu hình" : "⌗ Cấu hình vùng";
  dom.zoneButton.classList.toggle("zone-config-active", active);
}

export function startClock() {
  setInterval(() => {
    document.getElementById("clock").textContent = new Date().toLocaleTimeString("vi-VN", {hour12: false});
    if (!state.reviewStartedAt) return;
    const seconds = Math.floor((Date.now() - state.reviewStartedAt) / 1000);
    dom.timer.textContent = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
  }, 1000);
}
