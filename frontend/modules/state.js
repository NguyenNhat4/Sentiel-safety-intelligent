import {PREVIEW_CANDIDATES} from "./config.js";

export const state = {
  draggingPoint: null,
  frameSequence: 0,
  lastHandledFrame: -1,
  lastSampleTime: -1,
  latestPeople: [],
  pendingViolation: null,
  previewCandidateIndex: 0,
  previewCandidates: PREVIEW_CANDIDATES,
  previewReady: false,
  reviewStartedAt: null,
  running: false,
  selectedPoint: null,
  selectingZone: false,
  videoUrl: null,
  violationLatched: false,
  zonePoints: []
};

export function resetForVideo() {
  state.running = false;
  state.zonePoints = [];
  state.latestPeople = [];
  state.pendingViolation = null;
  state.violationLatched = false;
  state.previewReady = false;
  state.previewCandidateIndex = 0;
  state.selectedPoint = null;
  state.draggingPoint = null;
}

export function resetFrameSequence() {
  state.frameSequence = 0;
  state.lastHandledFrame = -1;
  state.lastSampleTime = -1;
}
