import { apiClient, clearStoredSession, getStoredUser, setStoredUser } from "@/lib/api-client";
import type {
  ActivityDto,
  AgentRunDto,
  AuthMeDto,
  CalorieEstimateDto,
  CalorieLogDto,
  CheckInSubmission,
  DailyMetricsDto,
  DailyQuotaDto,
  GarminAuthStatusDto,
  HealthOverviewDto,
  OnboardingRequestDto,
  ParsedRecipeDto,
  ProfileDto,
  RecipeDto,
  RunTraceDto,
  ScenarioDto,
  SupportPlanCurrentDto,
  SleepSessionDto,
  WearableEventDto,
  CaseDto,
} from "@/lib/api-contracts";
import {
  mapCase,
  mapHealthOverviewToSummary,
  mapRecipe,
  mapRunTrace,
  mapScenario,
  mapSupportPlan,
  mapUserFromBackend,
  mapWearableEventToSignal,
} from "@/lib/api-mappers";
import { appConfig } from "@/lib/config";
import {
  mockAgentRun,
  mockCases,
  mockHealthSummary,
  mockRecipes,
  mockScenarios,
  mockSignals,
  mockSupportPlan,
  mockUser,
} from "@/lib/mock-data";
import type { AgentRun, Case, HealthSummary, Recipe, Scenario, Signal, SupportPlan, TriggeredRun, User } from "@/lib/types";

export interface RecipeDraftInput {
  title: string;
  description: string;
  source_url: string;
  our_way_notes?: string;
  prep_minutes: number;
  cook_minutes: number;
  servings: number;
  calories?: number | null;
  protein_grams?: number | null;
  carbs_grams?: number | null;
  fat_grams?: number | null;
  fiber_grams?: number | null;
  prep_effort?: string | null;
  equipment_tags?: string[];
  cost_level?: string | null;
  tags: string[];
  ingredients: Array<{
    name: string;
    quantity: string;
    category: string;
    section: string;
  }>;
  instructions: string;
  photo_filename?: string;
}

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

async function fetchProfileIfAvailable(): Promise<ProfileDto | null> {
  try {
    const response = await apiClient.get<ProfileDto>("/api/profile");
    return response.data;
  } catch {
    return null;
  }
}

async function fetchSessionUser(fallbackName?: string): Promise<User> {
  const { data: me } = await apiClient.get<AuthMeDto>("/api/auth/me");

  const profile = await fetchProfileIfAvailable();

  const user = mapUserFromBackend(me, profile, fallbackName || getStoredUser()?.full_name);
  setStoredUser(user);
  return user;
}

export async function refreshSessionUser(fallbackName?: string): Promise<User> {
  return fetchSessionUser(fallbackName);
}

export interface DemoUserEntry {
  id: number;
  email: string;
  role: string;
  label: string;
}

export async function fetchDemoUsers(): Promise<DemoUserEntry[]> {
  const { data } = await apiClient.get<DemoUserEntry[]>("/api/demo/users");
  return data;
}

function mapRunRecord(run: AgentRunDto): AgentRun {
  return {
    id: String(run.id),
    user_id: String(run.user_id),
    status: run.status,
    started_at: run.started_at,
    completed_at: run.completed_at || undefined,
    risk_level: run.risk_level || undefined,
    member_label: run.member_label || undefined,
    member_email: run.member_email || undefined,
    persona: run.persona_type || undefined,
    summary: run.summary || undefined,
    messages: [],
  };
}

async function submitOnboardingLive(data: OnboardingRequestDto): Promise<User> {
  await apiClient.post<ProfileDto>("/api/onboarding", data);
  return fetchSessionUser();
}

async function getRecentSignalsLive(): Promise<Signal[]> {
  const { data } = await apiClient.get<WearableEventDto[]>("/api/events/recent");
  return data.map(mapWearableEventToSignal);
}

async function getSupportPlanLive(): Promise<SupportPlan> {
  const { data } = await apiClient.get<SupportPlanCurrentDto>("/api/support-plan/current");
  return mapSupportPlan(data);
}

async function getCasesLive(): Promise<Case[]> {
  const { data } = await apiClient.get<CaseDto[]>("/api/cases");
  return data.map(mapCase);
}

async function triggerScenarioLive(scenarioId: string): Promise<TriggeredRun> {
  const { data } = await apiClient.post<{ run_id: number }>(`/api/scenarios/${scenarioId}/run`);
  return { id: String(data.run_id), status: "pending" };
}

async function getRunsLive(): Promise<AgentRun[]> {
  const { data } = await apiClient.get<AgentRunDto[]>("/api/runs");
  return data.map(mapRunRecord);
}

async function getAgentRunLive(runId: string): Promise<AgentRun> {
  const { data } = await apiClient.get<RunTraceDto>(`/api/runs/${runId}`);
  return mapRunTrace(data);
}

async function getHealthSummaryLive(): Promise<HealthSummary> {
  const { data } = await apiClient.get<HealthOverviewDto>("/api/health/overview");
  return mapHealthOverviewToSummary(data);
}

async function getRecipesLive(): Promise<Recipe[]> {
  const { data } = await apiClient.get<RecipeDto[]>("/api/recipes");
  return data.map(mapRecipe);
}

async function getRecipeLive(id: string): Promise<Recipe> {
  const { data } = await apiClient.get<RecipeDto>(`/api/recipes/${id}`);
  return mapRecipe(data);
}

async function getRecommendedRecipesLive(): Promise<Recipe[]> {
  const { data } = await apiClient.get<RecipeDto[]>("/api/recipes/recommended");
  return data.map(mapRecipe);
}

async function parseRecipeUrlLive(url: string): Promise<ParsedRecipeDto> {
  const { data } = await apiClient.post<ParsedRecipeDto>("/api/recipes/parse-url", { url });
  return data;
}

async function parseRecipeTextLive(text: string): Promise<ParsedRecipeDto> {
  const { data } = await apiClient.post<ParsedRecipeDto>("/api/recipes/parse-text", { text });
  return data;
}

async function createRecipeLive(input: RecipeDraftInput): Promise<Recipe> {
  const { data } = await apiClient.post<RecipeDto>("/api/recipes", {
    ...input,
    our_way_notes: input.our_way_notes || "",
    photo_filename: input.photo_filename || "",
  });
  return mapRecipe(data);
}

async function getScenariosLive(): Promise<Scenario[]> {
  const { data } = await apiClient.get<ScenarioDto[]>("/api/scenarios");
  return data.map(mapScenario);
}

async function submitCheckInLive(data: CheckInSubmission): Promise<AgentRun> {
  // Single atomic endpoint: creates wearable events + normalized event + agent run
  const { data: run } = await apiClient.post<AgentRunDto>("/api/events/checkin", {
    mood: data.mood,
    sleep_hours: data.sleep_hours,
    stress: data.stress,
    note: data.note,
  });
  return mapRunRecord(run);
}

async function submitOnboardingMock(data: OnboardingRequestDto): Promise<User> {
  await delay(500);
  const user = getStoredUser() ?? mockUser;
  const updated = { ...user, persona: data.persona_type, onboarded: true };
  setStoredUser(updated);
  return updated;
}

async function getRecentSignalsMock(): Promise<Signal[]> {
  await delay(300);
  return mockSignals;
}

async function getSupportPlanMock(): Promise<SupportPlan> {
  await delay(400);
  return mockSupportPlan;
}

async function getCasesMock(): Promise<Case[]> {
  await delay(400);
  return mockCases;
}

async function triggerScenarioMock(scenarioId: string): Promise<TriggeredRun> {
  await delay(1500);
  return { id: `r-${Date.now()}-${scenarioId}`, status: "pending" };
}

async function getRunsMock(): Promise<AgentRun[]> {
  await delay(250);
  return [mockAgentRun];
}

async function getAgentRunMock(_runId: string): Promise<AgentRun> {
  await delay(300);
  return mockAgentRun;
}

async function getHealthSummaryMock(): Promise<HealthSummary> {
  await delay(400);
  return mockHealthSummary;
}

async function getRecipesMock(): Promise<Recipe[]> {
  await delay(300);
  return mockRecipes;
}

async function getRecipeMock(id: string): Promise<Recipe> {
  await delay(200);
  return mockRecipes.find((recipe) => recipe.id === id) || mockRecipes[0];
}

async function getRecommendedRecipesMock(): Promise<Recipe[]> {
  await delay(300);
  return mockRecipes;
}

async function parseRecipeUrlMock(url: string): Promise<ParsedRecipeDto> {
  await delay(500);
  return {
    title: "Imported Recipe",
    description: `Parsed from ${url}`,
    source_url: url,
    prep_minutes: 10,
    cook_minutes: 15,
    servings: 2,
    calories: null,
    protein_grams: null,
    carbs_grams: null,
    fat_grams: null,
    fiber_grams: null,
    prep_effort: "medium",
    equipment_tags: [],
    cost_level: null,
    tags: ["quick", "imported"],
    ingredients: [
      { name: "olive oil", quantity: "1 tbsp", category: "Pantry", section: "Main" },
      { name: "spinach", quantity: "2 cups", category: "Produce", section: "Main" },
    ],
    instructions: "Combine ingredients.\nCook until ready.",
    photo_url: "",
  };
}

async function parseRecipeTextMock(text: string): Promise<ParsedRecipeDto> {
  await delay(500);
  return {
    title: "Pasted Recipe",
    description: text.slice(0, 120) || "Recipe parsed from pasted text.",
    source_url: "",
    prep_minutes: 10,
    cook_minutes: 10,
    servings: 2,
    calories: null,
    protein_grams: null,
    carbs_grams: null,
    fat_grams: null,
    fiber_grams: null,
    prep_effort: "low",
    equipment_tags: [],
    cost_level: null,
    tags: ["pasted", "ai"],
    ingredients: [
      { name: "rolled oats", quantity: "1/2 cup", category: "Pantry", section: "Main" },
      { name: "banana", quantity: "1", category: "Produce", section: "Main" },
    ],
    instructions: "Mix ingredients.\nServe warm.",
    photo_url: "",
  };
}

async function createRecipeMock(input: RecipeDraftInput): Promise<Recipe> {
  await delay(400);
  return mapRecipe({
    id: Date.now(),
    user_id: 1,
    title: input.title,
    description: input.description,
    source_url: input.source_url,
    our_way_notes: input.our_way_notes || "",
    prep_minutes: input.prep_minutes,
    cook_minutes: input.cook_minutes,
    servings: input.servings,
    calories: input.calories ?? null,
    protein_grams: input.protein_grams ?? null,
    carbs_grams: input.carbs_grams ?? null,
    fat_grams: input.fat_grams ?? null,
    fiber_grams: input.fiber_grams ?? null,
    prep_effort: input.prep_effort ?? null,
    equipment_tags: input.equipment_tags ?? [],
    cost_level: input.cost_level ?? null,
    tags: input.tags,
    ingredients: input.ingredients,
    instructions: input.instructions,
    photo_filename: input.photo_filename || "",
    created_at: new Date().toISOString(),
  });
}

async function getScenariosMock(): Promise<Scenario[]> {
  await delay(200);
  return mockScenarios;
}

async function submitCheckInMock(): Promise<AgentRun> {
  await delay(1000);
  return { ...mockAgentRun, id: `r-${Date.now()}`, status: "running" };
}

export function isMockApiEnabled() {
  return appConfig.useMockApi;
}

export { getStoredUser };

export function logout() {
  clearStoredSession();
}

export async function submitOnboarding(data: OnboardingRequestDto): Promise<User> {
  return appConfig.useMockApi ? submitOnboardingMock(data) : submitOnboardingLive(data);
}

export async function getRecentSignals(): Promise<Signal[]> {
  return appConfig.useMockApi ? getRecentSignalsMock() : getRecentSignalsLive();
}

export async function getSupportPlan(): Promise<SupportPlan> {
  return appConfig.useMockApi ? getSupportPlanMock() : getSupportPlanLive();
}

export async function getCases(): Promise<Case[]> {
  return appConfig.useMockApi ? getCasesMock() : getCasesLive();
}

export async function triggerScenario(scenarioId: string): Promise<TriggeredRun> {
  return appConfig.useMockApi ? triggerScenarioMock(scenarioId) : triggerScenarioLive(scenarioId);
}

export async function getRuns(): Promise<AgentRun[]> {
  return appConfig.useMockApi ? getRunsMock() : getRunsLive();
}

export async function getAgentRun(runId: string): Promise<AgentRun> {
  return appConfig.useMockApi ? getAgentRunMock(runId) : getAgentRunLive(runId);
}

export async function getHealthSummary(): Promise<HealthSummary> {
  return appConfig.useMockApi ? getHealthSummaryMock() : getHealthSummaryLive();
}

export async function getRecipes(): Promise<Recipe[]> {
  return appConfig.useMockApi ? getRecipesMock() : getRecipesLive();
}

export async function getRecipe(id: string): Promise<Recipe> {
  return appConfig.useMockApi ? getRecipeMock(id) : getRecipeLive(id);
}

export async function getRecommendedRecipes(): Promise<Recipe[]> {
  return appConfig.useMockApi ? getRecommendedRecipesMock() : getRecommendedRecipesLive();
}

export async function parseRecipeUrl(url: string): Promise<ParsedRecipeDto> {
  return appConfig.useMockApi ? parseRecipeUrlMock(url) : parseRecipeUrlLive(url);
}

export async function parseRecipeText(text: string): Promise<ParsedRecipeDto> {
  return appConfig.useMockApi ? parseRecipeTextMock(text) : parseRecipeTextLive(text);
}

export async function createRecipe(input: RecipeDraftInput): Promise<Recipe> {
  return appConfig.useMockApi ? createRecipeMock(input) : createRecipeLive(input);
}

export async function getScenarios(): Promise<Scenario[]> {
  return appConfig.useMockApi ? getScenariosMock() : getScenariosLive();
}

export async function submitCheckIn(data: CheckInSubmission): Promise<AgentRun> {
  return appConfig.useMockApi ? submitCheckInMock() : submitCheckInLive(data);
}

// ---------------------------------------------------------------------------
// Garmin integration
// ---------------------------------------------------------------------------

async function getGarminAuthStatusLive(): Promise<GarminAuthStatusDto> {
  const { data } = await apiClient.get<GarminAuthStatusDto>("/api/health/garmin/auth-status");
  return data;
}

async function connectGarminLive(email: string, password: string): Promise<GarminAuthStatusDto> {
  const { data } = await apiClient.post<GarminAuthStatusDto>("/api/health/garmin/connect", { email, password });
  return data;
}

async function disconnectGarminLive(): Promise<void> {
  await apiClient.delete("/api/health/garmin/disconnect");
}

async function triggerGarminSyncLive(): Promise<{ synced: number }> {
  const { data } = await apiClient.post<{ synced: number }>("/api/health/sync");
  return data;
}

async function getGarminAuthStatusMock(): Promise<GarminAuthStatusDto> {
  await delay(200);
  return { connected: false, user_id: null, garmin_email: null, last_sync: null };
}

async function connectGarminMock(_email: string, _password: string): Promise<GarminAuthStatusDto> {
  await delay(800);
  return { connected: true, user_id: 1, garmin_email: _email, last_sync: null };
}

async function disconnectGarminMock(): Promise<void> {
  await delay(400);
}

async function triggerGarminSyncMock(): Promise<{ synced: number }> {
  await delay(1200);
  return { synced: 7 };
}

export async function getGarminAuthStatus(): Promise<GarminAuthStatusDto> {
  return appConfig.useMockApi ? getGarminAuthStatusMock() : getGarminAuthStatusLive();
}

export async function connectGarmin(email: string, password: string): Promise<GarminAuthStatusDto> {
  return appConfig.useMockApi ? connectGarminMock(email, password) : connectGarminLive(email, password);
}

export async function disconnectGarmin(): Promise<void> {
  return appConfig.useMockApi ? disconnectGarminMock() : disconnectGarminLive();
}

export async function triggerGarminSync(): Promise<{ synced: number }> {
  return appConfig.useMockApi ? triggerGarminSyncMock() : triggerGarminSyncLive();
}

// ---------------------------------------------------------------------------
// Health data: daily metrics, sleep, activities
// ---------------------------------------------------------------------------

async function getDailyMetricsLive(days = 30): Promise<DailyMetricsDto[]> {
  const { data } = await apiClient.get<DailyMetricsDto[]>(`/api/health/daily?days=${days}`);
  return data;
}

async function getSleepHistoryLive(days = 30): Promise<SleepSessionDto[]> {
  const { data } = await apiClient.get<SleepSessionDto[]>(`/api/health/sleep?days=${days}`);
  return data;
}

async function getActivitiesLive(limit = 20): Promise<ActivityDto[]> {
  const { data } = await apiClient.get<ActivityDto[]>(`/api/health/activities?limit=${limit}`);
  return data;
}

function _makeMockDailyMetrics(days: number): DailyMetricsDto[] {
  const now = new Date("2026-03-29");
  return Array.from({ length: Math.min(days, 7) }, (_, i) => {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().slice(0, 10);
    return {
      id: i + 1, user_id: 1, metric_date: dateStr,
      steps: 3000 + Math.round(Math.random() * 5000),
      step_goal: 8000, active_calories: 200 + Math.round(Math.random() * 300),
      total_calories: 1800 + Math.round(Math.random() * 600),
      resting_hr: 62 + Math.round(Math.random() * 10),
      avg_hr: 70 + Math.round(Math.random() * 15),
      body_battery_high: 80 + Math.round(Math.random() * 20),
      body_battery_low: 20 + Math.round(Math.random() * 30),
      stress_avg: 35 + Math.round(Math.random() * 45),
      intensity_minutes_moderate: Math.round(Math.random() * 30),
      intensity_minutes_vigorous: Math.round(Math.random() * 15),
      floors_climbed: Math.round(Math.random() * 10),
      spo2_avg: 97 + Math.random() * 2,
      hrv_weekly_avg: 40 + Math.random() * 20,
      hrv_status: "balanced",
      vo2_max: 38 + Math.random() * 10,
      active_minutes: 20 + Math.round(Math.random() * 60),
      synced_at: d.toISOString(),
    };
  });
}

async function getDailyMetricsMock(days = 30): Promise<DailyMetricsDto[]> {
  await delay(300);
  return _makeMockDailyMetrics(days);
}

async function getSleepHistoryMock(days = 30): Promise<SleepSessionDto[]> {
  await delay(300);
  const now = new Date("2026-03-29");
  return Array.from({ length: Math.min(days, 7) }, (_, i) => {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const dateStr = d.toISOString().slice(0, 10);
    const durationSec = Math.round((4.5 + Math.random() * 4) * 3600);
    return {
      id: i + 1, user_id: 1, sleep_date: dateStr,
      sleep_start: `${dateStr}T23:00:00Z`, sleep_end: `${dateStr}T07:00:00Z`,
      duration_seconds: durationSec,
      deep_seconds: Math.round(durationSec * 0.2),
      light_seconds: Math.round(durationSec * 0.5),
      rem_seconds: Math.round(durationSec * 0.2),
      awake_seconds: Math.round(durationSec * 0.1),
      sleep_score: 50 + Math.round(Math.random() * 40),
      avg_spo2: 96 + Math.random() * 3,
      avg_respiration: 14 + Math.random() * 3,
      synced_at: d.toISOString(),
    };
  });
}

async function getActivitiesMock(_limit = 20): Promise<ActivityDto[]> {
  await delay(200);
  const types = ["running", "cycling", "walking", "strength_training", "yoga"];
  const now = new Date("2026-03-29");
  return Array.from({ length: 5 }, (_, i) => {
    const d = new Date(now);
    d.setDate(d.getDate() - i * 2);
    return {
      id: i + 1, user_id: 1,
      garmin_activity_id: `act-${i + 1}`,
      activity_type: types[i % types.length],
      activity_name: types[i % types.length].replace(/_/g, " "),
      start_time: d.toISOString(),
      duration_seconds: 1200 + Math.round(Math.random() * 3600),
      distance_meters: Math.round(Math.random() * 8000),
      calories: 150 + Math.round(Math.random() * 400),
      avg_hr: 120 + Math.round(Math.random() * 40),
      max_hr: 160 + Math.round(Math.random() * 20),
      elevation_gain_meters: Math.round(Math.random() * 100),
      avg_speed_mps: 1.5 + Math.random() * 3,
      training_load: 30 + Math.random() * 70,
      synced_at: d.toISOString(),
    };
  });
}

export async function getDailyMetrics(days = 30): Promise<DailyMetricsDto[]> {
  return appConfig.useMockApi ? getDailyMetricsMock(days) : getDailyMetricsLive(days);
}

export async function getSleepHistory(days = 30): Promise<SleepSessionDto[]> {
  return appConfig.useMockApi ? getSleepHistoryMock(days) : getSleepHistoryLive(days);
}

export async function getActivities(limit = 20): Promise<ActivityDto[]> {
  return appConfig.useMockApi ? getActivitiesMock(limit) : getActivitiesLive(limit);
}

// ---------------------------------------------------------------------------
// Daily quota
// ---------------------------------------------------------------------------

async function getDailyQuotaLive(): Promise<DailyQuotaDto> {
  const { data } = await apiClient.get<DailyQuotaDto>("/api/quota/daily");
  return data;
}

async function getDailyQuotaMock(): Promise<DailyQuotaDto> {
  await delay(150);
  const tomorrow = new Date();
  tomorrow.setUTCHours(24, 0, 0, 0);
  return {
    global_units_today: 23,
    global_units_limit: 500,
    user_units_today: 10,
    user_units_limit: 50,
    user_units_this_hour: 5,
    user_hourly_limit: 15,
    reset_at: tomorrow.toISOString(),
    ai_enabled: true,
  };
}

export async function getDailyQuota(): Promise<DailyQuotaDto> {
  return appConfig.useMockApi ? getDailyQuotaMock() : getDailyQuotaLive();
}

// ---------------------------------------------------------------------------
// Calorie log
// ---------------------------------------------------------------------------

async function getCalorieLogLive(logDate?: string): Promise<CalorieLogDto[]> {
  const url = logDate ? `/api/health/calorie-log?log_date=${logDate}` : "/api/health/calorie-log";
  const { data } = await apiClient.get<CalorieLogDto[]>(url);
  return data;
}

async function addCalorieLogLive(entry: Omit<CalorieLogDto, "id" | "user_id" | "created_at">): Promise<CalorieLogDto> {
  const { data } = await apiClient.post<CalorieLogDto>("/api/health/calorie-log", entry);
  return data;
}

async function deleteCalorieLogLive(entryId: number): Promise<void> {
  await apiClient.delete(`/api/health/calorie-log/${entryId}`);
}

async function estimateCaloriesLive(foodName: string, quantity: string): Promise<CalorieEstimateDto> {
  const { data } = await apiClient.post<CalorieEstimateDto>("/api/health/calorie-log/ai-estimate", { food_name: foodName, quantity });
  return data;
}

let _mockCalorieLog: CalorieLogDto[] = [
  { id: 1, user_id: 1, log_date: "2026-03-29", meal_type: "breakfast", food_name: "Oatmeal with banana", calories: 350, quantity: "1 bowl", notes: "", ai_estimated: false, created_at: "2026-03-29T08:00:00Z" },
  { id: 2, user_id: 1, log_date: "2026-03-29", meal_type: "lunch", food_name: "Spinach walnut salad", calories: 420, quantity: "1 serving", notes: "", ai_estimated: false, created_at: "2026-03-29T12:30:00Z" },
];

async function getCalorieLogMock(_logDate?: string): Promise<CalorieLogDto[]> {
  await delay(200);
  return [..._mockCalorieLog];
}

async function addCalorieLogMock(entry: Omit<CalorieLogDto, "id" | "user_id" | "created_at">): Promise<CalorieLogDto> {
  await delay(300);
  const newEntry: CalorieLogDto = {
    ...entry,
    id: Date.now(),
    user_id: 1,
    created_at: new Date().toISOString(),
  };
  _mockCalorieLog = [newEntry, ..._mockCalorieLog];
  return newEntry;
}

async function deleteCalorieLogMock(entryId: number): Promise<void> {
  await delay(200);
  _mockCalorieLog = _mockCalorieLog.filter((e) => e.id !== entryId);
}

async function estimateCaloriesMock(foodName: string, quantity: string): Promise<CalorieEstimateDto> {
  await delay(600);
  return { food_name: foodName, quantity, estimated_calories: 250, confidence: "medium" };
}

export async function getCalorieLog(logDate?: string): Promise<CalorieLogDto[]> {
  return appConfig.useMockApi ? getCalorieLogMock(logDate) : getCalorieLogLive(logDate);
}

export async function addCalorieLog(entry: Omit<CalorieLogDto, "id" | "user_id" | "created_at">): Promise<CalorieLogDto> {
  return appConfig.useMockApi ? addCalorieLogMock(entry) : addCalorieLogLive(entry);
}

export async function deleteCalorieLog(entryId: number): Promise<void> {
  return appConfig.useMockApi ? deleteCalorieLogMock(entryId) : deleteCalorieLogLive(entryId);
}

export async function estimateCalories(foodName: string, quantity: string): Promise<CalorieEstimateDto> {
  return appConfig.useMockApi ? estimateCaloriesMock(foodName, quantity) : estimateCaloriesLive(foodName, quantity);
}
