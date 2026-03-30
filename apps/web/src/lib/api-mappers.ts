import type {
  AgentMessageDto,
  CaseDto,
  HealthOverviewDto,
  InterventionDto,
  ProfileDto,
  RecipeDto,
  RunTraceDto,
  ScenarioDto,
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
  InterventionCard,
  PersonaType,
  Recipe,
  RecipeIngredient,
  Scenario,
  Signal,
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

function emailToDisplayName(email: string): string {
  const localPart = email.split("@")[0] || "NüMe User";
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

function buildCard(title: string, description: string, priority: InterventionCard["priority"]): InterventionCard {
  return { title, description, priority };
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

export function mapUserFromBackend(me: AuthMeDto, profile?: ProfileDto | null, fallbackName?: string): User {
  return {
    id: String(me.id),
    email: me.email,
    full_name: fallbackName?.trim() || emailToDisplayName(me.email),
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

export function mapInterventionToSupportPlan(
  intervention: InterventionDto,
  riskLevel: SupportPlan["risk_level"] = "low",
): SupportPlan {
  return {
    meal: buildCard("Meal Suggestion", intervention.meal_suggestion || "No meal suggestion yet.", "medium"),
    activity: buildCard("Activity Suggestion", intervention.activity_suggestion || "No activity suggestion yet.", "medium"),
    wellness: buildCard("Wellness Action", intervention.wellness_action || "No wellness action yet.", "high"),
    empathy_message: intervention.empathy_message || "Your care plan is being prepared.",
    risk_level: riskLevel,
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
