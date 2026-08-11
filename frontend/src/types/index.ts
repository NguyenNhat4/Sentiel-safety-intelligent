export type MachineState = "running" | "stopped";
export type ReviewStatus = "acknowledged" | "false_alarm";

export interface ZonePoint {
  x: number;
  y: number;
}

export interface MonitoringZone {
  zone_id: string;
  display_name: string;
  points: ZonePoint[];
  machine_state: MachineState;
  enabled: boolean;
  order: number;
}

export interface MonitoringZoneCollection {
  camera_id: string;
  revision: number;
  zones: MonitoringZone[];
  updated_at: string | null;
}

export interface PersonDetection {
  track_id?: number;
  bbox: [number, number, number, number];
  confidence: number;
  foot_point?: [number, number];
  inside_zone: boolean;
  zone_memberships?: ZoneMembership[];
  safety_shirt: boolean;
  ppe: {
    helmet: PpeObservation;
    safety_glasses: PpeObservation;
    gloves: PpeObservation;
  };
  missing_required_ppe: Array<"helmet" | "safety_glasses" | "gloves">;
  active_violations?: ActiveViolation[];
}

export interface ActiveViolation {
  occurrence_id: string;
  rule_key: string;
  zone_id?: string | null;
  is_new: boolean;
}

export interface ZoneMembership {
  zone_id: string;
  inside: boolean;
}

export interface ZoneResult {
  zone_id: string;
  machine_state: MachineState;
  person_inside_zone: boolean;
  violation: boolean;
}

export interface PpeObservation {
  status: "present" | "missing" | "unknown";
  confidence: number | null;
}

export interface ModelDetection {
  class_id: number;
  class_name: string;
  bbox: [number, number, number, number];
  confidence: number;
  person_index: number | null;
}

export interface InferenceRule {
  person_inside_zone: boolean;
  machine_state: MachineState;
  safety_shirt_required: boolean;
  camera_id: string;
  zone_id: string;
  ppe_requirements: PpeRequirementUpdate;
  ppe_alert: boolean;
  zone_revision?: number | null;
  zone_results?: ZoneResult[];
}

export interface InferenceResult {
  type: "inference_result";
  frame_id: number;
  video_time: number;
  result: "normal" | "violate";
  review_required: boolean;
  has_active_violation?: boolean;
  monitoring_session_id?: string;
  people: PersonDetection[];
  detections?: ModelDetection[];
  snapshot_data?: string;
  rule: InferenceRule;
}

export interface SafetyEvent {
  id: number;
  timestamp: string;
  zone_id: string;
  camera_id: string;
  event_type: string;
  severity: string;
  status: ReviewStatus;
  acknowledged_by?: string | null;
  snapshot_path?: string | null;
  details?: {
    people?: PersonDetection[];
    video_timestamp_seconds?: number;
    review_result?: string;
  };
  monitoring_session_id?: string | null;
  occurrence_ids?: string[];
  batch_id?: string | null;
}

export interface EventBatchItem {
  zone_id: string;
  event_type: "zone_intrusion";
  severity: string;
  occurrence_ids: string[];
  details: Record<string, unknown>;
}

export interface EventBatchPayload {
  monitoring_session_id: string;
  camera_id: string;
  status: ReviewStatus;
  acknowledged_by: string;
  snapshot_data?: string;
  snapshot_people?: PersonDetection[];
  snapshot_detections?: ModelDetection[];
  events: EventBatchItem[];
}

export interface EventBatchResponse {
  batch_id: string;
  snapshot_path?: string | null;
  events: SafetyEvent[];
}

export interface EventPayload {
  zone_id: string;
  camera_id: string;
  event_type: string;
  severity: string;
  status: ReviewStatus;
  acknowledged_by: string;
  snapshot_data?: string;
  snapshot_people?: PersonDetection[];
  snapshot_detections?: ModelDetection[];
  details: Record<string, unknown>;
  monitoring_session_id?: string;
  occurrence_ids: string[];
}

export interface PpeRequirementUpdate {
  helmet_required: boolean;
  safety_glasses_required: boolean;
  gloves_required: boolean;
}

export interface PpeRequirement extends PpeRequirementUpdate {
  camera_id: string;
  zone_id: string;
  is_configured: boolean;
  updated_at: string | null;
}
