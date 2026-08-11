import {afterEach, describe, expect, it, vi} from "vitest";
import {loadPpeRequirements, savePpeRequirements} from "./ppe-requirements";

describe("PPE requirements API", () => {
  afterEach(() => vi.restoreAllMocks());

  it("loads the fixed camera-zone requirement resource", async () => {
    const payload = {
      camera_id: "uploaded_video", zone_id: "zone_01",
      helmet_required: false, safety_glasses_required: false, gloves_required: false,
      is_configured: false, updated_at: null
    };
    const fetchMock = vi.spyOn(window, "fetch").mockResolvedValue(
      new Response(JSON.stringify(payload), {status: 200, headers: {"Content-Type": "application/json"}})
    );

    await expect(loadPpeRequirements("uploaded_video", "zone_01")).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/ppe-requirements/uploaded_video/zone_01");
  });

  it("saves all three booleans with PUT", async () => {
    const fetchMock = vi.spyOn(window, "fetch").mockResolvedValue(
      new Response(JSON.stringify({
        camera_id: "uploaded_video", zone_id: "zone_01",
        helmet_required: true, safety_glasses_required: false, gloves_required: true,
        is_configured: true, updated_at: "2026-08-06T10:00:00Z"
      }), {status: 200, headers: {"Content-Type": "application/json"}})
    );

    await savePpeRequirements("uploaded_video", "zone_01", {
      helmet_required: true,
      safety_glasses_required: false,
      gloves_required: true
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/ppe-requirements/uploaded_video/zone_01",
      {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          helmet_required: true,
          safety_glasses_required: false,
          gloves_required: true
        })
      }
    );
  });

  it("returns a safe error for non-success responses", async () => {
    vi.spyOn(window, "fetch").mockResolvedValue(
      new Response(JSON.stringify({detail: "Database unavailable"}), {
        status: 503,
        headers: {"Content-Type": "application/json"}
      })
    );

    await expect(loadPpeRequirements("uploaded_video", "zone_01"))
      .rejects.toThrow("Database unavailable");
  });
});
