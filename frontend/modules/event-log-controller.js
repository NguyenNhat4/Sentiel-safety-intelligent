import {getApiBase, resolveBackendUrl} from "./config.js";
import {dom} from "./dom.js";
import {showToast} from "./ui.js";

export function createEventLogController() {
  function initialize() {
    dom.monitorNav.addEventListener("click", showMonitor);
    dom.violationLogNav.addEventListener("click", show);
    dom.refreshEventsButton.addEventListener("click", loadEvents);
  }

  async function show() {
    dom.monitorPage.classList.remove("active");
    dom.eventLogPage.classList.add("active");
    dom.monitorNav.classList.remove("active");
    dom.violationLogNav.classList.add("active");
    await loadEvents();
  }

  function showMonitor() {
    dom.eventLogPage.classList.remove("active");
    dom.monitorPage.classList.add("active");
    dom.violationLogNav.classList.remove("active");
    dom.monitorNav.classList.add("active");
  }

  async function loadEvents() {
    setStatus("Đang tải nhật ký vi phạm...");
    dom.eventLogList.replaceChildren();
    try {
      const response = await fetch(`${getApiBase()}/events?status=acknowledged&limit=50`);
      if (!response.ok) throw new Error(`Không thể tải nhật ký (HTTP ${response.status})`);
      const events = await response.json();
      if (!events.length) {
        setStatus("Chưa có vi phạm nào được xác nhận.");
        return;
      }
      dom.eventLogStatus.hidden = true;
      events.forEach(event => dom.eventLogList.append(createEventCard(event)));
    } catch (error) {
      setStatus(error.message);
      showToast(error.message);
    }
  }

  return {initialize, loadEvents, show, showMonitor};
}

function createEventCard(event) {
  const card = createElement("article", "event-card");
  const snapshotUrl = resolveBackendUrl(event.snapshot_path);
  if (snapshotUrl) {
    const image = createElement("img");
    image.src = snapshotUrl;
    image.alt = `Snapshot sự kiện ${event.id}`;
    card.append(image);
  } else {
    card.append(createElement("div", "log-status", "Không có snapshot"));
  }

  const body = createElement("div", "event-card-body");
  const heading = createElement("div", "event-card-head");
  const title = createElement("div");
  title.append(
    createElement("small", "", `EVENT #${event.id}`),
    createElement("h3", "", eventTypeLabel(event.event_type)),
    createElement("time", "", formatTimestamp(event.timestamp))
  );
  heading.append(title, createElement("span", "event-badge", "ĐÃ XÁC NHẬN"));
  body.append(heading, createMetadata(event), createDetails(event));
  card.append(body);
  return card;
}

function createMetadata(event) {
  const metadata = createElement("div", "event-meta");
  metadata.append(
    createElement("span", "", `Vùng: ${event.zone_id}`),
    createElement("span", "", `Camera: ${event.camera_id}`),
    createElement("span", "", `Mức độ: ${event.severity}`),
    createElement("span", "", `Xác nhận: ${event.acknowledged_by || "Safety Officer"}`)
  );
  return metadata;
}

function createDetails(event) {
  const details = event.details || {};
  const people = Array.isArray(details.people) ? details.people.length : 0;
  const timestamp = Number(details.video_timestamp_seconds || 0).toFixed(1);
  return createElement("p", "event-details", `Phát hiện ${people} người · Video ${timestamp}s · ${details.review_result || "actual_violation"}`);
}

function createElement(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text) element.textContent = text;
  return element;
}

function eventTypeLabel(type) {
  if (type === "missing_ppe_and_intrusion") return "Thiếu PPE trong vùng cấm";
  return "Người đi vào vùng cấm khi máy đang chạy";
}

function formatTimestamp(timestamp) {
  return new Date(timestamp).toLocaleString("vi-VN", {hour12: false});
}

function setStatus(message) {
  dom.eventLogStatus.hidden = false;
  dom.eventLogStatus.textContent = message;
}
