import {afterEach, describe, expect, it, vi} from "vitest";
import {loadMonitoringZones, saveMonitoringZones} from "./monitoring-zones";

describe("monitoring zone transport", () => {
  afterEach(() => vi.restoreAllMocks());

  it("loads and atomically saves the full collection with expected_revision", async () => {
    const collection = {camera_id: "uploaded_video", revision: 4, zones: [], updated_at: null};
    const fetchSpy = vi.spyOn(window, "fetch")
      .mockResolvedValueOnce(new Response(JSON.stringify(collection), {status: 200}))
      .mockResolvedValueOnce(new Response(JSON.stringify({...collection, revision: 5}), {status: 200}));

    expect(await loadMonitoringZones("uploaded_video")).toEqual(collection);
    expect((await saveMonitoringZones("uploaded_video", 4, [])).revision).toBe(5);
    expect(fetchSpy.mock.calls[1][1]).toMatchObject({method: "PUT"});
    expect(JSON.parse(String(fetchSpy.mock.calls[1][1]?.body))).toEqual({expected_revision: 4, zones: []});
  });

  it("surfaces an optimistic revision conflict without overwriting", async () => {
    vi.spyOn(window, "fetch").mockResolvedValue(new Response(
      JSON.stringify({detail: {code: "revision_conflict"}}),
      {status: 409, headers: {"Content-Type": "application/json"}},
    ));
    await expect(saveMonitoringZones("uploaded_video", 1, [])).rejects.toThrow("đã thay đổi ở nơi khác");
  });
});
