import {CameraDetectionClient} from "./camera-detection-client";
import {expect, it} from "vitest";

class FakeSocket extends EventTarget {
  static OPEN = 1;
  readyState = FakeSocket.OPEN;
  sent: string[] = [];
  send(value: string) { this.sent.push(value); }
  close() { this.readyState = 3; }
}

it("authenticates once and routes camera-correlated results", async () => {
  const socket = new FakeSocket();
  const results: Array<{camera_id: string}> = [];
  const client = new CameraDetectionClient({
    accessToken: "session-token",
    cameraIds: ["cam_1", "cam_2"],
    onResult: result => results.push(result),
    onFailure: () => undefined,
    socketFactory: () => socket as unknown as WebSocket,
    socketUrls: ["ws://backend/api/v1/ws/camera-detections"],
  });
  const connected = client.connect();
  socket.dispatchEvent(new Event("open"));
  expect(JSON.parse(socket.sent[0])).toEqual({type: "authenticate", access_token: "session-token", camera_ids: ["cam_1", "cam_2"]});
  socket.dispatchEvent(new MessageEvent("message", {data: JSON.stringify({type: "subscribed", camera_ids: ["cam_1", "cam_2"]})}));
  await connected;
  socket.dispatchEvent(new MessageEvent("message", {data: JSON.stringify({type: "camera_inference_result", camera_id: "cam_2", frame_id: 4})}));
  expect(results).toEqual([{type: "camera_inference_result", camera_id: "cam_2", frame_id: 4}]);
});

it("accepts authoritative camera session status messages", async () => {
  const socket = new FakeSocket();
  const statuses: string[] = [];
  const failures: string[] = [];
  const client = new CameraDetectionClient({accessToken: "token", cameraIds: ["cam_1"], onResult: () => undefined, onSessionStatus: status => statuses.push(status.session_status), onFailure: message => failures.push(message), socketFactory: () => socket as unknown as WebSocket, socketUrls: ["ws://backend"]});
  const connected = client.connect(); socket.dispatchEvent(new Event("open"));
  socket.dispatchEvent(new MessageEvent("message", {data: JSON.stringify({type: "subscribed"})})); await connected;
  socket.dispatchEvent(new MessageEvent("message", {data: JSON.stringify({type: "camera_session_status", camera_id: "cam_1", session_id: "s1", asset_id: "a1", media_type: "image", video_time: 0, session_status: "COMPLETED", inference_fps: 2})}));
  expect(statuses).toEqual(["COMPLETED"]); expect(failures).toEqual([]);
});
