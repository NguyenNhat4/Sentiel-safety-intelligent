export type MachineState = "running" | "stopped";
export type ReviewStatus = "acknowledged" | "false_alarm";
export type EventStatus = ReviewStatus | "unacknowledged" | "resolved";
export type UserRole = "system_admin" | "safety_manager" | "area_manager";
export type AssignableUserRole = UserRole;

export interface AuthenticatedUser { id: string; full_name: string; email: string; role: UserRole; role_label: string; must_change_password: boolean; managed_area_id?: string | null; telegram_username?: string | null; telegram_chat_id?: string | null; }
export interface LoginRequest { email: string; password: string; }
export interface LoginResponse { access_token: string; token_type: "bearer"; user: AuthenticatedUser; }
export interface ManagedUser extends AuthenticatedUser { is_active: boolean; created_at: string; }
export interface CreateUserRequest { full_name: string; email: string; password: string; role: AssignableUserRole; managed_area_id?: string | null; telegram_username?: string | null; telegram_chat_id?: string | null; }
export interface PasswordChangeRequest { new_password: string; current_password?: string; }
export interface UserRoleUpdate { role: AssignableUserRole; managed_area_id?: string | null; telegram_username?: string | null; telegram_chat_id?: string | null; }

export interface ZoneComplianceStats { zone_id: string; zone_name: string; compliance_rate: number; total_detections: number; total_violations: number; }
export interface StatisticsSummary { total_events: number; unacknowledged_events: number; overall_compliance_rate: number; violations_by_type: Record<string, number>; violations_by_severity: Record<string, number>; zone_stats: ZoneComplianceStats[]; }

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

export interface SafetyEvent {
  id: number;
  timestamp: string;
  zone_id: string;
  camera_id: string;
  event_type: string;
  severity: string;
  status: EventStatus;
  acknowledged_by?: string | null;
  snapshot_path?: string | null;
  details?: {
    people?: PersonDetection[];
    video_timestamp_seconds?: number;
    review_result?: string;
  };
  monitoring_session_id?: string | null;
  track_id?: number | null;
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
  track_id?: number;
  occurrence_ids: string[];
}

export interface PpeRequirementUpdate {
  profile: "hat_vest_v1";
  hat_required: boolean;
  vest_required: boolean;
  restricted_area_detection_enabled?: boolean;
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
