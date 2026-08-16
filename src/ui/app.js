const pages = {
  monitor: "Live Monitor",
  events: "Nhật ký vi phạm",
  dashboard: "Dashboard an toàn",
  logjson: "Log JSON"
};

function openPage(id) {
  document.querySelectorAll(".page").forEach(page => page.classList.toggle("active", page.id === id));
  document.querySelectorAll(".nav-item").forEach(item => item.classList.toggle("active", item.dataset.page === id));
  document.getElementById("page-title").textContent = pages[id];
}

document.querySelectorAll(".nav-item").forEach(item => {
  item.addEventListener("click", () => openPage(item.dataset.page));
});
document.querySelector("[data-go-events]").addEventListener("click", () => openPage("events"));

const machineSwitch = document.getElementById("machine-switch");
const machineLabel = document.getElementById("machine-label");
machineSwitch.addEventListener("click", () => {
  const isOn = machineSwitch.classList.toggle("on");
  machineLabel.textContent = isOn ? "Đang hoạt động" : "Đã dừng";
  showToast(isOn ? "Machine A đã chuyển sang trạng thái ON." : "Machine A đã chuyển sang trạng thái OFF.");
});

const toast = document.getElementById("toast");
let toastTimeout;
function showToast(message) {
  document.getElementById("toast-message").textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => toast.classList.remove("show"), 3200);
}

document.getElementById("ack-btn").addEventListener("click", () => {
  showToast("Sự kiện đã được xác nhận và lưu vào nhật ký.");
});
document.getElementById("false-btn").addEventListener("click", () => {
  showToast("Sự kiện đã được đánh dấu báo sai để đánh giá lại.");
});

const sampleJson = {
  track_id: 3,
  person_bbox: [120, 80, 350, 520],
  foot_point: [235, 520],
  ppe: {
    safety_vest: "missing",
    confidence: 0.87
  },
  inside_danger_zone: true,
  machine_status: "running",
  violation: true,
  severity: "critical"
};

document.getElementById("copy-json-btn").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(JSON.stringify(sampleJson, null, 2));
    showToast("Đã sao chép JSON vào clipboard.");
  } catch {
    showToast("Không thể truy cập clipboard trong trình duyệt này.");
  }
});

const mediaInput = document.getElementById("media-input");
const uploadButton = document.getElementById("upload-btn");
const inferenceButton = document.getElementById("inference-btn");
const cameraScene = document.getElementById("camera-scene");
const uploadedImage = document.getElementById("uploaded-image");
const uploadedVideo = document.getElementById("uploaded-video");
let mediaType = null;
let mediaUrl = null;

uploadButton.addEventListener("click", () => mediaInput.click());
mediaInput.addEventListener("change", () => {
  const file = mediaInput.files[0];
  if (!file) return;
  if (mediaUrl) URL.revokeObjectURL(mediaUrl);
  mediaUrl = URL.createObjectURL(file);
  uploadedImage.classList.remove("active");
  uploadedVideo.classList.remove("active");
  uploadedVideo.pause();

  if (file.type.startsWith("video/")) {
    mediaType = "video";
    uploadedVideo.src = mediaUrl;
    uploadedVideo.currentTime = 0;
    uploadedVideo.classList.add("active");
    inferenceButton.textContent = "▶ Inference";
  } else if (file.type.startsWith("image/")) {
    mediaType = "image";
    uploadedImage.src = mediaUrl;
    uploadedImage.classList.add("active");
    inferenceButton.textContent = "▶ Inference";
  } else {
    showToast("Định dạng không được hỗ trợ. Vui lòng chọn ảnh hoặc video.");
    return;
  }
  cameraScene.classList.add("has-media");
  uploadButton.textContent = `✓ ${file.name.length > 18 ? `${file.name.slice(0, 15)}…` : file.name}`;
  showToast(`${mediaType === "video" ? "Video" : "Ảnh"} đã được tải vào khung Live.`);
});

inferenceButton.addEventListener("click", () => {
  if (mediaType !== "video") return;
  if (uploadedVideo.ended) uploadedVideo.currentTime = 0;
  uploadedVideo.play();
  inferenceButton.textContent = "● Đang inference";
  showToast("Đã bắt đầu chạy video và inference mô phỏng.");
});
uploadedVideo.addEventListener("ended", () => {
  inferenceButton.textContent = "↻ Inference lại";
});

const zoneConfigButton = document.getElementById("zone-config-btn");
const zoneEditor = document.getElementById("zone-editor");
const zonePointsLayer = document.getElementById("zone-points");
const zonePolygon = document.getElementById("zone-polygon");
const zoneHint = document.getElementById("zone-hint");
let zonePoints = [];
let selectedPoint = null;
let draggingPoint = null;
let deleteButton = null;

zoneConfigButton.addEventListener("click", () => {
  const active = zoneEditor.classList.toggle("active");
  zoneConfigButton.classList.toggle("zone-config-active", active);
  zoneConfigButton.textContent = active ? "✓ Xong cấu hình" : "⌗ Cấu hình vùng";
  selectedPoint = null;
  renderZone();
});

function localPosition(event) {
  const rect = zoneEditor.getBoundingClientRect();
  return {
    x: Math.max(0, Math.min(rect.width, event.clientX - rect.left)),
    y: Math.max(0, Math.min(rect.height, event.clientY - rect.top))
  };
}

zoneEditor.addEventListener("pointerdown", event => {
  if (event.target !== zoneEditor && event.target.tagName !== "svg") return;
  if (zonePoints.length >= 4) {
    selectedPoint = null;
    renderZone();
    return;
  }
  zonePoints.push(localPosition(event));
  selectedPoint = zonePoints.length - 1;
  renderZone();
});

window.addEventListener("pointermove", event => {
  if (draggingPoint === null) return;
  zonePoints[draggingPoint] = localPosition(event);
  renderZone();
});
window.addEventListener("pointerup", () => {
  draggingPoint = null;
});

function removePoint(index) {
  zonePoints.splice(index, 1);
  selectedPoint = null;
  renderZone();
}

function renderZone() {
  zonePointsLayer.innerHTML = "";
  if (deleteButton) deleteButton.remove();
  deleteButton = null;
  zonePolygon.setAttribute("points", zonePoints.length === 4
    ? zonePoints.map(point => `${point.x},${point.y}`).join(" ")
    : "");
  zoneEditor.classList.toggle("zone-configured", zonePoints.length === 4);
  zoneHint.textContent = zonePoints.length === 4
    ? "Vùng nguy hiểm đã được thiết lập · Kéo điểm để điều chỉnh"
    : `Chọn 4 điểm để tạo vùng nguy hiểm · ${zonePoints.length}/4`;

  zonePoints.forEach((point, index) => {
    const button = document.createElement("button");
    button.className = `zone-point${selectedPoint === index ? " selected" : ""}`;
    button.style.left = `${point.x}px`;
    button.style.top = `${point.y}px`;
    button.title = `Điểm ${index + 1} — kéo để di chuyển`;
    button.addEventListener("pointerdown", event => {
      event.stopPropagation();
      draggingPoint = index;
      selectedPoint = index;
      button.setPointerCapture?.(event.pointerId);
      renderZone();
    });
    button.addEventListener("click", event => {
      event.stopPropagation();
      selectedPoint = index;
      renderZone();
    });
    zonePointsLayer.appendChild(button);
  });

  if (selectedPoint !== null && zonePoints[selectedPoint]) {
    const point = zonePoints[selectedPoint];
    deleteButton = document.createElement("button");
    deleteButton.className = "delete-point";
    deleteButton.textContent = "×";
    deleteButton.title = "Xóa điểm";
    deleteButton.style.left = `${point.x}px`;
    deleteButton.style.top = `${point.y}px`;
    deleteButton.addEventListener("pointerdown", event => event.stopPropagation());
    deleteButton.addEventListener("click", event => {
      event.stopPropagation();
      removePoint(selectedPoint);
    });
    zoneEditor.appendChild(deleteButton);
  }
}

let seconds = 18;
setInterval(() => {
  seconds += 1;
  document.getElementById("timer").textContent = `00:${String(seconds).padStart(2, "0")}`;
  const now = new Date();
  document.getElementById("clock").textContent = now.toLocaleTimeString("vi-VN", { hour12: false });
  document.getElementById("video-time").textContent =
    `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")} ${now.toLocaleTimeString("vi-VN", { hour12: false })}.${String(now.getMilliseconds()).padStart(3, "0")}`;
}, 1000);
