import type {
  AgentMessageDto,
  CaseDto,
  HealthOverviewDto,
  InterventionDto,
  ProfileDto,
  RecipeDto,
  RunTraceDto,
  ScenarioDto,
  SupportPlanActivityDto,
  SupportPlanActivityTemplateDto,
  SupportPlanCurrentDto,
  SupportPlanMealDto,
  SupportPlanRecipeDto,
  SupportPlanWellnessDto,
  SupportPlanWellnessTemplateDto,
  WearableEventDto,
  AuthMeDto,
} from "@/lib/api-contracts";
import type {
  AgentMessage,
  AgentName,
  AgentRun,
  Case,
  FinalAction,
  HealthSummary,
  PersonaType,
  Recipe,
  RecipeIngredient,
  Scenario,
  Signal,
  SupportPlanAlternative,
  SupportPlan,
  User,
} from "@/lib/types";

const KNOWN_AGENT_NAMES: Record<string, AgentName> = {
  coordinator: "coordinator",
  carecoordinator: "coordinator",
  signalinterpretation: "signal_interpretation",
  signal_interpretation: "signal_interpretation",
  riskstratification: "risk_stratification",
  risk_stratification: "risk_stratification",
  interventionplanning: "intervention_planning",
  intervention_planning: "intervention_planning",
  empathycheckin: "empathy_checkin",
  empathy_checkin: "empathy_checkin",
  validationloop: "validation_loop",
  validation_loop: "validation_loop",
  studentsupport: "student_support",
  studentsupportspecialist: "student_support",
  studentsupportfallback: "student_support",
  student_support: "student_support",
  caregiverburnout: "caregiver_burnout",
  caregiverburnoutspecialist: "caregiver_burnout",
  caregiverburnoutfallback: "caregiver_burnout",
  caregiver_burnout: "caregiver_burnout",
};

function toStringId(value: string | number | null | undefined): string {
  return value == null ? "" : String(value);
}

function titleCaseWords(input: string): string {
  return input
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function identifierToDisplayName(identifier: string | null | undefined): string {
  const localPart = (identifier || "").split("@")[0] || "NüMe User";
  return titleCaseWords(localPart.replace(/\d+/g, " ").replace(/[.+]/g, " "));
}

function normalizeAgentName(name: string): AgentName | string {
  const key = name.replace(/\s+/g, "").replace(/[^a-zA-Z_]/g, "").toLowerCase();
  return KNOWN_AGENT_NAMES[key] || KNOWN_AGENT_NAMES[name.toLowerCase()] || name.toLowerCase().replace(/\s+/g, "_");
}

function summarizeValue(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value) && value.length > 0) {
    return value
      .map((item) => summarizeValue(item))
      .filter(Boolean)
      .slice(0, 3)
      .join(", ");
  }
  if (value && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>)
      .map(([key, inner]) => {
        const summary = summarizeValue(inner);
        return summary ? `${titleCaseWords(key)}: ${summary}` : null;
      })
      .filter(Boolean);
    return entries.slice(0, 3).join(" · ");
  }
  return null;
}

function summarizeAgentOutput(output: Record<string, unknown>): string {
  const preferredKeys = ["summary", "message", "result", "explanation", "plan", "risk_level", "findings"];
  for (const key of preferredKeys) {
    if (key in output) {
      const preferred = summarizeValue(output[key]);
      if (preferred) return preferred;
    }
  }

  const fallback = summarizeValue(output);
  return fallback || "Agent step completed.";
}

function normalizeRiskLevel(value: string | undefined | null): SupportPlan["risk"]["level"] {
  if (value === "moderate" || value === "high" || value === "critical") return value;
  return "low";
}

function computeSleepQuality(score: number): string {
  if (score >= 85) return "Excellent";
  if (score >= 70) return "Good";
  if (score >= 55) return "Fair";
  return "Poor";
}

function normalizePersona(persona: PersonaType | undefined): PersonaType | undefined {
  if (!persona) return undefined;
  return persona;
}

function normalizeNumberRecord(values: Record<string, unknown> | undefined | null): Record<string, number> {
  const normalized: Record<string, number> = {};
  for (const [key, value] of Object.entries(values || {})) {
    const parsed = Number(value);
    if (Number.isFinite(parsed)) normalized[key] = parsed;
  }
  return normalized;
}

function toOptionalStringId(value: unknown): string | undefined {
  return value == null ? undefined : String(value);
}

function normalizeStringList(values: unknown): string[] {
  if (!Array.isArray(values)) return [];
  return values
    .map((value) => String(value || "").trim())
    .filter(Boolean);
}

function normalizeAlternative(
  value: unknown,
  fallbackKind: SupportPlanAlternative["kind"],
): SupportPlanAlternative | null {
  if (typeof value === "number" || typeof value === "string") {
    const referenceId = String(value);
    return {
      kind: fallbackKind,
      title: `${titleCaseWords(fallbackKind)} Alternative #${referenceId}`,
      reference_id: referenceId,
    };
  }

  if (!value || typeof value !== "object") return null;

  const item = value as Record<string, unknown>;
  const kindValue = String(item.kind || fallbackKind).trim().toLowerCase();
  const kind: SupportPlanAlternative["kind"] =
    kindValue === "meal" || kindValue === "activity" || kindValue === "wellness" ? kindValue : "unknown";
  const referenceId = toOptionalStringId(item.recipe_id ?? item.template_id ?? item.id);
  const rank = Number(item.rank);
  const score = Number(item.score);
  const title =
    String(item.title || "").trim() ||
    (referenceId ? `${titleCaseWords(kind)} Alternative #${referenceId}` : `${titleCaseWords(kind)} Alternative`);

  return {
    kind,
    title,
    reference_id: referenceId,
    rank: Number.isFinite(rank) ? rank : undefined,
    score: Number.isFinite(score) ? score : undefined,
  };
}

function normalizeAlternatives(
  values: unknown[] | null | undefined,
  fallbackKind: SupportPlanAlternative["kind"],
): SupportPlanAlternative[] {
  return (values || [])
    .map((value) => normalizeAlternative(value, fallbackKind))
    .filter((value): value is SupportPlanAlternative => value !== null);
}

function normalizeRecipeIngredient(ingredient: RecipeDto["ingredients"][number]): RecipeIngredient {
  return {
    name: ingredient.name?.trim() || "",
    quantity: ingredient.quantity?.trim() || "",
    category: ingredient.category?.trim() || "Other",
    section: ingredient.section?.trim() || "",
  };
}

function groupRecipeIngredients(ingredients: RecipeDto["ingredients"]): Recipe["ingredients"] {
  if (!ingredients.length) return [];

  const normalized = ingredients.map(normalizeRecipeIngredient);
  const hasSections = normalized.some((ingredient) => ingredient.section);
  const groups = new Map<string, RecipeIngredient[]>();

  for (const ingredient of normalized) {
    const group = hasSections ? ingredient.section || "Ingredients" : "Ingredients";
    if (!groups.has(group)) groups.set(group, []);
    groups.get(group)!.push(ingredient);
  }

  return [...groups.entries()].map(([group, items]) => ({ group, items }));
}

function groupRecipeInstructions(instructions: string): Recipe["instructions"] {
  if (!instructions.trim()) return [];

  const groups: Recipe["instructions"] = [];
  let currentGroup = "Steps";
  let currentSteps: string[] = [];

  const flush = () => {
    if (currentSteps.length > 0) {
      groups.push({ group: currentGroup, steps: currentSteps });
      currentSteps = [];
    }
  };

  for (const rawLine of instructions.split("\n")) {
    const line = rawLine.trim();
    if (!line) continue;
    if (line.startsWith("## ")) {
      flush();
      currentGroup = line.replace(/^##\s+/, "").trim() || "Steps";
      continue;
    }
    currentSteps.push(line.replace(/^\d+[.)]\s+/, "").trim());
  }

  flush();
  return groups.length > 0 ? groups : [{ group: "Steps", steps: instructions.split("\n").filter(Boolean) }];
}

function mapSupportPlanRecipe(recipe: SupportPlanRecipeDto) {
  return {
    id: String(recipe.id),
    title: recipe.title,
    description: recipe.description,
    tags: recipe.tags || [],
    prep_time: recipe.prep_minutes,
    cook_time: recipe.cook_minutes,
    calories: recipe.calories ?? null,
    protein_grams: recipe.protein_grams ?? null,
    carbs_grams: recipe.carbs_grams ?? null,
    fat_grams: recipe.fat_grams ?? null,
    fiber_grams: recipe.fiber_grams ?? null,
    prep_effort: recipe.prep_effort ?? null,
    cost_level: recipe.cost_level ?? null,
    equipment_tags: recipe.equipment_tags ?? [],
  };
}

function mapSupportPlanActivityTemplate(template: SupportPlanActivityTemplateDto) {
  return {
    id: String(template.id),
    title: template.title,
    description: template.description,
    duration_minutes: template.duration_minutes,
    intensity: template.intensity,
    accessibility_tags: template.accessibility_tags ?? [],
    equipment_tags: template.equipment_tags ?? [],
    time_cost_level: template.time_cost_level,
    fatigue_sensitivity: template.fatigue_sensitivity,
    contraindication_tags: template.contraindication_tags ?? [],
    metadata: template.metadata ?? {},
  };
}

function mapSupportPlanWellnessTemplate(template: SupportPlanWellnessTemplateDto) {
  return {
    id: String(template.id),
    title: template.title,
    description: template.description,
    category: template.category,
    duration_minutes: template.duration_minutes,
    accessibility_tags: template.accessibility_tags ?? [],
    time_cost_level: template.time_cost_level,
    fatigue_sensitivity: template.fatigue_sensitivity,
    metadata: template.metadata ?? {},
  };
}

function mapSupportPlanMeal(meal: SupportPlanMealDto) {
  return {
    recipe_id: toOptionalStringId(meal.recipe_id),
    title: meal.title,
    description: meal.description,
    text: meal.text,
    constraints: normalizeStringList(meal.constraints),
    why_chosen: normalizeStringList(meal.why_chosen),
    alternatives_considered: normalizeAlternatives(meal.alternatives_considered, "meal"),
    recipe: meal.recipe ? mapSupportPlanRecipe(meal.recipe) : undefined,
  };
}

function mapSupportPlanActivity(activity: SupportPlanActivityDto) {
  return {
    template_id: toOptionalStringId(activity.template_id),
    title: activity.title,
    description: activity.description,
    text: activity.text,
    duration_minutes:
      typeof activity.duration_minutes === "number" && Number.isFinite(activity.duration_minutes)
        ? activity.duration_minutes
        : undefined,
    intensity: activity.intensity || undefined,
    why_chosen: normalizeStringList(activity.why_chosen),
    alternatives_considered: normalizeAlternatives(activity.alternatives_considered, "activity"),
    template: activity.template ? mapSupportPlanActivityTemplate(activity.template) : undefined,
  };
}

function mapSupportPlanWellness(wellness: SupportPlanWellnessDto) {
  return {
    template_id: toOptionalStringId(wellness.template_id),
    title: wellness.title,
    description: wellness.description,
    text: wellness.text,
    category: wellness.category || undefined,
    why_chosen: normalizeStringList(wellness.why_chosen),
    alternatives_considered: normalizeAlternatives(wellness.alternatives_considered, "wellness"),
    template: wellness.template ? mapSupportPlanWellnessTemplate(wellness.template) : undefined,
  };
}

export function mapUserFromBackend(me: AuthMeDto, profile?: ProfileDto | null, fallbackName?: string): User {
  const identifier = me.username || me.email;
  return {
    id: String(me.id),
    email: me.email,
    username: me.username,
    full_name: fallbackName?.trim() || identifierToDisplayName(identifier),
    role: me.role,
    persona: normalizePersona(profile?.persona_type),
    onboarded: me.has_profile,
  };
}

export function mapWearableEventToSignal(event: WearableEventDto): Signal {
  return {
    id: String(event.id),
    user_id: String(event.user_id),
    signal_type: event.signal_type,
    value: event.value,
    unit: event.unit,
    recorded_at: event.recorded_at,
  };
}

export function mapAgentMessage(message: AgentMessageDto): AgentMessage {
  const agentName = normalizeAgentName(message.agent_name);
  return {
    id: String(message.id),
    run_id: String(message.run_id),
    agent_name: agentName,
    agent_type: message.agent_type,
    content: summarizeAgentOutput(message.output),
    timestamp: message.created_at,
    is_a2a: message.agent_type === "a2a",
    loop_iteration: message.agent_type === "loop" ? message.iteration : undefined,
    input: message.input,
    output: message.output,
  };
}

export function mapRunTrace(trace: RunTraceDto): AgentRun {
  return {
    id: String(trace.run.id),
    user_id: String(trace.run.user_id),
    status: trace.run.status,
    started_at: trace.run.started_at,
    completed_at: trace.run.completed_at || undefined,
    risk_level: trace.run.risk_level || undefined,
    member_label: trace.run.member_label || undefined,
    member_email: trace.run.member_email || undefined,
    persona: normalizePersona(trace.run.persona_type || undefined),
    summary: trace.run.summary || undefined,
    final_action: trace.intervention ? mapFinalAction(trace.intervention) : undefined,
    case: trace.case ? mapCase(trace.case) : undefined,
    messages: trace.messages.map(mapAgentMessage),
  };
}

export function mapCase(dto: CaseDto): Case {
  return {
    id: String(dto.id),
    user_id: String(dto.user_id),
    run_id: toStringId(dto.run_id),
    member_label: dto.member_label || undefined,
    member_email: dto.member_email || undefined,
    persona: normalizePersona(dto.persona_type || undefined),
    risk_level: dto.risk_level,
    status: dto.status,
    summary: dto.summary || (dto.run_id ? `Follow-up case created from run #${dto.run_id}` : `Follow-up case for member #${dto.user_id}`),
    created_at: dto.created_at,
    updated_at: dto.updated_at,
  };
}

function mapFinalAction(intervention: InterventionDto): FinalAction {
  return {
    meal_suggestion: intervention.meal_suggestion,
    activity_suggestion: intervention.activity_suggestion,
    wellness_action: intervention.wellness_action,
    empathy_message: intervention.empathy_message,
  };
}

export function mapSupportPlan(dto: SupportPlanCurrentDto): SupportPlan {
  return {
    generated_at: dto.generated_at,
    run: dto.run
      ? {
          id: String(dto.run.id),
          status: dto.run.status,
          risk_level: normalizeRiskLevel(dto.run.risk_level),
          started_at: dto.run.started_at,
          completed_at: dto.run.completed_at || undefined,
          normalized_event_id: toOptionalStringId(dto.run.normalized_event_id),
        }
      : undefined,
    state_snapshot: dto.state_snapshot
      ? {
          id: String(dto.state_snapshot.id),
          run_id: toOptionalStringId(dto.state_snapshot.run_id),
          source: dto.state_snapshot.source,
          created_at: dto.state_snapshot.created_at,
          dynamic_state: dto.state_snapshot.dynamic_state || {},
          archetype_scores: normalizeNumberRecord(dto.state_snapshot.archetype_scores),
        }
      : undefined,
    risk: {
      level: normalizeRiskLevel(dto.risk.level),
      urgency: dto.risk.urgency || "routine",
      confidence: Number.isFinite(Number(dto.risk.confidence)) ? Number(dto.risk.confidence) : 0,
      subscores: normalizeNumberRecord(dto.risk.subscores),
      drivers: normalizeStringList(dto.risk.drivers),
      rationale: dto.risk.rationale || "",
    },
    plan: dto.plan
      ? {
          intervention_id: String(dto.plan.intervention_id),
          created_at: dto.plan.created_at,
          meal: mapSupportPlanMeal(dto.plan.meal),
          activity: mapSupportPlanActivity(dto.plan.activity),
          wellness: mapSupportPlanWellness(dto.plan.wellness),
          empathy_message: dto.plan.empathy_message,
          rationale: dto.plan.rationale || "",
          why_changed_from_previous: normalizeStringList(dto.plan.why_changed_from_previous),
        }
      : undefined,
  };
}

export function mapHealthOverviewToSummary(overview: HealthOverviewDto): HealthSummary {
  return {
    steps: {
      current: overview.steps,
      goal: overview.step_goal,
      trend: 0,
    },
    sleep: {
      hours: overview.sleep_hours,
      quality: computeSleepQuality(overview.sleep_score),
      trend: 0,
    },
    heart_rate: {
      current: overview.avg_hr,
      resting: overview.resting_hr,
      trend: 0,
    },
    stress: {
      level: overview.stress_avg,
      trend: 0,
    },
  };
}

export function mapRecipe(dto: RecipeDto): Recipe {
  const ingredientItems = dto.ingredients.map(normalizeRecipeIngredient);

  return {
    id: String(dto.id),
    title: dto.title,
    description: dto.description,
    source_url: dto.source_url,
    our_way_notes: dto.our_way_notes,
    tags: dto.tags,
    prep_time: dto.prep_minutes,
    cook_time: dto.cook_minutes,
    servings: dto.servings,
    calories: dto.calories ?? null,
    protein_grams: dto.protein_grams ?? null,
    carbs_grams: dto.carbs_grams ?? null,
    fat_grams: dto.fat_grams ?? null,
    fiber_grams: dto.fiber_grams ?? null,
    prep_effort: dto.prep_effort ?? null,
    equipment_tags: dto.equipment_tags ?? [],
    cost_level: dto.cost_level ?? null,
    ingredients: groupRecipeIngredients(dto.ingredients),
    ingredient_items: ingredientItems,
    instructions: groupRecipeInstructions(dto.instructions),
    image_url: dto.photo_filename ? `/uploads/${dto.photo_filename}` : undefined,
  };
}

export function mapScenario(dto: ScenarioDto): Scenario {
  return {
    id: dto.id,
    label: dto.name,
    description: dto.description,
    persona: dto.persona_type,
  };
}
