import type {CameraInferenceResult} from "../types";
import {cameraDetectionWebSocketUrls} from "./config";

interface Options {
  accessToken: string;
  cameraIds: string[];
  onResult: (result: CameraInferenceResult) => void;
  onFailure: (message: string) => void;
  socketFactory?: (url: string) => WebSocket;
  socketUrls?: string[];
}

export class CameraDetectionClient {
  private socket: WebSocket | null = null;
  private readonly socketFactory: (url: string) => WebSocket;

  constructor(private readonly options: Options) {
    this.socketFactory = options.socketFactory ?? (url => new WebSocket(url));
  }

  async connect(): Promise<void> {
    this.close();
    let lastError = new Error("Không thể kết nối detection camera");
    for (const url of this.options.socketUrls ?? cameraDetectionWebSocketUrls()) {
      try {
        await this.connectAt(url);
        return;
      } catch (reason) {
        lastError = reason instanceof Error ? reason : lastError;
        this.close();
      }
    }
    throw lastError;
  }

  close(): void {
    const socket = this.socket;
    this.socket = null;
    if (socket && socket.readyState < WebSocket.CLOSING) socket.close();
  }

  private connectAt(url: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const socket = this.socketFactory(url);
      this.socket = socket;
      let subscribed = false;
      const timeout = window.setTimeout(() => reject(new Error("Backend không xác nhận detection subscription")), 5000);
      socket.addEventListener("open", () => socket.send(JSON.stringify({
        type: "authenticate",
        access_token: this.options.accessToken,
        camera_ids: this.options.cameraIds,
      })));
      socket.addEventListener("message", event => {
        if (this.socket !== socket) return;
        try {
          const message = JSON.parse(String(event.data)) as CameraInferenceResult | {type: "subscribed"} | {type: "error"; message?: string};
          if (message.type === "subscribed") {
            subscribed = true;
            window.clearTimeout(timeout);
            resolve();
          } else if (message.type === "camera_inference_result") {
            this.options.onResult(message);
          } else {
            const detail = message.message || "Detection subscription thất bại";
            if (subscribed) this.options.onFailure(detail); else reject(new Error(detail));
          }
        } catch {
          if (subscribed) this.options.onFailure("Detection message không hợp lệ");
          else reject(new Error("Detection message không hợp lệ"));
        }
      });
      socket.addEventListener("error", () => {
        window.clearTimeout(timeout);
        if (!subscribed) reject(new Error("Không thể mở detection WebSocket"));
      });
      socket.addEventListener("close", () => {
        window.clearTimeout(timeout);
        if (this.socket !== socket) return;
        this.socket = null;
        if (subscribed) this.options.onFailure("Mất kết nối detection camera");
        else reject(new Error("Detection WebSocket đóng trước khi sẵn sàng"));
      });
    });
  }
}
