import type { AxiosError } from "axios";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  addCalorieLog,
  connectGarmin,
  deleteCalorieLog,
  disconnectGarmin,
  estimateCalories,
  getActivities,
  getCalorieLog,
  getDailyMetrics,
  getGarminAuthStatus,
  getSleepHistory,
  logSupportPlanFeedback,
  getSupportPlan,
  refreshSessionUser,
  triggerGarminSync,
} from "@/lib/api";
import { apiClient } from "@/lib/api-client";
import { appConfig, storageKeys } from "@/lib/config";

// Silence appConfig mock-api warning: tests always run in live mode (useMockApi=false)
vi.mock("@/lib/config", async (importOriginal) => {
  const orig = await importOriginal<typeof import("@/lib/config")>();
  return { ...orig, appConfig: { ...orig.appConfig, useMockApi: false } };
});

function makeAxiosError(status: number, detail?: string): AxiosError {
  return {
    isAxiosError: true,
    name: "AxiosError",
    message: detail ?? `Request failed with status ${status}`,
    toJSON: () => ({}),
    response: {
      status,
      statusText: "",
      headers: {},
      config: { headers: {} },
      data: detail ? { detail } : undefined,
    },
  } as AxiosError;
}

function mockResponse<T>(data: T) {
  return { data } as { data: T };
}

describe("Garmin integration API", () => {
  beforeEach(() => { vi.restoreAllMocks(); });

  it("getGarminAuthStatus returns connected status", async () => {
    vi.spyOn(apiClient, "get").mockResolvedValueOnce(
      mockResponse({ connected: true, user_id: 5, garmin_email: "user@garmin.com", last_sync: "2026-03-29T08:00:00Z" }),
    );
    const status = await getGarminAuthStatus();
    expect(status.connected).toBe(true);
    expect(status.garmin_email).toBe("user@garmin.com");
  });

  it("getGarminAuthStatus returns disconnected status", async () => {
    vi.spyOn(apiClient, "get").mockResolvedValueOnce(
      mockResponse({ connected: false, user_id: null, garmin_email: null, last_sync: null }),
    );
    const status = await getGarminAuthStatus();
    expect(status.connected).toBe(false);
    expect(status.garmin_email).toBeNull();
  });

  it("connectGarmin posts email and password and returns status", async () => {
    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce(
      mockResponse({ connected: true, user_id: 1, garmin_email: "test@garmin.com", last_sync: null }),
    );
    const result = await connectGarmin("test@garmin.com", "secret");
    expect(postSpy).toHaveBeenCalledWith("/api/health/garmin/connect", { email: "test@garmin.com", password: "secret" });
    expect(result.connected).toBe(true);
  });

  it("connectGarmin propagates HTTP errors", async () => {
    vi.spyOn(apiClient, "post").mockRejectedValueOnce(makeAxiosError(400, "Garmin authentication failed"));
    await expect(connectGarmin("bad@example.com", "wrong")).rejects.toMatchObject({
      response: { status: 400 },
    });
  });

  it("disconnectGarmin calls DELETE endpoint", async () => {
    const deleteSpy = vi.spyOn(apiClient, "delete").mockResolvedValueOnce(mockResponse(undefined));
    await disconnectGarmin();
    expect(deleteSpy).toHaveBeenCalledWith("/api/health/garmin/disconnect");
  });

  it("triggerGarminSync calls POST /sync", async () => {
    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce(mockResponse({ synced: 7 }));
    const result = await triggerGarminSync();
    expect(postSpy).toHaveBeenCalledWith("/api/health/sync");
    expect(result.synced).toBe(7);
  });
});

describe("Health data API", () => {
  beforeEach(() => { vi.restoreAllMocks(); });

  it("getDailyMetrics calls correct endpoint with default days", async () => {
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockResponse([]));
    await getDailyMetrics();
    expect(getSpy).toHaveBeenCalledWith("/api/health/daily?days=30");
  });

  it("getDailyMetrics passes custom days parameter", async () => {
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockResponse([]));
    await getDailyMetrics(7);
    expect(getSpy).toHaveBeenCalledWith("/api/health/daily?days=7");
  });

  it("getSleepHistory calls correct endpoint", async () => {
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockResponse([]));
    await getSleepHistory(14);
    expect(getSpy).toHaveBeenCalledWith("/api/health/sleep?days=14");
  });

  it("getActivities calls correct endpoint with limit", async () => {
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockResponse([]));
    await getActivities(10);
    expect(getSpy).toHaveBeenCalledWith("/api/health/activities?limit=10");
  });
});

describe("Calorie log API", () => {
  beforeEach(() => { vi.restoreAllMocks(); });

  it("getCalorieLog fetches all entries when no date given", async () => {
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockResponse([]));
    await getCalorieLog();
    expect(getSpy).toHaveBeenCalledWith("/api/health/calorie-log");
  });

  it("getCalorieLog passes date filter when provided", async () => {
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce(mockResponse([]));
    await getCalorieLog("2026-03-29");
    expect(getSpy).toHaveBeenCalledWith("/api/health/calorie-log?log_date=2026-03-29");
  });

  it("addCalorieLog posts entry and returns saved record", async () => {
    const entry = { log_date: "2026-03-29", meal_type: "lunch", food_name: "Salad", calories: 400, quantity: "1 bowl", notes: "", ai_estimated: false };
    const saved = { ...entry, id: 99, user_id: 1, created_at: "2026-03-29T13:00:00Z" };
    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce(mockResponse(saved));
    const result = await addCalorieLog(entry);
    expect(postSpy).toHaveBeenCalledWith("/api/health/calorie-log", entry);
    expect(result.id).toBe(99);
    expect(result.food_name).toBe("Salad");
  });

  it("deleteCalorieLog calls DELETE with correct id", async () => {
    const deleteSpy = vi.spyOn(apiClient, "delete").mockResolvedValueOnce(mockResponse(undefined));
    await deleteCalorieLog(42);
    expect(deleteSpy).toHaveBeenCalledWith("/api/health/calorie-log/42");
  });

  it("estimateCalories posts food name and quantity", async () => {
    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce(
      mockResponse({ food_name: "Pasta", quantity: "1 cup", estimated_calories: 220, confidence: "high" }),
    );
    const result = await estimateCalories("Pasta", "1 cup");
    expect(postSpy).toHaveBeenCalledWith("/api/health/calorie-log/ai-estimate", { food_name: "Pasta", quantity: "1 cup" });
    expect(result.estimated_calories).toBe(220);
    expect(result.confidence).toBe("high");
  });
});

describe("refreshSessionUser", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("keeps the signed-in user when profile enrichment fails", async () => {
    const getSpy = vi.spyOn(apiClient, "get");
    getSpy
      .mockResolvedValueOnce(
        mockResponse({ id: 7, email: "member@example.com", username: null, role: "member", has_profile: true }),
      )
      .mockRejectedValueOnce(makeAxiosError(500, "Profile query failed"));

    const user = await refreshSessionUser("Member Example");

    expect(user).toEqual({
      id: "7",
      email: "member@example.com",
      username: null,
      full_name: "Member Example",
      role: "member",
      persona: undefined,
      onboarded: true,
    });
    expect(getSpy).toHaveBeenCalledTimes(2);
    expect(localStorage.getItem(storageKeys.user)).toBe(JSON.stringify(user));
  });

  it("still fails when the Clerk-backed auth lookup fails", async () => {
    const getSpy = vi.spyOn(apiClient, "get").mockRejectedValueOnce(makeAxiosError(401, "Invalid Clerk session token"));

    await expect(refreshSessionUser()).rejects.toMatchObject({
      response: { status: 401, data: { detail: "Invalid Clerk session token" } },
    });
    expect(getSpy).toHaveBeenCalledTimes(1);
  });

  it("supports username-only Clerk users", async () => {
    const getSpy = vi.spyOn(apiClient, "get");
    getSpy
      .mockResolvedValueOnce(mockResponse({ id: 8, email: null, username: "wellness.member", role: "member", has_profile: false }))
      .mockRejectedValueOnce(makeAxiosError(404, "Profile not found"));

    const user = await refreshSessionUser();

    expect(user).toEqual({
      id: "8",
      email: null,
      username: "wellness.member",
      full_name: "Wellness Member",
      role: "member",
      persona: undefined,
      onboarded: false,
    });
    expect(getSpy).toHaveBeenCalledTimes(2);
    expect(localStorage.getItem(storageKeys.user)).toBe(JSON.stringify(user));
  });
});

describe("support-plan API", () => {
  beforeEach(() => { vi.restoreAllMocks(); });

  it("getSupportPlan uses the structured support-plan endpoint", async () => {
    const getSpy = vi.spyOn(apiClient, "get").mockResolvedValueOnce(
      mockResponse({
        generated_at: "2026-04-05T12:00:00Z",
        run: {
          id: 123,
          status: "completed",
          risk_level: "moderate",
          started_at: "2026-04-05T11:58:00Z",
          completed_at: "2026-04-05T12:00:00Z",
          normalized_event_id: 45,
        },
        state_snapshot: {
          id: 45,
          run_id: 123,
          source: "live_checkin",
          created_at: "2026-04-05T11:57:00Z",
          dynamic_state: { sleep_debt: 0.62, stress_load: 0.71 },
          archetype_scores: { student_overload: 0.74 },
        },
        risk: {
          level: "moderate",
          urgency: "next_day",
          confidence: 0.83,
          subscores: { physiological_strain: 0.71, recovery_debt: 0.78 },
          drivers: ["Sleep has been below baseline for three days."],
          rationale: "Moderate risk driven mostly by recovery debt and physiological strain.",
        },
        plan: {
          intervention_id: 77,
          created_at: "2026-04-05T12:00:00Z",
          meal: {
            recipe_id: 88,
            title: "Turkey and Rice Bowl",
            description: "High-protein, low-prep lunch",
            text: "High-protein, low-prep lunch",
            constraints: ["high_protein", "low_prep"],
            why_chosen: ["Fits current prep capacity"],
            alternatives_considered: [{ kind: "meal", title: "Protein Oats", rank: 2, recipe_id: 17 }],
            recipe: {
              id: 88,
              title: "Turkey and Rice Bowl",
              description: "High-protein, low-prep lunch",
              tags: ["high_protein"],
              prep_minutes: 10,
              cook_minutes: 15,
              calories: 420,
              protein_grams: 32,
              carbs_grams: 45,
              fat_grams: 12,
              fiber_grams: 6,
              prep_effort: "low",
              cost_level: "medium",
              equipment_tags: ["pan"],
            },
          },
          activity: {
            template_id: 5,
            title: "Ten-Minute Reset Walk",
            description: "Short walk",
            text: "Short walk",
            duration_minutes: 10,
            intensity: "low",
            why_chosen: [],
            alternatives_considered: [],
            template: null,
          },
          wellness: {
            template_id: 11,
            title: "Two-Minute Grounding Reset",
            description: "Grounding reset",
            text: "Grounding reset",
            category: "grounding",
            why_chosen: [],
            alternatives_considered: [],
            template: null,
          },
          empathy_message: "Today looks heavier than usual, so the plan stays deliberately low-friction.",
          rationale: "Low-prep, low-friction choices selected to support recovery and consistency.",
          why_changed_from_previous: ["Recovery score fell"],
        },
      }),
    );

    const result = await getSupportPlan();

    expect(getSpy).toHaveBeenCalledWith("/api/support-plan/current");
    expect(result.risk.level).toBe("moderate");
    expect(result.plan?.meal.recipe?.title).toBe("Turkey and Rice Bowl");
    expect(result.plan?.meal.alternatives_considered[0]).toEqual({
      kind: "meal",
      title: "Protein Oats",
      reference_id: "17",
      rank: 2,
      score: undefined,
    });
  });

  it("logSupportPlanFeedback posts intervention-scoped feedback", async () => {
    const postSpy = vi.spyOn(apiClient, "post").mockResolvedValueOnce(
      mockResponse({
        id: 901,
        user_id: 1,
        run_id: 123,
        intervention_id: 77,
        event_type: "accepted",
        payload: {
          source: "member_dashboard",
          recommendation_kind: "meal",
          recommendation_id: 88,
          recommendation_title: "Turkey and Rice Bowl",
        },
        created_at: "2026-04-05T12:05:00Z",
      }),
    );

    await logSupportPlanFeedback({
      intervention_id: "77",
      run_id: "123",
      event_type: "accepted",
      source: "member_dashboard",
      recommendation_kind: "meal",
      recommendation_id: "88",
      payload: {
        recommendation_title: "Turkey and Rice Bowl",
      },
    });

    expect(postSpy).toHaveBeenCalledWith("/api/support-plan/feedback", {
      intervention_id: 77,
      run_id: 123,
      event_type: "accepted",
      source: "member_dashboard",
      recommendation_kind: "meal",
      recommendation_id: 88,
      payload: {
        recommendation_title: "Turkey and Rice Bowl",
      },
    });
  });
});
