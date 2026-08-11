import {describe, expect, it, vi} from "vitest";
import type {InferenceResult} from "../types";
import {InferenceClient} from "./inference-client";

class FakeSocket extends EventTarget {
  readyState: number = WebSocket.CONNECTING;
  sent: unknown[] = [];

  send(data: unknown) { this.sent.push(data); }
  close() { this.readyState = WebSocket.CLOSED; }
  open() { this.readyState = WebSocket.OPEN; this.dispatchEvent(new Event("open")); }
  message(data: unknown) { this.dispatchEvent(new MessageEvent("message", {data: JSON.stringify(data)})); }
}

describe("InferenceClient", () => {
  it("configures first and allows only one frame in flight", async () => {
    const sockets: FakeSocket[] = [];
    const onResult = vi.fn();
    const client = new InferenceClient({
      getConfiguration: () => ({
        zone_points: [{x: 0, y: 0}, {x: 1, y: 0}, {x: 1, y: 1}, {x: 0, y: 1}],
        machine_state: "running",
        monitoring_session_id: "3cddfe85-9428-44d7-afbf-0cd9e5fc0640"
      }),
      onResult,
      onFailure: vi.fn(),
      socketFactory: () => {
        const socket = new FakeSocket();
        sockets.push(socket);
        return socket as unknown as WebSocket;
      }
    });

    const connection = client.connect();
    sockets[0].open();
    expect(JSON.parse(sockets[0].sent[0] as string).type).toBe("configure");
    expect(JSON.parse(sockets[0].sent[0] as string).monitoring_session_id).toBe("3cddfe85-9428-44d7-afbf-0cd9e5fc0640");
    sockets[0].message({type: "configured"});
    await connection;

    expect(client.sendFrame(7, 2.5, new Blob(["jpeg"]))).toBe(true);
    expect(client.sendFrame(8, 3, new Blob(["jpeg"]))).toBe(false);
    const result: InferenceResult = {
      type: "inference_result", frame_id: 7, video_time: 2.5,
      result: "normal", review_required: false, people: [],
      rule: {
        person_inside_zone: false, machine_state: "running", safety_shirt_required: true,
        camera_id: "uploaded_video", zone_id: "zone_01",
        ppe_requirements: {helmet_required: false, safety_glasses_required: false, gloves_required: false},
        ppe_alert: false,
      }
    };
    sockets[0].message(result);
    expect(onResult).toHaveBeenCalledWith(result);
    expect(client.canSend).toBe(true);
  });

  it("sends configure message even when zone_points is empty", async () => {
    const sockets: FakeSocket[] = [];
    const client = new InferenceClient({
      getConfiguration: () => ({
        zone_points: [],
        machine_state: "running",
        monitoring_session_id: "46a62d3a-4fb4-4a54-87bc-58e075722e2c"
      }),
      onResult: vi.fn(),
      onFailure: vi.fn(),
      socketFactory: () => {
        const socket = new FakeSocket();
        sockets.push(socket);
        return socket as unknown as WebSocket;
      }
    });

    const connection = client.connect();
    sockets[0].open();
    expect(JSON.parse(sockets[0].sent[0] as string)).toEqual({
      type: "configure",
      zone_points: [],
      machine_state: "running",
      monitoring_session_id: "46a62d3a-4fb4-4a54-87bc-58e075722e2c"
    });
    sockets[0].message({type: "configured"});
    await connection;
    expect(client.canSend).toBe(true);
  });

  it("sends the saved multi-zone collection and revision", async () => {
    const sockets: FakeSocket[] = [];
    const client = new InferenceClient({
      getConfiguration: () => ({
        zones: [{
          zone_id: "press_01", display_name: "Máy dập", machine_state: "running", enabled: true, order: 0,
          points: [{x: 0, y: 0}, {x: 0.4, y: 0}, {x: 0.4, y: 1}, {x: 0, y: 1}],
        }],
        zone_revision: 7,
        camera_id: "uploaded_video",
        monitoring_session_id: "46a62d3a-4fb4-4a54-87bc-58e075722e2c",
      }),
      onResult: vi.fn(), onFailure: vi.fn(),
      socketFactory: () => {
        const socket = new FakeSocket(); sockets.push(socket); return socket as unknown as WebSocket;
      },
    });

    const connection = client.connect();
    sockets[0].open();
    expect(JSON.parse(sockets[0].sent[0] as string)).toMatchObject({
      type: "configure", zone_revision: 7, camera_id: "uploaded_video",
      zones: [{zone_id: "press_01", machine_state: "running"}],
    });
    sockets[0].message({type: "configured", zone_revision: 7});
    await connection;
  });
});
