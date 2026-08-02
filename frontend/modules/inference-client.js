import {inferenceWebSocketUrls, setApiBaseFromSocket} from "./config.js";

export class InferenceClient {
  constructor({getConfiguration, onResult, onFailure}) {
    this.getConfiguration = getConfiguration;
    this.onResult = onResult;
    this.onFailure = onFailure;
    this.socket = null;
    this.configured = false;
    this.awaitingResult = false;
  }

  get canSend() {
    return this.configured && !this.awaitingResult && this.socket?.readyState === WebSocket.OPEN;
  }

  async connect() {
    this.close();
    let lastError = new Error("Không thể kết nối WebSocket inference");
    for (const socketUrl of inferenceWebSocketUrls()) {
      try {
        await this.connectAt(socketUrl);
        setApiBaseFromSocket(socketUrl);
        return;
      } catch (error) {
        lastError = error;
        this.close();
      }
    }
    throw lastError;
  }

  connectAt(socketUrl) {
    return new Promise((resolve, reject) => {
      const socket = new WebSocket(socketUrl);
      this.socket = socket;
      let ready = false;
      const timeout = setTimeout(() => {
        if (ready) return;
        reject(new Error(`WebSocket không phản hồi cấu hình: ${socketUrl}`));
        socket.close();
      }, 3000);

      socket.addEventListener("open", () => this.updateConfiguration());
      socket.addEventListener("message", event => {
        if (this.socket !== socket) return;
        let message;
        try {
          message = JSON.parse(event.data);
        } catch {
          this.rejectOrFail(ready, reject, "Backend trả về WebSocket message không hợp lệ");
          return;
        }
        if (message.type === "configured") {
          clearTimeout(timeout);
          this.configured = true;
          ready = true;
          resolve();
        } else if (message.type === "inference_result") {
          this.awaitingResult = false;
          this.onResult(message);
        } else if (message.type === "error") {
          clearTimeout(timeout);
          this.awaitingResult = false;
          this.rejectOrFail(ready, reject, message.message || "WebSocket inference thất bại");
        }
      });
      socket.addEventListener("error", () => {
        if (!ready) {
          clearTimeout(timeout);
          reject(new Error(`Không thể kết nối WebSocket inference: ${socketUrl}`));
        }
      });
      socket.addEventListener("close", () => {
        clearTimeout(timeout);
        if (this.socket !== socket) return;
        this.socket = null;
        this.configured = false;
        this.awaitingResult = false;
        if (!ready) reject(new Error("WebSocket inference đã đóng trước khi sẵn sàng"));
        else this.onFailure("Mất kết nối WebSocket inference");
      });
    });
  }

  rejectOrFail(ready, reject, message) {
    if (!ready) reject(new Error(message));
    else this.onFailure(message);
  }

  updateConfiguration() {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
    const configuration = this.getConfiguration();
    if (configuration.zone_points.length !== 4) return;
    this.configured = false;
    this.socket.send(JSON.stringify({type: "configure", ...configuration}));
  }

  sendFrame({frameId, videoTime, blob}) {
    if (!this.canSend) return false;
    this.awaitingResult = true;
    this.socket.send(JSON.stringify({
      type: "frame_meta",
      frame_id: frameId,
      video_time: videoTime
    }));
    this.socket.send(blob);
    return true;
  }

  close() {
    const socket = this.socket;
    this.socket = null;
    this.configured = false;
    this.awaitingResult = false;
    if (socket && socket.readyState < WebSocket.CLOSING) socket.close();
  }
}
