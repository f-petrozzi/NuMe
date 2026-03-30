import type { PersonaType, RunStatus, RiskLevel, SignalType } from "@/lib/types";

export interface AuthMeDto {
  id: number;
  email: string;
  role: "member" | "coordinator" | "admin";
  has_profile: boolean;
}

export interface ProfileDto {
  id: number;
  user_id: number;
  age_range: string;
  sex: string;
  height_cm: number | null;
  weight_kg: number | null;
  goal: string;
  activity_level: string;
  dietary_style: string;
  allergies: string[];
  persona_type: PersonaType;
  created_at: string;
}

export interface AccessibilityDto {
  user_id: number;
  simplified_language: boolean;
  large_text: boolean;
  low_energy_mode: boolean;
}

export interface WearableEventDto {
  id: number;
  user_id: number;
  source: string;
  signal_type: SignalType;
  value: string;
  unit: string;
  recorded_at: string;
}

export interface NormalizedEventDto {
  id: number;
  user_id: number;
  signals: Record<string, unknown>;
  summary: string;
  created_at: string;
}

export interface AgentRunDto {
  id: number;
  user_id: number;
  normalized_event_id: number | null;
  status: RunStatus;
  started_at: string;
  completed_at: string | null;
  risk_level: RiskLevel | "";
  member_label?: string | null;
  member_email?: string | null;
  persona_type?: PersonaType | null;
  summary?: string | null;
}

export interface AgentMessageDto {
  id: number;
  run_id: number;
  agent_name: string;
  agent_type: "local" | "a2a" | "parallel" | "loop";
  input: Record<string, unknown>;
  output: Record<string, unknown>;
  iteration: number;
  duration_ms: number | null;
  created_at: string;
}

export interface RunTraceDto {
  run: AgentRunDto;
  messages: AgentMessageDto[];
  intervention?: InterventionDto | null;
  case?: CaseDto | null;
}

export interface CaseDto {
  id: number;
  user_id: number;
  run_id: number | null;
  risk_level: RiskLevel;
  status: "open" | "in_progress" | "closed";
  created_at: string;
  updated_at: string;
  member_label?: string | null;
  member_email?: string | null;
  persona_type?: PersonaType | null;
  summary?: string | null;
}

export interface InterventionDto {
  id: number;
  run_id: number | null;
  user_id: number;
  meal_suggestion: string;
  activity_suggestion: string;
  wellness_action: string;
  empathy_message: string;
  meal_constraints?: string[];
  created_at: string;
}

export interface NotificationDto {
  id: number;
  user_id: number;
  type: string;
  content: string;
  status: string;
  created_at: string;
}

export interface ResourceDto {
  id: number;
  persona_type: PersonaType;
  category: string;
  title: string;
  description: string;
  url: string;
}

export interface ScenarioDto {
  id: string;
  name: string;
  description: string;
  persona_type: PersonaType;
}

export interface HealthOverviewDto {
  latest_date: string | null;
  steps: number;
  step_goal: number;
  active_calories: number;
  total_calories: number;
  resting_hr: number;
  avg_hr: number;
  body_battery_high: number;
  body_battery_low: number;
  stress_avg: number;
  active_minutes: number;
  sleep_hours: number;
  sleep_score: number;
  garmin_connected: boolean;
}

export interface RecipeIngredientDto {
  name: string;
  quantity: string;
  category: string;
  section: string;
}

export interface RecipeDto {
  id: number;
  user_id: number | null;
  title: string;
  description: string;
  source_url: string;
  our_way_notes: string;
  prep_minutes: number;
  cook_minutes: number;
  servings: number;
  tags: string[];
  ingredients: RecipeIngredientDto[];
  instructions: string;
  photo_filename: string;
  created_at: string;
}

export interface ParsedRecipeDto {
  title: string;
  description: string;
  source_url: string;
  prep_minutes: number;
  cook_minutes: number;
  servings: number;
  tags: string[];
  ingredients: RecipeIngredientDto[];
  instructions: string;
  photo_url: string;
}

export interface OnboardingRequestDto {
  age_range: string;
  sex: string;
  height_cm?: number;
  weight_kg?: number;
  goal: string;
  activity_level: string;
  dietary_style: string;
  allergies: string[];
  persona_type: PersonaType;
  simplified_language: boolean;
  large_text: boolean;
  low_energy_mode: boolean;
}

export interface CheckInSubmission {
  mood: number;
  sleep_hours: number;
  stress: number;
  note: string;
}

export interface GarminAuthStatusDto {
  connected: boolean;
  user_id: number | null;
  garmin_email: string | null;
  last_sync: string | null;
}

export interface DailyMetricsDto {
  id: number;
  user_id: number;
  metric_date: string;
  steps: number;
  step_goal: number;
  active_calories: number;
  total_calories: number;
  resting_hr: number;
  avg_hr: number;
  body_battery_high: number;
  body_battery_low: number;
  stress_avg: number;
  intensity_minutes_moderate: number;
  intensity_minutes_vigorous: number;
  floors_climbed: number;
  spo2_avg: number;
  hrv_weekly_avg: number;
  hrv_status: string;
  vo2_max: number;
  active_minutes: number;
  synced_at: string;
}

export interface SleepSessionDto {
  id: number;
  user_id: number;
  sleep_date: string;
  sleep_start: string;
  sleep_end: string;
  duration_seconds: number;
  deep_seconds: number;
  light_seconds: number;
  rem_seconds: number;
  awake_seconds: number;
  sleep_score: number;
  avg_spo2: number;
  avg_respiration: number;
  synced_at: string;
}

export interface ActivityDto {
  id: number;
  user_id: number;
  garmin_activity_id: string;
  activity_type: string;
  activity_name: string;
  start_time: string;
  duration_seconds: number;
  distance_meters: number;
  calories: number;
  avg_hr: number;
  max_hr: number;
  elevation_gain_meters: number;
  avg_speed_mps: number;
  training_load: number;
  synced_at: string;
}

export interface CalorieLogDto {
  id: number;
  user_id: number;
  log_date: string;
  meal_type: string;
  food_name: string;
  calories: number;
  quantity: string;
  notes: string;
  ai_estimated: boolean;
  created_at: string;
}

export interface CalorieEstimateDto {
  food_name: string;
  quantity: string;
  estimated_calories: number;
  confidence: string;
}
