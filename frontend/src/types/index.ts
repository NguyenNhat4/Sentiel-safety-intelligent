export type MachineState = "running" | "stopped";
export type ReviewStatus = "acknowledged" | "false_alarm";
export type EventStatus = ReviewStatus | "unacknowledged" | "resolved";
export type UserRole = "system_admin" | "safety_manager" | "area_manager";
export type AssignableUserRole = UserRole;

export interface AuthenticatedUser { id: string; full_name: string; email: string; role: UserRole; role_label: string; must_change_password: boolean; managed_area_id?: string | null; managed_camera_ids?: string[]; telegram_username?: string | null; telegram_chat_id?: string | null; }
export type MediaType = "video" | "image";
export type MediaAssetStatus = "UPLOADING" | "READY" | "ERROR";
export type MediaStorageBackend = "filesystem" | "s3";
export type CameraSessionStatus = "STARTING" | "RUNNING" | "COMPLETED" | "ERROR" | "STOPPED";

export interface MediaAsset {
  id: string;
  display_name: string;
  media_type: MediaType;
  status: MediaAssetStatus;
  content_type: string;
  size_bytes: number;
  storage_backend: MediaStorageBackend;
  uploaded_at: string;
  assigned_camera_id: string | null;
  can_delete?: boolean;
  error_message?: string | null;
}

export interface CameraConfigurationZone extends MonitoringZone { ppe_requirements: PpeRequirementUpdate; }

export interface CameraConfiguration {
  camera_id: string;
  camera_name?: string | null;
  revision: number;
  asset_id: string | null;
  machine_state: MachineState;
  ppe_requirements: PpeRequirementUpdate;
  zones: CameraConfigurationZone[];
  updated_at: string | null;
}

export interface CameraConfigurationUpdate {
  expected_revision: number;
  asset_id: string | null;
  machine_state: MachineState;
  ppe_requirements: PpeRequirementUpdate;
  zones: CameraConfigurationZone[];
}

export interface CameraSession {
  id: string;
  camera_id: string;
  asset_id: string;
  media_type: MediaType;
  status: CameraSessionStatus;
  config_revision: number;
  inference_fps: number;
  started_at: string;
  running_at: string | null;
  completed_at: string | null;
  error_code: string | null;
}

export interface CameraSessionStatusEvent {
  type: "camera_session_status";
  camera_id: string;
  session_id: string;
  asset_id: string;
  media_type: MediaType;
  video_time: number;
  session_status: CameraSessionStatus;
  inference_fps: number;
  error_code?: string | null;
}
export interface LoginRequest { email: string; password: string; }
export interface LoginResponse { access_token: string; token_type: "bearer"; user: AuthenticatedUser; }
export interface ManagedUser extends AuthenticatedUser { is_active: boolean; created_at: string; }
export interface CreateUserRequest { full_name: string; email: string; password: string; role: AssignableUserRole; managed_area_id?: string | null; telegram_username?: string | null; telegram_chat_id?: string | null; }
export interface PasswordChangeRequest { new_password: string; current_password?: string; }
export interface UserRoleUpdate { role: AssignableUserRole; managed_area_id?: string | null; managed_camera_ids?: string[]; telegram_username?: string | null; telegram_chat_id?: string | null; }
export interface TelegramLinkStart { link_url: string; expires_at: string; }
export interface TelegramLinkComplete { status: "linked" | "pending" | "expired"; chat_id?: string | null; telegram_username?: string | null; }

export interface ZoneComplianceStats { zone_id: string; zone_name: string; compliance_rate: number | null; total_detections: number; total_violations: number; }
export interface CameraEventStats { camera_id: string; camera_name: string; official_violations: number; unacknowledged_events: number; false_alarm_events: number; }
export interface StatisticsSummary { total_events: number; unacknowledged_events: number; false_alarm_events?: number; camera_stats?: CameraEventStats[]; overall_compliance_rate: number | null; violations_by_type: Record<string, number>; violations_by_severity: Record<string, number>; zone_stats: ZoneComplianceStats[]; }

export interface ZonePoint {
  x: number;
  y: number;
}

export interface MonitoringZone {
  zone_id: string;
  display_name: string;
  points: ZonePoint[];
  /** @deprecated Camera mapping is the source of truth. */
  machine_state?: MachineState;
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
  ppe: {
    hat: PpeObservation;
    vest: PpeObservation;
  };
  missing_required_ppe: Array<"hat" | "vest">;
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
  class_id: 0 | 3 | 4;
  class_name: "hat" | "person" | "vest";
  bbox: [number, number, number, number];
  confidence: number;
  person_index: number | null;
}

export interface InferenceRule {
  person_inside_zone: boolean;
  machine_state: MachineState;
  ppe_profile: "hat_vest_v1";
  camera_id: string;
  zone_id: string;
  ppe_requirements: PpeRequirementUpdate;
  ppe_alert: boolean;
  restricted_area_alert?: boolean;
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

export interface CameraInferenceResult extends Omit<InferenceResult, "type" | "video_time"> {
  type: "camera_inference_result";
  camera_id: string;
  session_id: string;
  asset_id: string;
  media_type: MediaType;
  video_time: number;
  session_status: CameraSessionStatus;
  inference_fps: number;
  source_timestamp_ms?: number;
  captured_at?: number;
  frame_width: number;
  frame_height: number;
  pending_event_ids?: number[];
}

export interface PendingReviewDetails {
  violations?: string[];
  video_timestamp_seconds?: number;
  pending_review?: CameraInferenceResult;
  review_result?: string;
  people?: PersonDetection[];
}

export interface SafetyEvent {
  id: number;
  timestamp: string;
  zone_id: string;
  camera_id: string;
  camera_name?: string | null;
  event_type: string;
  severity: string;
  status: EventStatus;
  acknowledged_by?: string | null;
  snapshot_path?: string | null;
  details?: PendingReviewDetails;
  monitoring_session_id?: string | null;
  track_id?: number | null;
  occurrence_ids?: string[];
  batch_id?: string | null;
  decision_context?: StoredDecisionContext | null;
  audit_retention_until?: string | null;
  snapshot_retention_until?: string | null;
}

export interface EventRuleContextInput {
  triggered_rule_keys: string[];
  ppe_profile: "hat_vest_v1";
  ppe_requirements: PpeRequirementUpdate;
}

export interface EventSceneContextInput {
  frame_id: number;
  video_timestamp_seconds: number;
  machine_state: MachineState;
  zone_name: string;
  zone_revision?: number | null;
  zone_points: ZonePoint[];
  people: PersonDetection[];
  detections: ModelDetection[];
}

export interface EventSystemDecisionInput {
  result: "violate";
  reason_codes: string[];
}

export interface DecisionContextInput {
  rule: EventRuleContextInput;
  scene: EventSceneContextInput;
  system_decision: EventSystemDecisionInput;
}

export interface StoredDecisionContext extends DecisionContextInput {
  schema_version: "decision_context_v1";
  rule: EventRuleContextInput & {rule_version: "safety_rule_v1"; violation_frame_count: number};
  scene: EventSceneContextInput & {camera_id: string; zone_id: string};
  system_decision: EventSystemDecisionInput & {severity: "low" | "medium" | "high" | "critical"};
  human_review: {
    outcome: "actual_violation" | "false_alarm";
    actor_user_id?: string | null;
    actor_name: string;
    actor_role?: string | null;
    reviewed_at: string;
  };
}

export interface EventIncidentSummary {
  text: string;
  source: "llm" | "deterministic";
  context_schema_version: "decision_context_v1" | null;
}

export interface EventDetail extends SafetyEvent {
  summary: EventIncidentSummary;
}

export interface EventBatchItem {
  zone_id: string;
  event_type: "zone_intrusion";
  severity: string;
  occurrence_ids: string[];
  details: Record<string, unknown>;
  decision_context?: DecisionContextInput;
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
  track_id?: number;
  occurrence_ids: string[];
  decision_context?: DecisionContextInput;
}

export interface PpeRequirementUpdate {
  profile: "hat_vest_v1";
  hat_required: boolean;
  vest_required: boolean;
  restricted_area_detection_enabled?: boolean;
  zone_intrusion_enabled?: boolean;
}

export interface PpeRequirement extends PpeRequirementUpdate {
  camera_id: string;
  zone_id: string;
  is_configured: boolean;
  updated_at: string | null;
}

export interface OperationalLatency {
  count: number;
  min_ms: number | null;
  mean_ms: number | null;
  p50_ms: number | null;
  p95_ms: number | null;
  max_ms: number | null;
}

export interface OperationalRequestMetrics {
  method: string;
  route: string;
  status_class: string;
  count: number;
  latency: OperationalLatency;
}

export interface OperationalMetricsSummary {
  generated_at: string;
  window_start: string;
  window_end: string;
  records_scanned: number;
  skipped_malformed_records: number;
  partial: boolean;
  partial_reasons: string[];
  requests: OperationalRequestMetrics[];
  websocket_connections: Array<{route: string; opened: number; closed: number; inference_latency: OperationalLatency}>;
  inference_latency_samples: Array<{timestamp: string; route: string; duration_ms: number; outcome: string}>;
  inference_outcomes: Record<string, number>;
  errors_by_kind: Record<string, number>;
}
