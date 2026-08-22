import type {StreamConfiguration, StreamMapping} from "../../types";

export function normalizeMappings(configuration: StreamConfiguration): StreamMapping[] {
  return (configuration.mappings ?? (configuration.active_camera_id ? [{camera_id: "cam_1", stream_camera_id: configuration.active_camera_id, machine_state: "stopped"}] : []))
    .map(mapping => ({...mapping, machine_state: mapping.machine_state ?? "stopped"}));
}

export function sameMappings(left: StreamMapping[], right: StreamMapping[]): boolean {
  if (left.length !== right.length) return false;
  const byCamera = new Map(left.map(mapping => [mapping.camera_id, mapping.stream_camera_id]));
  return right.every(mapping => byCamera.get(mapping.camera_id) === mapping.stream_camera_id);
}

export function changedCameraIds(left: StreamMapping[], right: StreamMapping[]): string[] {
  const previous = new Map(left.map(mapping => [mapping.camera_id, mapping.stream_camera_id]));
  const next = new Map(right.map(mapping => [mapping.camera_id, mapping.stream_camera_id]));
  return [...new Set([...previous.keys(), ...next.keys()])].filter(cameraId => previous.get(cameraId) !== next.get(cameraId));
}
