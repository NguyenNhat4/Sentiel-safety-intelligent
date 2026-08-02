let API = `${defaultBackendHttpOrigin()}/api/v1`;
const videoInput = document.getElementById("video-input");
const video = document.getElementById("video");
const videoPreview = document.getElementById("video-preview");
const overlay = document.getElementById("overlay");
const capture = document.getElementById("capture");
const stage = document.getElementById("media-stage");
const zoneButton = document.getElementById("zone-btn");
const playbackButton = document.getElementById("playback-btn");
const machineSwitch = document.getElementById("machine-switch");
const reviewActions = document.getElementById("review-actions");
const deletePointButton = document.getElementById("delete-point");

let videoUrl;
let zonePoints = [];
let selectingZone = false;
let running = false;
let requestPending = false;
let lastSampleTime = -1;
let latestPeople = [];
let pendingViolation = null;
let violationLatched = false;
let reviewStartedAt = null;
let previewReady = false;
let previewCandidateIndex = 0;
const previewCandidates = [0.05, 0.5, 1, 2, 3, 4, 5, 7, 10];
let selectedPoint = null;
let draggingPoint = null;
let inferenceSocket = null;
let socketConfigured = false;
let frameSequence = 0;
let lastHandledFrame = -1;

document.getElementById("upload-btn").addEventListener("click", () => videoInput.click());
document.getElementById("activity-action").addEventListener("click", () => videoInput.click());
videoInput.addEventListener("change", () => {
  const file = videoInput.files[0];
  if (!file) return;
  closeInferenceSocket();
  video.pause();
  if (videoUrl) URL.revokeObjectURL(videoUrl);
  videoUrl = URL.createObjectURL(file);
  video.src = videoUrl;
  video.load();
  videoPreview.hidden = true;
  previewReady = false;
  previewCandidateIndex = 0;
  document.getElementById("file-label").textContent = file.name;
  zonePoints = [];
  latestPeople = [];
  pendingViolation = null;
  violationLatched = false;
  reviewActions.hidden = true;
  playbackButton.disabled = true;
  playbackButton.textContent = "▶ Phát video";
  selectedPoint = null;
  draggingPoint = null;
  deletePointButton.hidden = true;
  document.getElementById("snapshot").classList.remove("visible");
  document.getElementById("flow-status").textContent = "Chờ cấu hình vùng";
  resetAlert();
  showToast("Video đã sẵn sàng. Hãy chọn 4 điểm cho vùng nguy hiểm.");
});

video.addEventListener("loadedmetadata", () => {
  overlay.width = video.videoWidth;
  overlay.height = video.videoHeight;
  capture.width = video.videoWidth;
  capture.height = video.videoHeight;
  stage.classList.add("ready");
  playbackButton.disabled = false;
  document.getElementById("empty-state").hidden = true;
  document.getElementById("video-meta").textContent = `${video.videoWidth} × ${video.videoHeight} · ${formatTime(video.duration)}`;
  selectingZone = true;
  zoneButton.textContent = "✓ Xong cấu hình";
  zoneButton.classList.add("zone-config-active");
  updateZoneHint();
  drawOverlay();
  seekPreviewCandidate();
});

video.addEventListener("seeked", () => {
  if (running || pendingViolation || previewReady) return;
  if (video.requestVideoFrameCallback) {
    video.requestVideoFrameCallback(evaluatePreviewCandidate);
  } else {
    setTimeout(evaluatePreviewCandidate, 30);
  }
});

zoneButton.addEventListener("click", () => {
  if (!video.paused) stopPreviewPlayback();
  selectingZone = !selectingZone;
  zoneButton.textContent = selectingZone ? "✓ Xong cấu hình" : "⌗ Chọn 4 điểm";
  zoneButton.classList.toggle("zone-config-active", selectingZone);
  updateZoneHint();
});

document.getElementById("reset-zone").addEventListener("click", () => {
  stopRealtimeInference();
  zonePoints = [];
  selectedPoint = null;
  deletePointButton.hidden = true;
  selectingZone = true;
  zoneButton.textContent = "✓ Xong cấu hình";
  zoneButton.classList.add("zone-config-active");
  document.getElementById("flow-status").textContent = "Chờ cấu hình vùng";
  updateZoneHint();
  drawOverlay();
});

overlay.addEventListener("pointerdown", event => {
  if (!selectingZone || !video.videoWidth || !video.paused) return;
  const position = normalizedPointerPosition(event);
  const hit = findPointAt(position);
  if (hit !== null) {
    selectedPoint = hit;
    draggingPoint = hit;
    overlay.setPointerCapture?.(event.pointerId);
  } else if (zonePoints.length < 4) {
    zonePoints.push(position);
    selectedPoint = zonePoints.length - 1;
  } else {
    selectedPoint = null;
  }
  syncZoneState();
});

overlay.addEventListener("pointermove", event => {
  if (draggingPoint === null) return;
  zonePoints[draggingPoint] = normalizedPointerPosition(event);
  syncZoneState();
});

overlay.addEventListener("pointerup", event => {
  if (draggingPoint !== null) overlay.releasePointerCapture?.(event.pointerId);
  draggingPoint = null;
});

deletePointButton.addEventListener("click", event => {
  event.stopPropagation();
  if (selectedPoint === null) return;
  zonePoints.splice(selectedPoint, 1);
  selectedPoint = null;
  deletePointButton.hidden = true;
  selectingZone = true;
  syncZoneState();
});

playbackButton.addEventListener("click", async () => {
  if (!video.src || pendingViolation) return;
  if (video.paused) {
    previewReady = true;
    selectingZone = false;
    zoneButton.textContent = "⌗ Cấu hình vùng";
    zoneButton.classList.remove("zone-config-active");
    videoPreview.hidden = true;
    deletePointButton.hidden = true;
    playbackButton.textContent = "■ Dừng video";
    running = zonePoints.length === 4;
    lastSampleTime = -1;
    frameSequence = 0;
    lastHandledFrame = -1;
    document.getElementById("flow-status").textContent = running
      ? "Đang inference realtime"
      : "Đang xem video · dừng để cấu hình đủ 4 điểm";
    document.getElementById("confidence-label").textContent = running ? "RUNNING" : "PREVIEW";
    document.getElementById("confidence-bar").style.width = running ? "70%" : "25%";
    if (video.ended) video.currentTime = 0;
    if (running) {
      document.getElementById("flow-status").textContent = "Đang kết nối inference";
      try {
        await connectInferenceSocket();
      } catch (error) {
        closeInferenceSocket();
        running = false;
        playbackButton.textContent = "▶ Phát video";
        document.getElementById("flow-status").textContent = "Không thể kết nối inference";
        showToast(error.message);
        return;
      }
      document.getElementById("flow-status").textContent = "Đang inference realtime";
    }
    await video.play();
    if (running) requestAnimationFrame(inferenceLoop);
  } else {
    stopPreviewPlayback();
  }
});

video.addEventListener("ended", () => {
  running = false;
  closeInferenceSocket();
  playbackButton.textContent = "↻ Phát lại";
  capturePausedFrame();
});

machineSwitch.addEventListener("click", () => {
  const on = machineSwitch.classList.toggle("on");
  document.getElementById("machine-label").textContent = on ? "Đang hoạt động" : "Đã dừng";
  updateRule("rule-machine", on, on ? "Machine A đang chạy" : "Machine A đã dừng", on ? "ON" : "OFF");
  sendInferenceConfiguration();
});

async function inferenceLoop() {
  if (!running) return;
  if (video.ended) {
    stopRealtimeInference();
    document.getElementById("flow-status").textContent = "Hoàn tất";
    showToast("Inference đã hoàn tất.");
    return;
  }
  if (!requestPending && video.currentTime - lastSampleTime >= 0.5) {
    lastSampleTime = video.currentTime;
    inferCurrentFrame();
  }
  if (running) requestAnimationFrame(inferenceLoop);
}

async function inferCurrentFrame() {
  if (
    zonePoints.length !== 4 ||
    !socketConfigured ||
    inferenceSocket?.readyState !== WebSocket.OPEN
  ) return;
  requestPending = true;
  const context = capture.getContext("2d");
  context.drawImage(video, 0, 0, capture.width, capture.height);
  const frameId = frameSequence++;
  const videoTime = video.currentTime;
  capture.toBlob(blob => {
    if (
      !blob ||
      !running ||
      !socketConfigured ||
      inferenceSocket?.readyState !== WebSocket.OPEN
    ) {
      requestPending = false;
      return;
    }
    inferenceSocket.send(JSON.stringify({
      type: "frame_meta",
      frame_id: frameId,
      video_time: videoTime
    }));
    inferenceSocket.send(blob);
  }, "image/jpeg", 0.82);
}

function defaultBackendHttpOrigin() {
  if (window.location.protocol === "http:" || window.location.protocol === "https:") {
    return window.location.origin;
  }
  return "http://127.0.0.1:8000";
}

function inferenceWebSocketUrls() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const hostname = window.location.hostname || "127.0.0.1";
  const candidates = [];
  if (window.location.host) {
    candidates.push(`${protocol}//${window.location.host}/api/v1/ws/inference`);
  }
  candidates.push(`${protocol}//${hostname}:8000/api/v1/ws/inference`);
  return [...new Set(candidates)];
}

async function connectInferenceSocket() {
  closeInferenceSocket();
  let lastError = new Error("Không thể kết nối WebSocket inference");
  for (const socketUrl of inferenceWebSocketUrls()) {
    try {
      await connectInferenceSocketAt(socketUrl);
      const backendUrl = new URL(socketUrl);
      backendUrl.protocol = backendUrl.protocol === "wss:" ? "https:" : "http:";
      API = `${backendUrl.origin}/api/v1`;
      return;
    } catch (error) {
      lastError = error;
      closeInferenceSocket();
    }
  }
  throw lastError;
}

function connectInferenceSocketAt(socketUrl) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(socketUrl);
    inferenceSocket = socket;
    socket.binaryType = "arraybuffer";
    let ready = false;
    const connectionTimeout = setTimeout(() => {
      if (ready) return;
      reject(new Error(`WebSocket không phản hồi cấu hình: ${socketUrl}`));
      socket.close();
    }, 3000);

    socket.addEventListener("open", () => sendInferenceConfiguration());
    socket.addEventListener("message", event => {
      if (inferenceSocket !== socket) return;
      let message;
      try {
        message = JSON.parse(event.data);
      } catch {
        if (!ready) reject(new Error("Backend trả về WebSocket message không hợp lệ"));
        else handleInferenceSocketFailure("Backend trả về WebSocket message không hợp lệ");
        return;
      }

      if (message.type === "configured") {
        clearTimeout(connectionTimeout);
        socketConfigured = true;
        ready = true;
        resolve();
        return;
      }
      if (message.type === "error") {
        const errorMessage = message.message || "WebSocket inference thất bại";
        if (!ready) {
          clearTimeout(connectionTimeout);
          reject(new Error(errorMessage));
        }
        else handleInferenceSocketFailure(errorMessage);
        return;
      }
      if (message.type === "inference_result") handleInferenceResult(message);
    });
    socket.addEventListener("error", () => {
      if (!ready) {
        clearTimeout(connectionTimeout);
        reject(new Error(`Không thể kết nối WebSocket inference: ${socketUrl}`));
      }
    });
    socket.addEventListener("close", () => {
      clearTimeout(connectionTimeout);
      if (inferenceSocket !== socket) return;
      inferenceSocket = null;
      socketConfigured = false;
      requestPending = false;
      if (!ready) reject(new Error("WebSocket inference đã đóng trước khi sẵn sàng"));
      else if (running) handleInferenceSocketFailure("Mất kết nối WebSocket inference");
    });
  });
}

function sendInferenceConfiguration() {
  if (zonePoints.length !== 4 || inferenceSocket?.readyState !== WebSocket.OPEN) return;
  socketConfigured = false;
  inferenceSocket.send(JSON.stringify({
    type: "configure",
    zone_points: zonePoints,
    machine_state: machineSwitch.classList.contains("on") ? "running" : "stopped"
  }));
}

function handleInferenceResult(result) {
  requestPending = false;
  if (result.frame_id <= lastHandledFrame) return;
  lastHandledFrame = result.frame_id;
  latestPeople = result.people;
  renderResult(result);
  drawOverlay();
  const personInsideZone = result.people.some(person => person.inside_zone);
  if (!personInsideZone) violationLatched = false;
  if (personInsideZone && !violationLatched) {
    violationLatched = true;
    pendingViolation = {...result, videoTime: result.video_time};
    running = false;
    video.pause();
    video.currentTime = result.video_time;
    closeInferenceSocket();
    playbackButton.textContent = "▶ Tiếp tục";
    playbackButton.disabled = true;
    showReview(result.snapshot_data);
  }
}

function handleInferenceSocketFailure(message) {
  closeInferenceSocket();
  running = false;
  video.pause();
  playbackButton.textContent = "▶ Phát video";
  playbackButton.disabled = false;
  document.getElementById("flow-status").textContent = "Inference đã ngắt kết nối";
  showToast(message);
}

function closeInferenceSocket() {
  const socket = inferenceSocket;
  inferenceSocket = null;
  socketConfigured = false;
  requestPending = false;
  if (socket && socket.readyState < WebSocket.CLOSING) socket.close();
}

function renderResult(result) {
  const violation = result.result === "violate";
  document.getElementById("person-count").textContent = `${result.people.length} người`;
  const resultLabel = document.getElementById("result-label");
  resultLabel.textContent = violation ? "● VIOLATE" : "● NORMAL";
  resultLabel.className = violation ? "result-violate" : "result-normal";
  const inside = result.people.some(person => person.inside_zone);
  const missingShirt = result.people.some(person => person.inside_zone && !person.safety_shirt);
  updateRule("rule-zone", inside, inside ? "Trong vùng nguy hiểm" : "Ngoài vùng", inside ? "YES" : "NO");
  updateRule("rule-ppe", !missingShirt, missingShirt ? "Không có áo bảo hộ" : "Có áo / không yêu cầu", missingShirt ? "MISS" : "OK");
  if (!violation) {
    const panel = document.getElementById("alert-panel");
    panel.classList.remove("violation");
    document.getElementById("alert-title").textContent = "Trạng thái bình thường";
    document.getElementById("severity").textContent = "NORMAL";
    document.getElementById("alert-summary").textContent = "Frame hiện tại không vi phạm rule an toàn đã định nghĩa.";
  }
}

function showReview(snapshotData) {
  const panel = document.getElementById("alert-panel");
  panel.classList.add("violation");
  const predictedViolation = pendingViolation.result === "violate";
  document.getElementById("alert-title").textContent = predictedViolation
    ? "Thiếu áo trong vùng cấm"
    : "Phát hiện người trong vùng";
  document.getElementById("severity").textContent = predictedViolation ? "VIOLATE" : "REVIEW";
  document.getElementById("alert-summary").textContent = "Video đã dừng tại frame phát hiện người trong vùng. Hãy xác nhận vi phạm thực tế hoặc bình thường / báo sai.";
  const snapshot = document.getElementById("snapshot");
  snapshot.src = snapshotData;
  snapshot.classList.add("visible");
  reviewActions.hidden = false;
  reviewStartedAt = Date.now();
  document.getElementById("review-message").textContent = "Khung hình đang chờ cán bộ an toàn xác minh";
  document.getElementById("event-status").textContent = "Đang chờ xác minh · chưa lưu";
  document.getElementById("flow-status").textContent = "Chờ xác minh";
  document.getElementById("confidence-label").textContent = predictedViolation ? "VIOLATE" : "REVIEW";
  document.getElementById("confidence-bar").style.width = "100%";
}

reviewActions.addEventListener("click", async event => {
  const status = event.target.dataset.review;
  if (!status || !pendingViolation) return;
  reviewActions.querySelectorAll("button").forEach(button => button.disabled = true);
  try {
    const response = await fetch(`${API}/events`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        zone_id: "zone_01",
        camera_id: "uploaded_video",
        event_type: pendingViolation.result === "violate" ? "missing_ppe_and_intrusion" : "zone_entry_review",
        severity: "high",
        status,
        acknowledged_by: "Safety Officer",
        snapshot_data: pendingViolation.snapshot_data,
        privacy_blurred: false,
        details: {
          inference_result: pendingViolation.result,
          review_result: status === "acknowledged" ? "actual_violation" : "normal",
          machine_state: machineSwitch.classList.contains("on") ? "running" : "stopped",
          video_timestamp_seconds: pendingViolation.videoTime,
          people: pendingViolation.people,
          zone_points: zonePoints
        }
      })
    });
    if (!response.ok) throw new Error("Không thể lưu kết quả xác minh");
    const saved = await response.json();
    document.getElementById("event-status").textContent = `Đã lưu EVENT #${saved.id} · ${status === "acknowledged" ? "vi phạm thực tế" : "báo sai"}`;
    reviewActions.hidden = true;
    playbackButton.disabled = false;
    reviewStartedAt = null;
    document.getElementById("review-message").textContent = "Đã lưu kết quả xác minh";
    document.getElementById("flow-status").textContent = "Đã lưu sự kiện";
    pendingViolation = null;
    showToast("Kết quả xác minh và khung hình đã được lưu.");
  } catch (error) {
    showToast(error.message);
  } finally {
    reviewActions.querySelectorAll("button").forEach(button => button.disabled = false);
  }
});

function drawOverlay() {
  const context = overlay.getContext("2d");
  context.clearRect(0, 0, overlay.width, overlay.height);
  if (zonePoints.length) {
    context.beginPath();
  zonePoints.forEach((point, index) => {
      const x = point.x * overlay.width;
      const y = point.y * overlay.height;
      if (index === 0) context.moveTo(x, y); else context.lineTo(x, y);
    });
    if (zonePoints.length === 4) context.closePath();
    context.fillStyle = "rgba(247, 215, 77, .20)";
    context.strokeStyle = "#f4cc2f";
    context.lineWidth = 3;
    if (zonePoints.length === 4) context.fill();
    context.stroke();
    zonePoints.forEach((point, index) => {
      context.beginPath();
      context.arc(point.x * overlay.width, point.y * overlay.height, 7, 0, Math.PI * 2);
    context.fillStyle = "#f4cc2f";
    context.fill();
    if (selectedPoint === index) {
      context.strokeStyle = "#fff";
      context.lineWidth = 3;
      context.stroke();
    }
      context.fillStyle = "#17231f";
      context.font = "bold 11px Manrope";
      context.fillText(String(index + 1), point.x * overlay.width - 3, point.y * overlay.height + 4);
    });
  }
  latestPeople.forEach(person => {
    const [x1, y1, x2, y2] = person.bbox;
    context.strokeStyle = person.inside_zone ? "#ff4940" : "#68e29a";
    context.lineWidth = 4;
    context.strokeRect(x1, y1, x2 - x1, y2 - y1);
    context.fillStyle = context.strokeStyle;
    context.font = "bold 16px Manrope";
    context.fillText(person.safety_shirt ? "PERSON · SHIRT" : "PERSON · NO SHIRT", x1, Math.max(18, y1 - 7));
    if (person.foot_point?.length === 2) {
      const [footX, footY] = person.foot_point;
      context.beginPath();
      context.arc(footX, footY, 7, 0, Math.PI * 2);
      context.fillStyle = person.inside_zone ? "#ff4940" : "#68e29a";
      context.fill();
      context.strokeStyle = "#ffffff";
      context.lineWidth = 2;
      context.stroke();
    }
  });
}

function updateRule(id, yes, text, badge) {
  const element = document.getElementById(id);
  element.className = `rule ${yes ? "yes" : "no"}`;
  element.querySelector("strong").textContent = text;
  element.querySelector("b").textContent = badge;
}

function updateZoneHint() {
  document.getElementById("zone-hint").textContent = zonePoints.length === 4
    ? "Vùng đã sẵn sàng · Kéo điểm để điều chỉnh"
    : `Chọn 4 điểm · ${zonePoints.length}/4`;
}

function stopRealtimeInference() {
  running = false;
  closeInferenceSocket();
  video.pause();
  playbackButton.textContent = "▶ Phát video";
  playbackButton.disabled = false;
}

function evaluatePreviewCandidate() {
  if (!video.videoWidth || !video.videoHeight || running || previewReady) return;
  const sample = document.createElement("canvas");
  sample.width = 32;
  sample.height = 18;
  const sampleContext = sample.getContext("2d", {willReadFrequently: true});
  sampleContext.drawImage(video, 0, 0, sample.width, sample.height);
  const pixels = sampleContext.getImageData(0, 0, sample.width, sample.height).data;
  let brightness = 0;
  for (let index = 0; index < pixels.length; index += 4) {
    brightness += (pixels[index] + pixels[index + 1] + pixels[index + 2]) / 3;
  }
  brightness /= pixels.length / 4;

  const lastCandidate = previewCandidateIndex >= previewCandidates.length - 1
    || previewCandidates[previewCandidateIndex] >= video.duration - 0.01;
  if (brightness < 18 && !lastCandidate) {
    previewCandidateIndex += 1;
    seekPreviewCandidate();
    return;
  }

  const context = capture.getContext("2d");
  context.drawImage(video, 0, 0, capture.width, capture.height);
  videoPreview.src = capture.toDataURL("image/jpeg", 0.9);
  videoPreview.hidden = false;
  previewReady = true;
  playbackButton.disabled = false;
  zoneButton.disabled = false;
  document.getElementById("flow-status").textContent = "Chờ cấu hình vùng";
}

function stopPreviewPlayback() {
  running = false;
  closeInferenceSocket();
  video.pause();
  playbackButton.textContent = "▶ Phát video";
  capturePausedFrame();
  selectingZone = true;
  zoneButton.textContent = "✓ Xong cấu hình";
  zoneButton.classList.add("zone-config-active");
  document.getElementById("flow-status").textContent = "Chọn hoặc điều chỉnh 4 điểm";
}

function capturePausedFrame() {
  if (!video.videoWidth || !video.videoHeight) return;
  const context = capture.getContext("2d");
  context.drawImage(video, 0, 0, capture.width, capture.height);
  videoPreview.src = capture.toDataURL("image/jpeg", 0.9);
  videoPreview.hidden = false;
}

function normalizedPointerPosition(event) {
  const rect = overlay.getBoundingClientRect();
  return {
    x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
    y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height))
  };
}

function findPointAt(position) {
  const rect = overlay.getBoundingClientRect();
  const radius = 18;
  const index = zonePoints.findIndex(point => {
    const dx = (point.x - position.x) * rect.width;
    const dy = (point.y - position.y) * rect.height;
    return Math.hypot(dx, dy) <= radius;
  });
  return index === -1 ? null : index;
}

function syncZoneState() {
  if (zonePoints.length === 4) {
    document.getElementById("flow-status").textContent = "Sẵn sàng inference realtime · nhấn Phát video";
  } else {
    document.getElementById("flow-status").textContent = "Chờ đủ 4 điểm";
  }
  updateZoneHint();
  drawOverlay();
  positionDeleteButton();
}

function positionDeleteButton() {
  if (selectedPoint === null || !zonePoints[selectedPoint]) {
    deletePointButton.hidden = true;
    return;
  }
  const point = zonePoints[selectedPoint];
  deletePointButton.style.left = `${point.x * 100}%`;
  deletePointButton.style.top = `${point.y * 100}%`;
  deletePointButton.hidden = false;
}

function seekPreviewCandidate() {
  const target = Math.min(
    previewCandidates[previewCandidateIndex],
    Math.max(0, video.duration - 0.01)
  );
  video.currentTime = target;
}

function resetAlert() {
  reviewStartedAt = null;
  const panel = document.getElementById("alert-panel");
  panel.classList.remove("violation");
  document.getElementById("alert-title").textContent = "Chưa có vi phạm";
  document.getElementById("severity").textContent = "NORMAL";
  document.getElementById("alert-summary").textContent = "Người trong vùng nguy hiểm phải mặc áo bảo hộ khi máy đang hoạt động.";
  document.getElementById("review-message").textContent = "Khung hình vi phạm sẽ hiện tại đây";
  document.getElementById("event-status").textContent = "CHƯA CÓ SỰ KIỆN ĐƯỢC LƯU";
  document.getElementById("confidence-label").textContent = "READY";
  document.getElementById("confidence-bar").style.width = "12%";
  document.getElementById("timer").textContent = "00:00";
}

function showToast(message) {
  const toast = document.getElementById("toast");
  document.getElementById("toast-message").textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 3000);
}

function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
}

setInterval(() => {
  document.getElementById("clock").textContent = new Date().toLocaleTimeString("vi-VN", {hour12: false});
  if (reviewStartedAt) {
    const seconds = Math.floor((Date.now() - reviewStartedAt) / 1000);
    document.getElementById("timer").textContent = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
  }
}, 1000);
