import {AlertPanel} from "../alerts/AlertPanel";
import {useMonitor} from "./use-monitor";

export function MonitorPage() {
  const {refs, state, actions} = useMonitor();
  const zoneHint = state.zonePoints.length === 4
    ? "Vùng đã sẵn sàng · Kéo điểm để điều chỉnh"
    : `Chọn 4 điểm · ${state.zonePoints.length}/4`;
  const deleteStyle = state.selectedPointPosition
    ? {left: `${state.selectedPointPosition.x * 100}%`, top: `${state.selectedPointPosition.y * 100}%`}
    : undefined;

  return (
    <section className="page active" id="monitor">
      <div className="toolbar">
        <div className="camera-select">
          <span className="camera-icon">●</span>
          <div><small>VIDEO ĐANG XEM</small><strong>{state.fileLabel}</strong></div>
          <span>⌄</span>
        </div>
        <div className="machine-control">
          <div><small>MACHINE A</small><strong>{state.machineRunning ? "Đang hoạt động" : "Đã dừng"}</strong></div>
          <button className={`switch ${state.machineRunning ? "on" : ""}`} aria-label="Chuyển trạng thái máy" onClick={actions.toggleMachine}><span /></button>
        </div>
        <input ref={refs.fileInputRef} type="file" accept="video/*" hidden onChange={actions.handleVideoSelection} />
        <button className="secondary-btn" onClick={actions.openFilePicker}>＋ Tải video</button>
        <button className="secondary-btn" disabled={state.playbackDisabled} onClick={() => void actions.handlePlayback()}>{state.playbackLabel}</button>
        <button className={`secondary-btn ${state.selectingZone ? "zone-config-active" : ""}`} disabled={state.zoneDisabled} onClick={actions.toggleZoneEditing}>
          {state.selectingZone ? "✓ Xong cấu hình" : "⌗ Cấu hình vùng"}
        </button>
      </div>

      <div className="monitor-grid">
        <article className="video-card">
          <div className="video-head">
            <span><i className="live-dot" /> VIDEO</span>
            <p>{state.videoMeta}</p>
            <button onClick={actions.resetZone} title="Xóa vùng">↺</button>
          </div>
          <div className={`camera-scene ${state.stageReady ? "ready" : ""}`}>
            <video ref={refs.videoRef} className="uploaded-media active" preload="auto" playsInline muted
              onLoadedMetadata={actions.handleLoadedMetadata} onSeeked={actions.handleSeeked} onEnded={actions.handleEnded} />
            {state.previewSrc && <img className="video-preview" src={state.previewSrc} alt="Khung hình đầu tiên của video" />}
            <canvas ref={refs.overlayRef} onPointerDown={actions.handlePointerDown} onPointerMove={actions.handlePointerMove} onPointerUp={actions.handlePointerUp} />
            {state.selectedPointPosition && <button className="point-delete" style={deleteStyle} title="Xóa điểm đã chọn" onClick={actions.deleteSelectedPoint}>×</button>}
            <div className="scene-glow" />
            <div className="machine machine-left"><span /><span /></div>
            <div className="machine machine-right"><span /><span /></div>
            <div className="danger-zone"><b>KHU VỰC NGUY HIỂM</b></div>
            <div className="person-box">
              <div className="person"><div className="head"><span className="blur" /></div><div className="body" /><div className="leg l" /><div className="leg r" /></div>
              <span className="corner tl" /><span className="corner tr" /><span className="corner bl" /><span className="corner br" />
              <label>PERSON · 96%</label><em>NO SAFETY SHIRT</em>
            </div>
            {!state.stageReady && <div className="empty-state"><strong>Tải video demo</strong><span>Sau đó chọn 4 điểm để tạo vùng nguy hiểm.</span></div>}
            <div className="zone-hint">{state.stageReady ? zoneHint : "Chưa cấu hình vùng"}</div>
          </div>
          <footer>
            <span><i /> AI Detection</span>
            <span>{state.peopleCount} người</span>
            <span>1 áo bảo hộ yêu cầu</span>
            <strong className={state.view.violation ? "result-violate" : "result-normal"}>{state.view.violation ? "● VIOLATE" : state.stageReady ? "● NORMAL" : "● Chờ video"}</strong>
          </footer>
        </article>

        <AlertPanel view={state.view} reviewPending={Boolean(state.pendingViolation)} reviewSaving={state.reviewSaving}
          snapshot={state.pendingViolation?.snapshot_data} timer={state.timer} onReview={status => void actions.review(status)} />
      </div>

      <div className="activity-strip">
        <div><span className="activity-icon">⚠</span><p><small>LUỒNG BASELINE</small><strong>Upload video → Chọn vùng → Phát + inference realtime → Xác minh → Lưu</strong></p></div>
        <span>ONE ZONE</span><span className="medium-pill">ONE PPE</span>
        <span>{state.flowStatus}</span>
        <button onClick={actions.openFilePicker}>Bắt đầu bằng video →</button>
      </div>

      <canvas ref={refs.captureRef} hidden />
      <div className={`toast ${state.toast ? "show" : ""}`}><span>✓</span><div><strong>Sentinel</strong><p>{state.toast}</p></div></div>
    </section>
  );
}
