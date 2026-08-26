import {describe, expect, it, vi} from "vitest";

import {
  checkVisionWorker,
  inferVisionWorker,
  summarizeLatencies,
  VisionWorkerContractError
} from "./vision-worker-compare";

const REQUEST_ID = "2aa6bc1d-59b2-4fef-91e0-761e8bb954d4";

const healthPayload = {
  status: "healthy",
  contract_version: "safety_vision_v1",
  model_version: "test-model"
};

const inferencePayload = {
  contract_version: "safety_vision_v1",
  request_id: REQUEST_ID,
  model_version: "test-model",
  canonical_people: [{bbox: [10, 20, 30, 40], confidence: 0.95, track_id: 7}],
  people: [
    {
      hat: {status: "present", confidence: 0.91},
      vest: {status: "unknown", confidence: null}
    }
  ],
  detections: [
    {
      class_id: 3,
      class_name: "person",
      bbox: [10, 20, 40, 60],
      confidence: 0.95,
      person_index: 0
    }
  ]
};

describe("vision worker comparison client", () => {
  it("routes health checks to the selected worker", async () => {
    const fetcher = vi.fn(async () => new Response(JSON.stringify(healthPayload), {status: 200}));

    await checkVisionWorker("gpu", fetcher);

    expect(fetcher).toHaveBeenCalledWith("/vision-worker-gpu-api/ping", {
      headers: {Accept: "application/json"},
      signal: expect.any(AbortSignal)
    });
  });

  it("sends the same JPEG contract to an explicitly selected worker", async () => {
    const fetcher = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      expect(url).toBe("/vision-worker-cpu-api/v1/infer");
      expect(init?.method).toBe("POST");
      expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer cpu-secret");
      const form = init?.body as FormData;
      expect(form.get("request_id")).toBe(REQUEST_ID);
      expect(form.get("monitoring_session_id")).toBe("compare-cpu-session");
      expect(form.get("image")).toBeInstanceOf(File);
      return new Response(JSON.stringify(inferencePayload), {status: 200});
    });

    await expect(
      inferVisionWorker(
        "cpu",
        {
          image: new File(["jpeg"], "frame.jpg", {type: "image/jpeg"}),
          apiKey: " cpu-secret ",
          monitoringSessionId: "compare-cpu-session",
          requestId: REQUEST_ID
        },
        fetcher
      )
    ).resolves.toEqual(inferencePayload);
  });

  it("rejects a response with the wrong request correlation", async () => {
    const fetcher = vi.fn(async () =>
      new Response(JSON.stringify({...inferencePayload, request_id: crypto.randomUUID()}), {status: 200})
    );

    await expect(
      inferVisionWorker(
        "gpu",
        {
          image: new File(["jpeg"], "frame.jpg", {type: "image/jpeg"}),
          requestId: REQUEST_ID
        },
        fetcher
      )
    ).rejects.toBeInstanceOf(VisionWorkerContractError);
  });

  it("calculates stable rolling latency statistics", () => {
    expect(summarizeLatencies([10, 20, 30, 40, 100])).toEqual({
      count: 5,
      latest: 100,
      mean: 40,
      p50: 30,
      p95: 100,
      fps: 25
    });
    expect(summarizeLatencies([])).toEqual({
      count: 0,
      latest: null,
      mean: null,
      p50: null,
      p95: null,
      fps: null
    });
  });
});
