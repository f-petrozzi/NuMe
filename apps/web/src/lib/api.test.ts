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
      .mockResolvedValueOnce(mockResponse({ id: 7, email: "member@example.com", role: "member", has_profile: true }))
      .mockRejectedValueOnce(makeAxiosError(500, "Profile query failed"));

    const user = await refreshSessionUser("Member Example");

    expect(user).toEqual({
      id: "7",
      email: "member@example.com",
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
});
