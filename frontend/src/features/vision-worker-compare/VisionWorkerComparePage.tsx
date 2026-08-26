import {useCallback, useEffect, useMemo, useRef, useState} from "react";

import {
  checkVisionWorker,
  inferVisionWorker,
  summarizeLatencies,
  type DetectionClass,
  type VisionWorkerHealth,
  type VisionWorkerInference,
  type VisionWorkerTarget
} from "../../api/vision-worker-compare";

const MAX_IMAGE_BYTES = 8 * 1024 * 1024;
const MAX_SAMPLES = 100;
const TARGETS: VisionWorkerTarget[] = ["cpu", "gpu"];
const BOX_COLORS: Record<DetectionClass, string> = {
  person: "#76e6c1",
  hat: "#ffd166",
  vest: "#78a9ff"
};

interface WorkerState {
  health: VisionWorkerHealth | null;
  result: VisionWorkerInference | null;
  samples: number[];
  error: string | null;
  busy: boolean;
}

const EMPTY_WORKER: WorkerState = {
  health: null,
  result: null,
  samples: [],
  error: null,
  busy: false
};

function readableError(error: unknown): string {
  if (error instanceof DOMException && error.name === "TimeoutError") {
    return "Worker không phản hồi trong 30 giây";
  }
  return error instanceof Error ? error.message : "Không thể kết nối tới worker";
}

function targetLabel(target: VisionWorkerTarget): string {
  return target === "cpu" ? "CPU" : "CUDA GPU";
}

function createSessionIds(): Record<VisionWorkerTarget, string> {
  const suffix = crypto.randomUUID().slice(0, 8);
  return {cpu: `compare-cpu-${suffix}`, gpu: `compare-gpu-${suffix}`};
}

function canvasJpeg(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) reject(new Error("Không thể mã hóa frame video thành JPEG"));
        else if (blob.size > MAX_IMAGE_BYTES) reject(new Error("Frame JPEG vượt quá giới hạn 8 MiB"));
        else resolve(blob);
      },
      "image/jpeg",
      0.86
    );
  });
}

function DetectionOverlay({
  result,
  width,
  height
}: {
  result: VisionWorkerInference | null;
  width: number;
  height: number;
}) {
  if (!result || width <= 0 || height <= 0) return null;
  return (
    <svg
      className="compare-overlay"
      viewBox={`0 0 ${width} ${height}`}
      aria-label={`${result.detections.length} detection boxes`}
    >
      {result.detections.map((detection, index) => {
        const [x1, y1, x2, y2] = detection.bbox;
        const label = `${detection.class_name} ${(detection.confidence * 100).toFixed(0)}%`;
        return (
          <g key={`${detection.class_name}-${index}`}>
            <rect
              x={x1}
              y={y1}
              width={x2 - x1}
              height={y2 - y1}
              stroke={BOX_COLORS[detection.class_name]}
            />
            <text x={x1 + 5} y={Math.max(18, y1 - 6)} fill={BOX_COLORS[detection.class_name]}>
              {label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function WorkerMetrics({target, state}: {target: VisionWorkerTarget; state: WorkerState}) {
  const summary = summarizeLatencies(state.samples);
  return (
    <article className={`worker-metrics ${target}`} aria-label={`Kết quả ${targetLabel(target)}`}>
      <header>
        <div>
          <p className="metric-kicker">{target === "cpu" ? "Baseline" : "Accelerated"}</p>
          <h2>{targetLabel(target)}</h2>
        </div>
        <span className={`worker-status ${state.busy ? "busy" : state.error ? "failed" : state.health ? "ready" : "idle"}`}>
          {state.busy ? "đang xử lý" : state.error ? "lỗi" : state.health ? "sẵn sàng" : "chưa kiểm tra"}
        </span>
      </header>

      <div className="headline-metric">
        <strong>{summary.latest === null ? "—" : summary.latest}</strong>
        <span>ms / frame gần nhất</span>
      </div>
      <dl className="metric-table">
        <div><dt>Trung bình</dt><dd>{summary.mean ?? "—"} ms</dd></div>
        <div><dt>p50</dt><dd>{summary.p50 ?? "—"} ms</dd></div>
        <div><dt>p95</dt><dd>{summary.p95 ?? "—"} ms</dd></div>
        <div><dt>Trần model</dt><dd>{summary.fps ?? "—"} FPS</dd></div>
        <div><dt>Mẫu thành công</dt><dd>{summary.count}</dd></div>
        <div><dt>Model</dt><dd title={state.result?.model_version ?? state.health?.model_version}>{state.result?.model_version ?? state.health?.model_version ?? "—"}</dd></div>
      </dl>

      {state.result ? (
        <div className="last-result">
          <span><strong>{state.result.canonical_people.length}</strong> người</span>
          <span><strong>{state.result.detections.length}</strong> boxes</span>
          <details>
            <summary>JSON cuối</summary>
            <pre>{JSON.stringify(state.result, null, 2)}</pre>
          </details>
        </div>
      ) : (
        <p className="metric-empty">Chưa có frame được xử lý.</p>
      )}
      {state.error && <p className="worker-error" role="alert">{state.error}</p>}
    </article>
  );
}

export function VisionWorkerComparePage() {
  const [apiKeys, setApiKeys] = useState<Record<VisionWorkerTarget, string>>({cpu: "", gpu: ""});
  const [sessions, setSessions] = useState(createSessionIds);
  const [workers, setWorkers] = useState<Record<VisionWorkerTarget, WorkerState>>({
    cpu: {...EMPTY_WORKER},
    gpu: {...EMPTY_WORKER}
  });
  const [file, setFile] = useState<File | null>(null);
  const [mediaKind, setMediaKind] = useState<"image" | "video" | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [mediaSize, setMediaSize] = useState({width: 0, height: 0});
  const [overlayTarget, setOverlayTarget] = useState<VisionWorkerTarget>("gpu");
  const [sampleRate, setSampleRate] = useState("2");
  const [sampling, setSampling] = useState(false);
  const [compareBusy, setCompareBusy] = useState(false);
  const [completedCycles, setCompletedCycles] = useState(0);
  const [skippedFrames, setSkippedFrames] = useState(0);
  const [pageError, setPageError] = useState<string | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const busyRef = useRef(false);
  const captureBusyRef = useRef(false);

  useEffect(
    () => () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    },
    [previewUrl]
  );

  const updateWorker = useCallback((target: VisionWorkerTarget, patch: Partial<WorkerState>) => {
    setWorkers((current) => ({...current, [target]: {...current[target], ...patch}}));
  }, []);

  const resetMeasurements = () => {
    setWorkers((current) => ({
      cpu: {...current.cpu, result: null, samples: [], error: null, busy: false},
      gpu: {...current.gpu, result: null, samples: [], error: null, busy: false}
    }));
    setCompletedCycles(0);
    setSkippedFrames(0);
    setSessions(createSessionIds());
  };

  const selectFile = (nextFile: File | undefined) => {
    setSampling(false);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setFile(null);
    setMediaKind(null);
    setMediaSize({width: 0, height: 0});
    setPageError(null);
    resetMeasurements();
    if (!nextFile) return;

    const nextKind = nextFile.type.startsWith("video/") ? "video" : nextFile.type === "image/jpeg" ? "image" : null;
    if (!nextKind) {
      setPageError("Chỉ chấp nhận ảnh JPEG hoặc file video mà trình duyệt phát được");
      return;
    }
    if (nextKind === "image" && nextFile.size > MAX_IMAGE_BYTES) {
      setPageError("Ảnh JPEG vượt quá giới hạn 8 MiB của worker");
      return;
    }
    setFile(nextFile);
    setMediaKind(nextKind);
    setPreviewUrl(URL.createObjectURL(nextFile));
  };

  const checkBothWorkers = async () => {
    setPageError(null);
    await Promise.all(
      TARGETS.map(async (target) => {
        updateWorker(target, {busy: true, error: null});
        try {
          updateWorker(target, {health: await checkVisionWorker(target), busy: false});
        } catch (error) {
          updateWorker(target, {health: null, error: readableError(error), busy: false});
        }
      })
    );
  };

  const compareFrame = useCallback(async (image: Blob, fileName = "video-frame.jpg") => {
    if (busyRef.current) {
      setSkippedFrames((value) => value + 1);
      return;
    }
    busyRef.current = true;
    setCompareBusy(true);
    setPageError(null);

    await Promise.all(
      TARGETS.map(async (target) => {
        updateWorker(target, {busy: true, error: null});
        const startedAt = performance.now();
        try {
          const result = await inferVisionWorker(target, {
            image,
            fileName,
            apiKey: apiKeys[target],
            monitoringSessionId: sessions[target]
          });
          const latency = Math.round(performance.now() - startedAt);
          setWorkers((current) => ({
            ...current,
            [target]: {
              ...current[target],
              result,
              samples: [...current[target].samples, latency].slice(-MAX_SAMPLES),
              error: null,
              busy: false
            }
          }));
        } catch (error) {
          updateWorker(target, {error: readableError(error), busy: false});
        }
      })
    );
    setCompletedCycles((value) => value + 1);
    busyRef.current = false;
    setCompareBusy(false);
  }, [apiKeys, sessions, updateWorker]);

  const compareImage = async () => {
    if (!file || mediaKind !== "image") return;
    await compareFrame(file, file.name);
  };

  const captureVideoFrame = useCallback(async (): Promise<Blob> => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
      throw new Error("Video chưa sẵn sàng để lấy frame");
    }
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Trình duyệt không hỗ trợ canvas 2D");
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvasJpeg(canvas);
  }, []);

  useEffect(() => {
    if (!sampling || mediaKind !== "video") return;
    const intervalMs = 1000 / Number(sampleRate);
    const tick = async () => {
      if (!videoRef.current || videoRef.current.paused || videoRef.current.ended) return;
      if (busyRef.current || captureBusyRef.current) {
        setSkippedFrames((value) => value + 1);
        return;
      }
      captureBusyRef.current = true;
      try {
        await compareFrame(await captureVideoFrame());
      } catch (error) {
        setPageError(readableError(error));
      } finally {
        captureBusyRef.current = false;
      }
    };
    void tick();
    const timer = window.setInterval(() => void tick(), intervalMs);
    return () => window.clearInterval(timer);
  }, [sampling, mediaKind, sampleRate, compareFrame, captureVideoFrame]);

  const startSampling = () => {
    if (mediaKind !== "video") return;
    setPageError(null);
    void videoRef.current?.play().catch(() => undefined);
    setSampling(true);
  };

  const cpuSummary = useMemo(() => summarizeLatencies(workers.cpu.samples), [workers.cpu.samples]);
  const gpuSummary = useMemo(() => summarizeLatencies(workers.gpu.samples), [workers.gpu.samples]);
  const speedup = cpuSummary.mean && gpuSummary.mean ? cpuSummary.mean / gpuSummary.mean : null;
  const activeResult = workers[overlayTarget].result;

  return (
    <main className="compare-lab">
      <header className="compare-header">
        <div>
          <p className="lab-eyebrow">P-047 · local performance probe</p>
          <h1>CPU <span>/</span> CUDA</h1>
          <p>Cùng một frame, hai worker, số đo browser-to-model có thể nhìn thấy ngay.</p>
        </div>
        <div className="contract-badge"><i /> safety_vision_v1</div>
      </header>

      <section className="compare-shell">
        <aside className="compare-controls" aria-label="Cấu hình benchmark">
          <div className="section-label"><span>01</span><div><h2>Kết nối</h2><p>Vite proxy cục bộ</p></div></div>
          <label>
            CPU worker API key
            <input
              aria-label="CPU worker API key"
              type="password"
              value={apiKeys.cpu}
              onChange={(event) => setApiKeys((current) => ({...current, cpu: event.target.value}))}
              placeholder="Để trống nếu không bật auth"
              autoComplete="off"
            />
          </label>
          <label>
            GPU worker API key
            <input
              aria-label="GPU worker API key"
              type="password"
              value={apiKeys.gpu}
              onChange={(event) => setApiKeys((current) => ({...current, gpu: event.target.value}))}
              placeholder="Để trống nếu không bật auth"
              autoComplete="off"
            />
          </label>
          <button className="button secondary" type="button" onClick={checkBothWorkers}>
            Kiểm tra cả hai worker
          </button>

          <div className="control-divider" />
          <div className="section-label"><span>02</span><div><h2>Media đầu vào</h2><p>JPEG hoặc video local</p></div></div>
          <label className="media-picker">
            <input
              aria-label="Chọn ảnh hoặc video"
              type="file"
              accept="image/jpeg,.jpg,.jpeg,video/*"
              onChange={(event) => selectFile(event.target.files?.[0])}
            />
            <span>{file ? file.name : "Chọn ảnh / video"}</span>
            <small>{file ? `${(file.size / 1024 / 1024).toFixed(2)} MiB · ${mediaKind}` : "Không upload cả video lên server"}</small>
          </label>

          {mediaKind === "video" && (
            <label>
              Tần suất lấy mẫu
              <select aria-label="Tần suất lấy mẫu" value={sampleRate} onChange={(event) => setSampleRate(event.target.value)}>
                <option value="1">1 FPS</option>
                <option value="2">2 FPS · giống production</option>
                <option value="5">5 FPS</option>
                <option value="10">10 FPS · stress</option>
              </select>
            </label>
          )}

          {mediaKind === "image" && (
            <button className="button primary" type="button" onClick={compareImage} disabled={compareBusy}>
              {compareBusy ? "Hai model đang chạy…" : "So sánh 1 frame"}
            </button>
          )}
          {mediaKind === "video" && (
            <button className={`button ${sampling ? "danger" : "primary"}`} type="button" onClick={sampling ? () => setSampling(false) : startSampling}>
              {sampling ? "Dừng đo video" : "Bắt đầu đo video"}
            </button>
          )}
          <button className="button ghost" type="button" onClick={resetMeasurements} disabled={!completedCycles && !skippedFrames}>
            Xóa số đo
          </button>
          {pageError && <p className="page-error" role="alert">{pageError}</p>}
          <p className="privacy-note">Video chỉ phát trong trình duyệt. Mỗi lần worker chỉ nhận một frame JPEG; API key không được lưu.</p>
        </aside>

        <section className="compare-workspace" aria-label="Media và kết quả benchmark">
          <div className="media-panel">
            <div className="media-toolbar">
              <div><p className="lab-eyebrow">Live probe</p><h2>Khung hình đang đo</h2></div>
              <div className="overlay-switch" aria-label="Chọn overlay">
                {TARGETS.map((target) => (
                  <button key={target} className={overlayTarget === target ? "active" : ""} type="button" onClick={() => setOverlayTarget(target)}>
                    {targetLabel(target)}
                  </button>
                ))}
              </div>
            </div>
            <div className={`media-stage ${previewUrl ? "loaded" : ""}`}>
              {previewUrl && mediaKind === "image" && (
                <div className="media-layer">
                  <img
                    src={previewUrl}
                    alt="Ảnh đang benchmark"
                    onLoad={(event) => setMediaSize({width: event.currentTarget.naturalWidth, height: event.currentTarget.naturalHeight})}
                  />
                  <DetectionOverlay result={activeResult} width={mediaSize.width} height={mediaSize.height} />
                </div>
              )}
              {previewUrl && mediaKind === "video" && (
                <div className="media-layer">
                  <video
                    ref={videoRef}
                    src={previewUrl}
                    controls
                    muted
                    playsInline
                    onLoadedMetadata={(event) => setMediaSize({width: event.currentTarget.videoWidth, height: event.currentTarget.videoHeight})}
                    onEnded={() => setSampling(false)}
                  />
                  <DetectionOverlay result={activeResult} width={mediaSize.width} height={mediaSize.height} />
                </div>
              )}
              {!previewUrl && (
                <div className="media-empty"><span>+</span><strong>Chưa có media</strong><p>Chọn JPEG hoặc video để bắt đầu.</p></div>
              )}
            </div>
            <canvas ref={canvasRef} className="capture-canvas" aria-hidden="true" />
            <div className="run-strip" aria-live="polite">
              <span className={sampling ? "run-light active" : "run-light"} />
              <div><small>Trạng thái</small><strong>{sampling ? `Đang lấy mẫu ${sampleRate} FPS` : compareBusy ? "Đang so sánh frame" : "Đang chờ"}</strong></div>
              <div><small>Chu kỳ hoàn tất</small><strong>{completedCycles}</strong></div>
              <div><small>Frame bỏ qua</small><strong className={skippedFrames ? "warning" : ""}>{skippedFrames}</strong></div>
              <div><small>GPU speedup</small><strong>{speedup ? `${speedup.toFixed(2)}×` : "—"}</strong></div>
            </div>
          </div>

          <section className="metrics-grid" aria-label="So sánh CPU và GPU">
            <WorkerMetrics target="cpu" state={workers.cpu} />
            <WorkerMetrics target="gpu" state={workers.gpu} />
          </section>

          <footer className="compare-note">
            <strong>Cách đọc:</strong> RTT gồm mã hóa JPEG + Vite proxy + network + model. “Trần model” là 1000 / latency trung bình, không phải FPS camera thực tế. GPU speedup lớn hơn 1× nghĩa là GPU nhanh hơn.
          </footer>
        </section>
      </section>
    </main>
  );
}
