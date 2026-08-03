import type {InferenceResult, MachineState, ZonePoint} from "../types";
import {inferenceWebSocketUrls, setBackendFromSocket} from "./config";

interface Configuration {
  zone_points: ZonePoint[];
  machine_state: MachineState;
}

interface InferenceClientOptions {
  getConfiguration: () => Configuration;
  onResult: (result: InferenceResult) => void;
  onFailure: (message: string) => void;
  socketFactory?: (url: string) => WebSocket;
}

type ServerMessage = InferenceResult | {type: "configured"} | {type: "error"; message?: string};

export class InferenceClient {
  private socket: WebSocket | null = null;
  private configured = false;
  private awaitingResult = false;
  private readonly socketFactory: (url: string) => WebSocket;

  constructor(private readonly options: InferenceClientOptions) {
    this.socketFactory = options.socketFactory ?? (url => new WebSocket(url));
  }

  get canSend(): boolean {
    return this.configured && !this.awaitingResult && this.socket?.readyState === WebSocket.OPEN;
  }

  async connect(): Promise<void> {
    this.close();
    let lastError = new Error("Không thể kết nối WebSocket inference");
    for (const socketUrl of inferenceWebSocketUrls()) {
      try {
        await this.connectAt(socketUrl);
        setBackendFromSocket(socketUrl);
        return;
      } catch (error) {
        lastError = error instanceof Error ? error : lastError;
        this.close();
      }
    }
    throw lastError;
  }

  updateConfiguration(): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
    const configuration = this.options.getConfiguration();
    if (configuration.zone_points.length !== 4) return;
    this.configured = false;
    this.socket.send(JSON.stringify({type: "configure", ...configuration}));
  }

  sendFrame(frameId: number, videoTime: number, blob: Blob): boolean {
    if (!this.canSend || !this.socket) return false;
    this.awaitingResult = true;
    this.socket.send(JSON.stringify({type: "frame_meta", frame_id: frameId, video_time: videoTime}));
    this.socket.send(blob);
    return true;
  }

  close(): void {
    const socket = this.socket;
    this.socket = null;
    this.configured = false;
    this.awaitingResult = false;
    if (socket && socket.readyState < WebSocket.CLOSING) socket.close();
  }

  private connectAt(socketUrl: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const socket = this.socketFactory(socketUrl);
      this.socket = socket;
      let ready = false;
      const timeout = window.setTimeout(() => {
        if (ready) return;
        reject(new Error(`WebSocket không phản hồi cấu hình: ${socketUrl}`));
        socket.close();
      }, 3000);

      socket.addEventListener("open", () => this.updateConfiguration());
      socket.addEventListener("message", event => {
        if (this.socket !== socket) return;
        let message: ServerMessage;
        try {
          message = JSON.parse(String(event.data)) as ServerMessage;
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
          this.options.onResult(message);
        } else {
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
        else this.options.onFailure("Mất kết nối WebSocket inference");
      });
    });
  }

  private rejectOrFail(ready: boolean, reject: (reason: Error) => void, message: string): void {
    if (!ready) reject(new Error(message));
    else this.options.onFailure(message);
  }
}
