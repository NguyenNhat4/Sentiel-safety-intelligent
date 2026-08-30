import {afterEach, describe, expect, it, vi} from "vitest";
import {
  loadCameraEvents,
  loadEventDetail,
  loadReviewedEvents,
  saveReviewedEvent,
  subscribeToSafetyEventUpdates,
  updateAreaEvent,
} from "./events";
import type {EventPayload} from "../types";

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {status, headers: {"Content-Type": "application/json"}});
}

afterEach(() => {
  window.sessionStorage.clear();
  vi.restoreAllMocks();
});

describe("event audit transport", () => {
  it("loads violation logs for one camera", async () => {
    const fetchMock = vi.fn(async () => jsonResponse([{id: 7, camera_id: "cam_3"}]));
    vi.stubGlobal("fetch", fetchMock);

    await expect(loadCameraEvents("cam_3")).resolves.toEqual([{id: 7, camera_id: "cam_3"}]);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/events?camera_id=cam_3&limit=50",
      expect.objectContaining({headers: expect.any(Object)}),
    );
  });

  it("loads a typed event detail with the current authenticated session", async () => {
    window.sessionStorage.setItem("sentinel.auth.access_token", "audit-token");
    const fetchMock = vi.fn(async () => jsonResponse({id: 42, summary: {text: "Audit", source: "deterministic"}}));
    vi.stubGlobal("fetch", fetchMock);

    const detail = await loadEventDetail(42);

    expect(detail.id).toBe(42);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/events/42",
      {cache: "no-store", headers: {Authorization: "Bearer audit-token"}},
    );
  });

  it("loads false alarms through the review-status filter", async () => {
    window.sessionStorage.setItem("sentinel.auth.access_token", "audit-token");
    const fetchMock = vi.fn(async () => jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    await loadReviewedEvents("false_alarm");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/events?status=false_alarm&limit=50",
      {cache: "no-store", headers: {Authorization: "Bearer audit-token"}},
    );
  });

  it("attaches the authenticated actor token when saving a review", async () => {
    window.sessionStorage.setItem("sentinel.auth.access_token", "audit-token");
    const fetchMock = vi.fn(async () => jsonResponse({
      id: 1,
      timestamp: "2026-08-30T10:20:00Z",
      zone_id: "zone_01",
      camera_id: "uploaded_video",
      event_type: "zone_intrusion",
      severity: "high",
      status: "acknowledged",
    }, 201));
    vi.stubGlobal("fetch", fetchMock);
    const payload = {
      zone_id: "zone_01",
      camera_id: "uploaded_video",
      event_type: "zone_intrusion",
      severity: "high",
      status: "acknowledged",
      acknowledged_by: "Legacy display value",
      details: {},
      occurrence_ids: [],
    } satisfies EventPayload;

    const listener = vi.fn();
    const unsubscribe = subscribeToSafetyEventUpdates(listener);
    await saveReviewedEvent(payload);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/events",
      expect.objectContaining({
        method: "POST",
        headers: {"Content-Type": "application/json", Authorization: "Bearer audit-token"},
      }),
    );
    expect(listener).toHaveBeenCalledWith({eventIds: [1], cameraIds: ["uploaded_video"]});
    unsubscribe();
  });

  it("announces an event status update made from a detail workflow", async () => {
    const updated = {
      id: 9,
      timestamp: "2026-08-30T10:20:00Z",
      zone_id: "press",
      camera_id: "cam_2",
      event_type: "zone_intrusion",
      severity: "high",
      status: "resolved",
    };
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(updated)));
    const listener = vi.fn();
    const unsubscribe = subscribeToSafetyEventUpdates(listener);

    await updateAreaEvent(9, "resolved");

    expect(listener).toHaveBeenCalledWith({eventIds: [9], cameraIds: ["cam_2"]});
    unsubscribe();
  });
});
