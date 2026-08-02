import {JPEG_QUALITY, SAMPLE_INTERVAL_SECONDS} from "./config.js";
import {dom} from "./dom.js";
import {state} from "./state.js";

export function createFrameSampler({inferenceClient}) {
  function start() {
    requestAnimationFrame(loop);
  }

  function loop() {
    if (!state.running || dom.video.ended) return;
    const sampleDue = dom.video.currentTime - state.lastSampleTime >= SAMPLE_INTERVAL_SECONDS;
    if (inferenceClient.canSend && sampleDue) {
      state.lastSampleTime = dom.video.currentTime;
      capture();
    }
    if (state.running) requestAnimationFrame(loop);
  }

  function capture() {
    dom.capture.getContext("2d").drawImage(dom.video, 0, 0, dom.capture.width, dom.capture.height);
    const frameId = state.frameSequence++;
    const videoTime = dom.video.currentTime;
    dom.capture.toBlob(blob => {
      if (!blob || !state.running) return;
      inferenceClient.sendFrame({frameId, videoTime, blob});
    }, "image/jpeg", JPEG_QUALITY);
  }

  return {start};
}
