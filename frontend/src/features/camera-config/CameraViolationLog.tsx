import {useCallback, useEffect, useRef, useState} from "react";
import {getAccessToken} from "../../api/auth";
import {CameraDetectionClient} from "../../api/camera-detection-client";
import {assetUrl} from "../../api/config";
import {loadCameraEvents, saveReviewedEvent, subscribeToSafetyEventUpdates} from "../../api/events";
import type {CameraConfiguration, EventStatus, InferenceResult, ReviewStatus, SafetyEvent} from "../../types";
import {ReviewModal} from "../alerts/ReviewModal";
import {violationRuleLabel} from "../alerts/violation-copy";
import {buildEventPayload} from "../monitor/use-monitor";

interface CameraViolationLogProps {
  cameraId: string;
  configuration: CameraConfiguration;
}

export function CameraViolationLog({cameraId, configuration}: CameraViolationLogProps) {
  const [events, setEvents] = useState<SafetyEvent[]>([]);
  const [status, setStatus] = useState("Đang tải log vi phạm...");
  const [loadFailed, setLoadFailed] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState<SafetyEvent | null>(null);
  const [reviewSaving, setReviewSaving] = useState(false);
  const [reviewStartedAt, setReviewStartedAt] = useState<number | null>(null);
  const requestIdRef = useRef(0);
  const selectedEventRef = useRef<SafetyEvent | null>(null);
  const reviewSavingRef = useRef(false);

  const load = useCallback(async (showLoading = true) => {
    const requestId = ++requestIdRef.current;
    if (showLoading) {
      setStatus("Đang tải log vi phạm...");
      setLoadFailed(false);
    }
    try {
      const loaded = await loadCameraEvents(cameraId);
      if (requestId !== requestIdRef.current) return;
      setEvents(loaded);
      setLoadFailed(false);
      setStatus(loaded.some(event => event.status === "unacknowledged") ? "" : "Camera này chưa có log vi phạm.");
    } catch (reason) {
      if (requestId !== requestIdRef.current) return;
      setLoadFailed(true);
      setStatus(reason instanceof Error ? reason.message : "Không thể tải log vi phạm của camera.");
    }
  }, [cameraId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => subscribeToSafetyEventUpdates(update => {
    if (!update.cameraIds.includes(cameraId)) return;
    if (selectedEventRef.current && update.eventIds.includes(selectedEventRef.current.id)) {
      selectedEventRef.current = null;
      setSelectedEvent(null);
      setReviewStartedAt(null);
    }
    void load(false);
  }), [cameraId, load]);

  useEffect(() => {
    const refresh = () => void load(false);
    const accessToken = getAccessToken();
    let client: CameraDetectionClient | null = null;
    let retryTimer: number | undefined;
    let disposed = false;

    const scheduleReconnect = () => {
      if (disposed || retryTimer !== undefined) return;
      retryTimer = window.setTimeout(() => {
        retryTimer = undefined;
        connect();
      }, 1000);
    };
    const connect = () => {
      if (!accessToken || disposed) return;
      client?.close();
      client = new CameraDetectionClient({
        accessToken,
        cameraIds: [cameraId],
        onResult: result => {
          if (result.pending_event_ids?.length) refresh();
        },
        onFailure: scheduleReconnect,
      });
      void client.connect().then(refresh).catch(scheduleReconnect);
    };
    connect();

    return () => {
      disposed = true;
      requestIdRef.current += 1;
      if (retryTimer !== undefined) window.clearTimeout(retryTimer);
      client?.close();
    };
  }, [cameraId, load]);

  const pendingEvents = events.filter(event => event.status === "unacknowledged");
  const openCount = pendingEvents.length;
  const pendingReview = selectedEvent?.details?.pending_review;
  const violationKeys = pendingReview?.people.flatMap(person => person.active_violations
    ?.filter(violation => violation.is_new)
    .map(violation => violation.rule_key) ?? []) ?? [];
  const violationLabel = violationRuleLabel(violationKeys);
  const reviewTitle = `Phát hiện ${violationLabel.charAt(0).toLocaleLowerCase("vi-VN")}${violationLabel.slice(1)}`;
  const reviewTimer = useReviewTimer(reviewStartedAt);

  function openReview(event: SafetyEvent) {
    if (!event.details?.pending_review) {
      setLoadFailed(true);
      setStatus("Cảnh báo không còn đủ dữ liệu để mở HITL.");
      return;
    }
    selectedEventRef.current = event;
    setSelectedEvent(event);
    setReviewStartedAt(Date.now());
  }

  function closeReview() {
    selectedEventRef.current = null;
    setSelectedEvent(null);
    setReviewStartedAt(null);
  }

  async function review(reviewStatus: ReviewStatus) {
    const event = selectedEventRef.current;
    const result = event?.details?.pending_review;
    if (!event || !result || reviewSavingRef.current) return;
    const occurrenceIds = new Set(event.occurrence_ids ?? []);
    const people = result.people.map(person => ({
      ...person,
      active_violations: person.active_violations?.filter(violation =>
        occurrenceIds.size === 0 || occurrenceIds.has(violation.occurrence_id),
      ),
    })).filter(person => person.active_violations?.some(violation => violation.is_new));
    const person = people[0];
    if (!person) {
      setLoadFailed(true);
      setStatus("Cảnh báo không còn occurrence hợp lệ để xác minh.");
      return;
    }
    const zoneId = person.active_violations?.find(violation => violation.zone_id)?.zone_id ?? result.rule.zone_id;
    const zone = configuration.zones.find(item => item.zone_id === zoneId);
    const inference = {...result, type: "inference_result", people: [person]} satisfies InferenceResult;
    reviewSavingRef.current = true;
    setReviewSaving(true);
    setLoadFailed(false);
    setStatus("");
    try {
      await saveReviewedEvent(buildEventPayload(
        reviewStatus,
        inference,
        zone?.points ?? [],
        configuration.machine_state === "running",
        zone?.display_name ?? zoneId,
      ));
      setEvents(current => current.filter(item => item.id !== event.id));
      closeReview();
    } catch (reason) {
      setLoadFailed(true);
      setStatus(reason instanceof Error ? reason.message : "Không thể lưu kết quả xác minh.");
    } finally {
      reviewSavingRef.current = false;
      setReviewSaving(false);
    }
  }

  return <section className="camera-config-section camera-violation-log" aria-labelledby="camera-violation-log-heading">
    <div className="camera-config-section-heading">
      <div className="camera-log-heading-copy"><span className="camera-config-section-kicker">LỊCH SỬ</span><strong id="camera-violation-log-heading">Nhật ký vi phạm Camera {cameraNumber(cameraId)}</strong><small>Event được tự động đồng bộ cho camera này.</small></div>
      <button type="button" className="secondary-btn" onClick={() => void load()}>↻ Làm mới</button>
    </div>
    <div className="camera-log-summary" aria-label="Tổng quan log vi phạm">
      <div><span>TỔNG LOG</span><strong>{events.length}</strong></div>
      <div><span>ĐANG XỬ LÝ</span><strong>{openCount}</strong></div>
      <div><span>ĐÃ ĐÓNG</span><strong>{Math.max(events.length - openCount, 0)}</strong></div>
    </div>
    {status && <p className="camera-violation-log-status" role={loadFailed ? undefined : "status"} aria-live={loadFailed ? "assertive" : undefined}>{status}</p>}
    {pendingEvents.length > 0 && <div className="camera-violation-list" role="list" aria-label={`Danh sách log Camera ${cameraNumber(cameraId)}`}>
      {pendingEvents.map(event => <CameraViolationRow key={event.id} event={event} onOpen={() => openReview(event)} />)}
    </div>}
    <ReviewModal
      isOpen={Boolean(pendingReview)}
      onClose={closeReview}
      snapshot={assetUrl(selectedEvent?.snapshot_path) ?? undefined}
      people={pendingReview?.people}
      zones={configuration.zones}
      timer={reviewTimer}
      reviewSaving={reviewSaving}
      alertTitle={reviewTitle}
      alertSummary={selectedEvent ? `${selectedEvent.camera_id} · ${new Date(selectedEvent.timestamp).toLocaleString("vi-VN")}` : ""}
      onReview={reviewStatus => void review(reviewStatus)}
      closeable
      compact
    />
  </section>;
}

function CameraViolationRow({event, onOpen}: {event: SafetyEvent; onOpen: () => void}) {
  return <article className="camera-violation-row" role="listitem">
    <div>
      <strong>#{event.id} · {violationLabel(event)}</strong>
      <small>{new Date(event.timestamp).toLocaleString("vi-VN", {hour12: false})} · Vùng {event.zone_id} · <b>{event.severity.toUpperCase()}</b></small>
    </div>
    <div className="camera-violation-row-meta">
      <span className={`camera-event-status ${event.status}`}>{statusLabel(event.status)}</span>
      <button type="button" className="event-audit-button" aria-label={`Xem chi tiết vi phạm #${event.id}`} onClick={onOpen}>Xem chi tiết →</button>
    </div>
  </article>;
}

function violationLabel(event: SafetyEvent): string {
  if (event.event_type === "zone_intrusion") return "Xâm nhập vùng";
  if (event.event_type === "missing_ppe_and_intrusion") return "Thiếu PPE và xâm nhập vùng";
  if (event.event_type === "missing_ppe") return "Thiếu PPE";
  return "Vi phạm an toàn";
}

function statusLabel(status: EventStatus): string {
  return {acknowledged: "Đã xác nhận", resolved: "Đã xử lý", false_alarm: "Báo sai", unacknowledged: "Chưa xác nhận"}[status];
}

function cameraNumber(cameraId: string): string {
  return cameraId.replace("cam_", "");
}

function useReviewTimer(startedAt: number | null): string {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (startedAt === null) { setElapsed(0); return; }
    const update = () => setElapsed(Math.floor((Date.now() - startedAt) / 1000));
    update();
    const timer = window.setInterval(update, 1000);
    return () => window.clearInterval(timer);
  }, [startedAt]);
  return `${String(Math.floor(elapsed / 60)).padStart(2, "0")}:${String(elapsed % 60).padStart(2, "0")}`;
}
