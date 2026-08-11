# Live Monitor

Owns local video playback, normalized four-point zone editing, frame sampling, Canvas overlays, and orchestration of inference/review state. On violation it pauses, seeks to the result timestamp, waits for the stopped video frame to render, and captures that full native frame for review/persistence. When a review is saved, it forwards that frame's typed people/SH17 boxes as transient snapshot-annotation metadata; these do not affect the safety decision.
