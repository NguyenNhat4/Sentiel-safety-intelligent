import {AlertPanel} from "../alerts/AlertPanel";
import {ReviewModal} from "../alerts/ReviewModal";
import {PpeRequirementsPanel} from "../rules/PpeRequirementsPanel";
import {useMonitor} from "./use-monitor";

export function MonitorPage() {
  const {refs, state, actions} = useMonitor();
  const zoneHint = state.selectedZone
    ? `${state.selectedZone.display_name} · ${state.selectedZone.points.length}/4${state.drawingZoneId ? " · đang vẽ" : " · kéo điểm để chỉnh"}`
    : "Chưa có vùng · bấm Tạo vùng để bắt đầu";
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
          <div><small>VÙNG ĐANG CHỌN</small><strong>{state.selectedZone ? (state.machineRunning ? "Đang hoạt động" : "Đã dừng") : "Chưa chọn vùng"}</strong></div>
          <button className={`switch ${state.machineRunning ? "on" : ""}`} aria-label="Chuyển trạng thái máy của vùng đang chọn" disabled={!state.selectedZone} onClick={actions.toggleMachine}><span /></button>
        </div>
        <input ref={refs.fileInputRef} type="file" accept="video/*" hidden onChange={actions.handleVideoSelection} />
        <button className="secondary-btn" disabled={!state.selectedZone} onClick={actions.openFilePicker}>＋ Tải video</button>
        <button className="secondary-btn" disabled={state.playbackDisabled} onClick={() => void actions.handlePlayback()}>{state.playbackLabel}</button>
        <button className="secondary-btn zone-create-btn" disabled={!state.zoneHydrated || Boolean(state.drawingZoneId)} onClick={actions.createZone}>＋ Tạo vùng</button>
      </div>

      <PpeRequirementsPanel cameraId="uploaded_video" zoneId={state.selectedZoneId ?? "zone_01"} />

      <section className="zone-manager" aria-label="Cấu hình vùng nguy hiểm">
        <div className="zone-manager-head">
          <div><small>VÙNG NGUY HIỂM · REVISION {state.zoneRevision}</small><strong>{state.zones.length} vùng đã cấu hình</strong></div>
          <div>
            {state.newDraftZoneId && <button className="secondary-btn" onClick={actions.cancelZoneCreation}>Hủy tạo vùng</button>}
            <button className="ppe-save-button" disabled={state.zoneSaving || Boolean(state.drawingZoneId)} onClick={() => void actions.saveZones()}>
              {state.zoneSaving ? "Đang lưu…" : "Lưu cấu hình vùng"}
            </button>
          </div>
        </div>
        <div className="zone-list">
          {state.zones.map(zone => (
            <button key={zone.zone_id} className={`zone-list-item ${state.selectedZoneId === zone.zone_id ? "selected" : ""}`} onClick={() => actions.selectZone(zone.zone_id)}>
              <span>{zone.order + 1}</span><strong>{zone.display_name}</strong><small>{zone.points.length}/4 · {zone.enabled ? "BẬT" : "TẮT"} · {zone.machine_state === "running" ? "RUN" : "STOP"}</small>
            </button>
          ))}
          {!state.zones.length && <p className="zone-empty">Canvas không tự tạo vùng. Hãy bấm <strong>Tạo vùng</strong>.</p>}
        </div>
        {state.selectedZone && (
          <div className="zone-fields">
            <label>Tên vùng<input value={state.selectedZone.display_name} maxLength={100} onChange={event => actions.updateSelectedZoneName(event.target.value)} /></label>
            <label className="zone-enabled"><input type="checkbox" checked={state.selectedZone.enabled} onChange={actions.toggleSelectedZoneEnabled} /> Bật inference cho vùng</label>
            <div className="zone-field-actions">
              <span>ID: {state.selectedZone.zone_id}</span>
              <button
                type="button"
                className="zone-delete-button"
                aria-label={`Xóa vùng ${state.selectedZone.display_name}`}
                disabled={state.zoneSaving}
                onClick={actions.deleteSelectedZone}
              >
                Xóa vùng
              </button>
            </div>
          </div>
        )}
      </section>

      <div className="monitor-grid">
        <article className="video-card">
          <div className="video-head">
            <span><i className="live-dot" /> VIDEO</span>
            <p>{state.videoMeta}</p>
            <button onClick={actions.resetZone} disabled={!state.selectedZone} title="Vẽ lại vùng đang chọn">↺</button>
          </div>
          {(state.pendingReviewCounts.critical > 0 || state.pendingReviewCounts.other > 0) && <div className="video-alert-summary" role="status">
            <strong>{state.pendingReviewCounts.critical} log nghiêm trọng cần review</strong>
            <span>· {state.pendingReviewCounts.other} log PPE cần review</span>
          </div>}
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
              <label>PERSON · 96%</label><em>PPE CHECK</em>
            </div>
            {!state.stageReady && <div className="empty-state"><strong>Tải video demo</strong><span>Phát video để xem detection; zone 4 điểm là tùy chọn.</span></div>}
            <div className="zone-hint">{state.stageReady ? zoneHint : "Chưa tải video"}</div>
          </div>
          <footer>
            <span><i /> AI Detection</span>
            <span>{state.peopleCount} người</span>
            <span>{state.ppeRequirementCount} PPE bắt buộc</span>
            <strong className={state.view.violation ? "result-violate" : "result-normal"}>{state.view.violation ? "● VIOLATE" : state.stageReady ? "● NORMAL" : "● Chờ video"}</strong>
          </footer>
        </article>

        <AlertPanel
          view={state.view}
          hitlLogs={state.hitlLogs}
          people={state.latestPeople}
          detections={state.latestDetections}
          onOpenModal={actions.openReviewLog}
        />
      </div>

      <ReviewModal
        isOpen={state.isReviewModalOpen}
        onClose={actions.closeReviewModal}
        snapshot={state.pendingViolation?.snapshot_data}
        people={state.pendingViolation?.people}
        detections={state.pendingViolation?.detections}
        timer={state.timer}
        reviewSaving={state.reviewSaving}
        alertTitle={state.view.alertTitle}
        alertSummary={state.view.alertSummary}
        onReview={status => void actions.review(status)}
      />

      <div className="activity-strip">
        <div><span className="activity-icon">⚠</span><p><small>LUỒNG BASELINE</small><strong>Upload video → Chọn vùng → Phát + inference realtime → Xác minh → Lưu</strong></p></div>
        <span>MULTI ZONE</span><span className="medium-pill">PPE · HAT / VEST</span>
        <span>{state.flowStatus}</span>
        <button onClick={actions.openFilePicker}>Bắt đầu bằng video →</button>
      </div>

      <canvas ref={refs.captureRef} hidden />
      <div className={`toast ${state.toast ? "show" : ""}`}><span>✓</span><div><strong>Sentinel</strong><p>{state.toast}</p></div></div>
    </section>
  );
}
