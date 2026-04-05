export type RiskLevel = "low" | "moderate" | "high" | "critical";
export type CaseStatus = "open" | "in_progress" | "closed";
export type PersonaType = "student" | "caregiver" | "older_adult" | "accessibility_focused";
export type UserRole = "member" | "coordinator" | "admin";
export type RunStatus = "pending" | "running" | "completed" | "failed";
export type SignalType =
  | "sleep_hours"
  | "sleep_quality"
  | "stress_level"
  | "heart_rate"
  | "steps"
  | "activity_level"
  | "check_in_mood"
  | "check_in_note";
export type AgentName =
  | "coordinator"
  | "signal_interpretation"
  | "risk_stratification"
  | "intervention_planning"
  | "empathy_checkin"
  | "validation_loop"
  | "student_support"
  | "caregiver_burnout"
  | "unknown";
export type AgentType = "local" | "a2a" | "parallel" | "loop";

export interface User {
  id: string;
  email: string | null;
  username?: string | null;
  full_name: string;
  role: UserRole;
  persona?: PersonaType;
  onboarded: boolean;
}

export interface Signal {
  id: string;
  user_id: string;
  signal_type: SignalType;
  value: string;
  unit: string;
  recorded_at: string;
}

export interface SupportPlanAlternative {
  kind: "meal" | "activity" | "wellness" | "unknown";
  title: string;
  rank?: number;
  score?: number;
  reference_id?: string;
}

export interface SupportPlanRecipeSummary {
  id: string;
  title: string;
  description: string;
  tags: string[];
  prep_time: number;
  cook_time: number;
  calories?: number | null;
  protein_grams?: number | null;
  carbs_grams?: number | null;
  fat_grams?: number | null;
  fiber_grams?: number | null;
  prep_effort?: string | null;
  cost_level?: string | null;
  equipment_tags: string[];
}

export interface SupportPlanActivityTemplate {
  id: string;
  title: string;
  description: string;
  duration_minutes: number;
  intensity: string;
  accessibility_tags: string[];
  equipment_tags: string[];
  time_cost_level: string;
  fatigue_sensitivity: string;
  contraindication_tags: string[];
  metadata: Record<string, unknown>;
}

export interface SupportPlanWellnessTemplate {
  id: string;
  title: string;
  description: string;
  category: string;
  duration_minutes: number;
  accessibility_tags: string[];
  time_cost_level: string;
  fatigue_sensitivity: string;
  metadata: Record<string, unknown>;
}

export interface SupportPlanMeal {
  recipe_id?: string;
  title: string;
  description: string;
  text: string;
  constraints: string[];
  why_chosen: string[];
  alternatives_considered: SupportPlanAlternative[];
  recipe?: SupportPlanRecipeSummary;
}

export interface SupportPlanActivity {
  template_id?: string;
  title: string;
  description: string;
  text: string;
  duration_minutes?: number;
  intensity?: string;
  why_chosen: string[];
  alternatives_considered: SupportPlanAlternative[];
  template?: SupportPlanActivityTemplate;
}

export interface SupportPlanWellness {
  template_id?: string;
  title: string;
  description: string;
  text: string;
  category?: string;
  why_chosen: string[];
  alternatives_considered: SupportPlanAlternative[];
  template?: SupportPlanWellnessTemplate;
}

export interface SupportPlanRun {
  id: string;
  status: RunStatus;
  risk_level: RiskLevel;
  started_at: string;
  completed_at?: string;
  normalized_event_id?: string;
}

export interface SupportPlanStateSnapshot {
  id: string;
  run_id?: string;
  source: string;
  created_at: string;
  dynamic_state: Record<string, unknown>;
  archetype_scores: Record<string, number>;
}

export interface SupportPlanRisk {
  level: RiskLevel;
  urgency: string;
  confidence: number;
  subscores: Record<string, number>;
  drivers: string[];
  rationale: string;
}

export interface SupportPlanPlan {
  intervention_id: string;
  created_at: string;
  meal: SupportPlanMeal;
  activity: SupportPlanActivity;
  wellness: SupportPlanWellness;
  empathy_message: string;
  rationale: string;
  why_changed_from_previous: string[];
}

export interface SupportPlan {
  generated_at: string;
  run?: SupportPlanRun;
  state_snapshot?: SupportPlanStateSnapshot;
  risk: SupportPlanRisk;
  plan?: SupportPlanPlan;
}

export interface Case {
  id: string;
  user_id: string;
  run_id?: string;
  member_label?: string;
  member_email?: string;
  persona?: PersonaType;
  risk_level: RiskLevel;
  status: CaseStatus;
  summary: string;
  created_at: string;
  updated_at: string;
}

export interface FinalAction {
  meal_suggestion: string;
  activity_suggestion: string;
  wellness_action: string;
  empathy_message: string;
}

export interface AgentMessage {
  id: string;
  run_id: string;
  agent_name: AgentName | string;
  agent_type: AgentType;
  content: string;
  timestamp: string;
  parent_id?: string;
  is_a2a?: boolean;
  loop_iteration?: number;
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
}

export interface AgentRun {
  id: string;
  user_id: string;
  scenario?: string;
  status: RunStatus;
  started_at: string;
  completed_at?: string;
  risk_level?: RiskLevel;
  member_label?: string;
  member_email?: string;
  persona?: PersonaType;
  summary?: string;
  final_action?: FinalAction;
  case?: Case;
  messages: AgentMessage[];
}

export interface TriggeredRun {
  id: string;
  status: RunStatus;
}

export interface HealthSummary {
  steps: { current: number; goal: number; trend: number };
  sleep: { hours: number; quality: string; trend: number };
  heart_rate: { current: number; resting: number; trend: number };
  stress: { level: number; trend: number };
}

export interface RecipeIngredient {
  name: string;
  quantity: string;
  category: string;
  section: string;
}

export interface RecipeIngredientGroup {
  group: string;
  items: RecipeIngredient[];
}

export interface RecipeInstructionGroup {
  group: string;
  steps: string[];
}

export interface Recipe {
  id: string;
  title: string;
  description: string;
  source_url: string;
  our_way_notes: string;
  tags: string[];
  prep_time: number;
  cook_time: number;
  servings: number;
  calories?: number | null;
  protein_grams?: number | null;
  carbs_grams?: number | null;
  fat_grams?: number | null;
  fiber_grams?: number | null;
  prep_effort?: string | null;
  equipment_tags?: string[];
  cost_level?: string | null;
  ingredients: RecipeIngredientGroup[];
  ingredient_items: RecipeIngredient[];
  instructions: RecipeInstructionGroup[];
  image_url?: string;
}

export interface Scenario {
  id: string;
  label: string;
  description: string;
  persona: PersonaType;
}
