import {dom} from "./dom.js";
import {createFrameSampler} from "./frame-sampler.js";
import {drawOverlay} from "./overlay-renderer.js";
import {resetForVideo, resetFrameSequence, state} from "./state.js";
import {formatTime, resetAlert, setZoneEditing, showToast, updateRule, updateZoneHint} from "./ui.js";
import {capturePausedFrame, evaluatePreviewCandidate, seekPreviewCandidate} from "./video-preview.js";

export function createVideoController({inferenceClient}) {
  const frameSampler = createFrameSampler({inferenceClient});
  function initialize() {
    dom.uploadButton.addEventListener("click", () => dom.videoInput.click());
    dom.activityAction.addEventListener("click", () => dom.videoInput.click());
    dom.videoInput.addEventListener("change", handleVideoSelection);
    dom.video.addEventListener("loadedmetadata", handleLoadedMetadata);
    dom.video.addEventListener("seeked", handleSeeked);
    dom.playbackButton.addEventListener("click", handlePlayback);
    dom.video.addEventListener("ended", handleEnded);
    dom.machineSwitch.addEventListener("click", handleMachineToggle);
  }

  function handleVideoSelection() {
    const file = dom.videoInput.files[0];
    if (!file) return;
    inferenceClient.close();
    dom.video.pause();
    if (state.videoUrl) URL.revokeObjectURL(state.videoUrl);
    state.videoUrl = URL.createObjectURL(file);
    dom.video.src = state.videoUrl;
    dom.video.load();
    resetForVideo();
    dom.videoPreview.hidden = true;
    dom.fileLabel.textContent = file.name;
    dom.reviewActions.hidden = true;
    dom.playbackButton.disabled = true;
    dom.zoneButton.disabled = true;
    dom.playbackButton.textContent = "▶ Phát video";
    dom.deletePointButton.hidden = true;
    dom.snapshot.classList.remove("visible");
    dom.flowStatus.textContent = "Chờ cấu hình vùng";
    resetAlert();
    showToast("Video đã sẵn sàng. Hãy chọn 4 điểm cho vùng nguy hiểm.");
  }

  function handleLoadedMetadata() {
    dom.overlay.width = dom.video.videoWidth;
    dom.overlay.height = dom.video.videoHeight;
    dom.capture.width = dom.video.videoWidth;
    dom.capture.height = dom.video.videoHeight;
    dom.stage.classList.add("ready");
    dom.emptyState.hidden = true;
    dom.videoMeta.textContent = `${dom.video.videoWidth} × ${dom.video.videoHeight} · ${formatTime(dom.video.duration)}`;
    setZoneEditing(true);
    updateZoneHint();
    drawOverlay();
    seekPreviewCandidate();
  }

  function handleSeeked() {
    if (state.running || state.pendingViolation || state.previewReady) return;
    if (dom.video.requestVideoFrameCallback) dom.video.requestVideoFrameCallback(evaluatePreviewCandidate);
    else setTimeout(evaluatePreviewCandidate, 30);
  }

  async function handlePlayback() {
    if (!dom.video.src || state.pendingViolation) return;
    if (!dom.video.paused) {
      stopPreviewPlayback();
      return;
    }
    preparePlayback();
    if (dom.video.ended) dom.video.currentTime = 0;
    if (state.running && !(await connectInference())) return;
    await dom.video.play();
    if (state.running) frameSampler.start();
  }

  function preparePlayback() {
    state.previewReady = true;
    setZoneEditing(false);
    dom.videoPreview.hidden = true;
    dom.deletePointButton.hidden = true;
    dom.playbackButton.textContent = "■ Dừng video";
    state.running = state.zonePoints.length === 4;
    resetFrameSequence();
    dom.flowStatus.textContent = state.running ? "Đang inference realtime" : "Đang xem video · dừng để cấu hình đủ 4 điểm";
    dom.confidenceLabel.textContent = state.running ? "RUNNING" : "PREVIEW";
    dom.confidenceBar.style.width = state.running ? "70%" : "25%";
  }

  async function connectInference() {
    dom.flowStatus.textContent = "Đang kết nối inference";
    try {
      await inferenceClient.connect();
      dom.flowStatus.textContent = "Đang inference realtime";
      return true;
    } catch (error) {
      inferenceClient.close();
      state.running = false;
      dom.playbackButton.textContent = "▶ Phát video";
      dom.flowStatus.textContent = "Không thể kết nối inference";
      showToast(error.message);
      return false;
    }
  }

  function handleEnded() {
    state.running = false;
    inferenceClient.close();
    dom.playbackButton.textContent = "↻ Phát lại";
    capturePausedFrame();
  }

  function handleMachineToggle() {
    const on = dom.machineSwitch.classList.toggle("on");
    dom.machineLabel.textContent = on ? "Đang hoạt động" : "Đã dừng";
    updateRule("rule-machine", on, on ? "Machine A đang chạy" : "Machine A đã dừng", on ? "ON" : "OFF");
    inferenceClient.updateConfiguration();
  }

  function stopRealtimeInference() {
    state.running = false;
    inferenceClient.close();
    dom.video.pause();
    dom.playbackButton.textContent = "▶ Phát video";
    dom.playbackButton.disabled = false;
  }

  function stopPreviewPlayback() {
    stopRealtimeInference();
    capturePausedFrame();
    setZoneEditing(true);
    dom.flowStatus.textContent = "Chọn hoặc điều chỉnh 4 điểm";
  }

  function pauseForReview(videoTime) {
    state.running = false;
    dom.video.pause();
    dom.video.currentTime = videoTime;
    inferenceClient.close();
    dom.playbackButton.textContent = "▶ Tiếp tục";
    dom.playbackButton.disabled = true;
  }

  function handleInferenceFailure(message) {
    stopRealtimeInference();
    dom.flowStatus.textContent = "Inference đã ngắt kết nối";
    showToast(message);
  }

  return {handleInferenceFailure, initialize, pauseForReview, stopPreviewPlayback, stopRealtimeInference};
}
