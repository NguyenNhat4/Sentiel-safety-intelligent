import {dom} from "./modules/dom.js";
import {createEventLogController} from "./modules/event-log-controller.js";
import {InferenceClient} from "./modules/inference-client.js";
import {createReviewController} from "./modules/review-controller.js";
import {state} from "./modules/state.js";
import {startClock} from "./modules/ui.js";
import {createVideoController} from "./modules/video-controller.js";
import {initializeZoneController} from "./modules/zone-controller.js";

let videoController;
const eventLogController = createEventLogController();
const reviewController = createReviewController({
  onZoneEntry: videoTime => videoController.pauseForReview(videoTime)
});

const inferenceClient = new InferenceClient({
  getConfiguration: () => ({
    zone_points: state.zonePoints,
    machine_state: dom.machineSwitch.classList.contains("on") ? "running" : "stopped"
  }),
  onResult: result => reviewController.handleInferenceResult(result),
  onFailure: message => videoController.handleInferenceFailure(message)
});

videoController = createVideoController({inferenceClient});
eventLogController.initialize();
videoController.initialize();
initializeZoneController({
  stopRealtimeInference: videoController.stopRealtimeInference,
  stopPreviewPlayback: videoController.stopPreviewPlayback
});
startClock();
