import {dom} from "./dom.js";
import {state} from "./state.js";

export function evaluatePreviewCandidate() {
  if (!dom.video.videoWidth || !dom.video.videoHeight || state.running || state.previewReady) return;
  const sample = document.createElement("canvas");
  sample.width = 32;
  sample.height = 18;
  const context = sample.getContext("2d", {willReadFrequently: true});
  context.drawImage(dom.video, 0, 0, sample.width, sample.height);
  const pixels = context.getImageData(0, 0, sample.width, sample.height).data;
  let brightness = 0;
  for (let index = 0; index < pixels.length; index += 4) {
    brightness += (pixels[index] + pixels[index + 1] + pixels[index + 2]) / 3;
  }
  brightness /= pixels.length / 4;

  const candidate = state.previewCandidates[state.previewCandidateIndex];
  const lastCandidate = state.previewCandidateIndex >= state.previewCandidates.length - 1
    || candidate >= dom.video.duration - 0.01;
  if (brightness < 18 && !lastCandidate) {
    state.previewCandidateIndex += 1;
    seekPreviewCandidate();
    return;
  }

  capturePausedFrame();
  state.previewReady = true;
  dom.playbackButton.disabled = false;
  dom.zoneButton.disabled = false;
  dom.flowStatus.textContent = "Chờ cấu hình vùng";
}

export function capturePausedFrame() {
  if (!dom.video.videoWidth || !dom.video.videoHeight) return;
  const context = dom.capture.getContext("2d");
  context.drawImage(dom.video, 0, 0, dom.capture.width, dom.capture.height);
  dom.videoPreview.src = dom.capture.toDataURL("image/jpeg", 0.9);
  dom.videoPreview.hidden = false;
}

export function seekPreviewCandidate() {
  const candidate = state.previewCandidates[state.previewCandidateIndex];
  const target = Math.min(candidate, Math.max(0, dom.video.duration - 0.01));
  dom.video.currentTime = target;
}
