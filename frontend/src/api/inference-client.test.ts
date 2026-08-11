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
        machine_state: "running"
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
      getConfiguration: () => ({zone_points: [], machine_state: "running"}),
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
      machine_state: "running"
    });
    sockets[0].message({type: "configured"});
    await connection;
    expect(client.canSend).toBe(true);
  });
});
