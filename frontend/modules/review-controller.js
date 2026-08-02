import {getApiBase} from "./config.js";
import {dom} from "./dom.js";
import {drawOverlay} from "./overlay-renderer.js";
import {state} from "./state.js";
import {resetAlert, showToast, updateRule} from "./ui.js";

export function createReviewController({onZoneEntry}) {
  function handleInferenceResult(result) {
    if (result.frame_id <= state.lastHandledFrame) return;
    state.lastHandledFrame = result.frame_id;
    state.latestPeople = result.people;
    renderResult(result);
    drawOverlay();
    const reviewRequired = result.review_required === true;
    if (!reviewRequired) state.violationLatched = false;
    if (reviewRequired && !state.violationLatched) {
      state.violationLatched = true;
      state.pendingViolation = {...result, videoTime: result.video_time};
      onZoneEntry(result.video_time);
      showReview(result.snapshot_data);
    }
  }

  dom.reviewActions.addEventListener("click", async event => {
    const status = event.target.dataset.review;
    if (!status || !state.pendingViolation) return;
    setReviewButtonsDisabled(true);
    try {
      const response = await fetch(`${getApiBase()}/events`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(buildEventPayload(status))
      });
      if (!response.ok) throw new Error(await readErrorMessage(response));
      await response.json();
      closeReview();
      showToast("Kết quả xác minh và khung hình đã được lưu.");
    } catch (error) {
      showToast(error.message);
    } finally {
      setReviewButtonsDisabled(false);
    }
  });

  return {handleInferenceResult};
}

async function readErrorMessage(response) {
  try {
    const body = await response.json();
    return body.detail || `Không thể lưu kết quả xác minh (HTTP ${response.status})`;
  } catch {
    return `Không thể lưu kết quả xác minh (HTTP ${response.status})`;
  }
}

function renderResult(result) {
  const violation = result.result === "violate";
  dom.personCount.textContent = `${result.people.length} người`;
  dom.resultLabel.textContent = violation ? "● VIOLATE" : "● NORMAL";
  dom.resultLabel.className = violation ? "result-violate" : "result-normal";
  const inside = result.people.some(person => person.inside_zone);
  const missingShirt = result.people.some(person => person.inside_zone && !person.safety_shirt);
  updateRule("rule-zone", inside, inside ? "Trong vùng nguy hiểm" : "Ngoài vùng", inside ? "YES" : "NO");
  updateRule("rule-ppe", !missingShirt, missingShirt ? "Không có áo bảo hộ" : "Có áo / không yêu cầu", missingShirt ? "MISS" : "OK");
  if (violation) return;
  dom.alertPanel.classList.remove("violation");
  dom.alertTitle.textContent = "Trạng thái bình thường";
  dom.severity.textContent = "NORMAL";
  dom.alertSummary.textContent = "Frame hiện tại không vi phạm rule an toàn đã định nghĩa.";
}

function showReview(snapshotData) {
  dom.alertPanel.classList.add("violation");
  dom.alertTitle.textContent = "Người vào vùng cấm khi máy đang chạy";
  dom.severity.textContent = "VIOLATE";
  dom.alertSummary.textContent = "Video đã dừng tại frame phát hiện người trong vùng. Hãy xác nhận vi phạm thực tế hoặc bình thường / báo sai.";
  dom.snapshot.src = snapshotData;
  dom.snapshot.classList.add("visible");
  dom.reviewActions.hidden = false;
  state.reviewStartedAt = Date.now();
  dom.reviewMessage.textContent = "Khung hình đang chờ cán bộ an toàn xác minh";
  dom.eventStatus.textContent = "Đang chờ xác minh · chưa lưu";
  dom.flowStatus.textContent = "Chờ xác minh";
  dom.confidenceLabel.textContent = "VIOLATE";
  dom.confidenceBar.style.width = "100%";
}

function buildEventPayload(status) {
  const pending = state.pendingViolation;
  return {
    zone_id: "zone_01", camera_id: "uploaded_video",
    event_type: "zone_intrusion_while_machine_running",
    severity: "high", status, acknowledged_by: "Safety Officer",
    snapshot_data: pending.snapshot_data, privacy_blurred: false,
    details: {
      inference_result: pending.result,
      review_result: status === "acknowledged" ? "actual_violation" : "normal",
      machine_state: dom.machineSwitch.classList.contains("on") ? "running" : "stopped",
      video_timestamp_seconds: pending.videoTime,
      people: pending.people, zone_points: state.zonePoints
    }
  };
}

function setReviewButtonsDisabled(disabled) {
  dom.reviewActions.querySelectorAll("button").forEach(button => { button.disabled = disabled; });
}

function closeReview() {
  state.pendingViolation = null;
  state.reviewStartedAt = null;
  dom.reviewActions.hidden = true;
  dom.snapshot.classList.remove("visible");
  dom.snapshot.removeAttribute("src");
  dom.playbackButton.disabled = false;
  dom.flowStatus.textContent = "Đã đóng xác minh";
  resetAlert();
}
