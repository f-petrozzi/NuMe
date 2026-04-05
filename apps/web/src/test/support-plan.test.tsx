import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MemberDashboard from "@/pages/MemberDashboard";
import RecipeListPage from "@/pages/RecipeListPage";
import type { Recipe, SupportPlan } from "@/lib/types";

const apiMocks = vi.hoisted(() => ({
  getDailyQuota: vi.fn(),
  getRecentSignals: vi.fn(),
  getRuns: vi.fn(),
  getSupportPlan: vi.fn(),
  logSupportPlanFeedback: vi.fn(),
  getRecipes: vi.fn(),
  getRecommendedRecipes: vi.fn(),
  parseRecipeUrl: vi.fn(),
  parseRecipeText: vi.fn(),
  createRecipe: vi.fn(),
}));

vi.mock("framer-motion", () => ({
  motion: new Proxy(
    {},
    {
      get: () => (props: Record<string, unknown>) => <div {...props} />,
    },
  ),
}));

vi.mock("@/lib/api", () => apiMocks);

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: {
      id: "u1",
      full_name: "Alex Rivera",
      email: "alex@example.com",
      role: "member",
      onboarded: true,
      persona: "student",
    },
  }),
}));

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

const quotaFixture = {
  global_units_today: 10,
  global_units_limit: 100,
  user_units_today: 5,
  user_units_limit: 25,
  user_units_this_hour: 5,
  user_hourly_limit: 10,
  reset_at: "2026-04-06T00:00:00Z",
  ai_enabled: true,
};

const structuredPlan: SupportPlan = {
  generated_at: "2026-04-05T12:00:00Z",
  run: {
    id: "123",
    status: "completed",
    risk_level: "moderate",
    started_at: "2026-04-05T11:58:00Z",
    completed_at: "2026-04-05T12:00:00Z",
    normalized_event_id: "45",
  },
  state_snapshot: {
    id: "45",
    run_id: "123",
    source: "live_checkin",
    created_at: "2026-04-05T11:57:00Z",
    dynamic_state: {
      sleep_debt: 0.62,
      stress_load: 0.71,
      recovery_score: 0.34,
      prep_capacity: 0.29,
      routine_stability: 0.37,
    },
    archetype_scores: {
      student_overload: 0.74,
      low_energy_recovery: 0.69,
    },
  },
  risk: {
    level: "moderate",
    urgency: "next_day",
    confidence: 0.83,
    subscores: {
      physiological_strain: 0.71,
      recovery_debt: 0.78,
    },
    drivers: [
      "Sleep has been below baseline for three days.",
      "Stress is elevated and body battery is suppressed.",
    ],
    rationale: "Moderate risk driven mostly by recovery debt and physiological strain.",
  },
  plan: {
    intervention_id: "77",
    created_at: "2026-04-05T12:00:00Z",
    meal: {
      recipe_id: "88",
      title: "Turkey and Rice Bowl",
      description: "High-protein, low-prep lunch",
      text: "High-protein, low-prep lunch",
      constraints: ["high_protein", "low_prep"],
      why_chosen: [
        "Fits current prep capacity",
        "Improves protein coverage without high effort",
      ],
      alternatives_considered: [
        { kind: "meal", title: "Protein Oats", rank: 2, reference_id: "17" },
      ],
      recipe: {
        id: "88",
        title: "Turkey and Rice Bowl",
        description: "High-protein, low-prep lunch",
        tags: ["high_protein", "low_prep"],
        prep_time: 10,
        cook_time: 15,
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
      template_id: "5",
      title: "Ten-Minute Reset Walk",
      description: "Short walk",
      text: "Short walk between classes.",
      duration_minutes: 10,
      intensity: "low",
      why_chosen: ["Keeps intensity manageable."],
      alternatives_considered: [],
      template: {
        id: "5",
        title: "Ten-Minute Reset Walk",
        description: "Short walk",
        duration_minutes: 10,
        intensity: "low",
        accessibility_tags: ["low_energy_friendly"],
        equipment_tags: [],
        time_cost_level: "low",
        fatigue_sensitivity: "high",
        contraindication_tags: [],
        metadata: {},
      },
    },
    wellness: {
      template_id: "11",
      title: "Two-Minute Grounding Reset",
      description: "Grounding reset",
      text: "Grounding reset before dinner.",
      category: "grounding",
      why_chosen: ["Directly addresses elevated stress load."],
      alternatives_considered: [],
      template: {
        id: "11",
        title: "Two-Minute Grounding Reset",
        description: "Grounding reset",
        category: "grounding",
        duration_minutes: 2,
        accessibility_tags: ["low_energy_friendly"],
        time_cost_level: "low",
        fatigue_sensitivity: "high",
        metadata: {},
      },
    },
    empathy_message: "Today looks heavier than usual, so the plan stays deliberately low-friction.",
    rationale: "Low-prep, low-friction choices selected to support recovery and consistency.",
    why_changed_from_previous: ["Recovery score fell"],
  },
};

const emptyPlan: SupportPlan = {
  generated_at: "2026-04-05T12:00:00Z",
  risk: {
    level: "low",
    urgency: "routine",
    confidence: 0,
    subscores: {},
    drivers: [],
    rationale: "No support plan has been generated for this member yet.",
  },
};

const recommendedRecipe: Recipe = {
  id: "101",
  title: "Spinach Yogurt Bowl",
  description: "A quick, high-protein bowl with almost no prep.",
  source_url: "",
  our_way_notes: "",
  tags: ["high_protein", "low_prep"],
  prep_time: 8,
  cook_time: 0,
  servings: 1,
  calories: 320,
  protein_grams: 24,
  carbs_grams: 22,
  fat_grams: 14,
  fiber_grams: 4,
  prep_effort: "low",
  equipment_tags: ["bowl", "spoon"],
  cost_level: "medium",
  ingredients: [],
  ingredient_items: [],
  instructions: [],
};

function renderWithProviders(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });

  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("support-plan pages", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    apiMocks.getDailyQuota.mockResolvedValue(quotaFixture);
    apiMocks.getRecentSignals.mockResolvedValue([]);
    apiMocks.getRuns.mockResolvedValue([]);
    apiMocks.getSupportPlan.mockResolvedValue(structuredPlan);
    apiMocks.logSupportPlanFeedback.mockResolvedValue(undefined);
    apiMocks.getRecipes.mockResolvedValue([]);
    apiMocks.getRecommendedRecipes.mockResolvedValue([]);
    apiMocks.parseRecipeUrl.mockResolvedValue(null);
    apiMocks.parseRecipeText.mockResolvedValue(null);
    apiMocks.createRecipe.mockResolvedValue(null);
  });

  it("dashboard renders structured support-plan data including risk drivers and recipe details", async () => {
    renderWithProviders(<MemberDashboard />);

    expect(await screen.findByText("Risk Drivers")).toBeInTheDocument();
    expect(screen.getByText("Sleep has been below baseline for three days.")).toBeInTheDocument();
    expect(screen.getAllByText("Turkey and Rice Bowl")).toHaveLength(2);
    expect(screen.getByText("32g protein")).toBeInTheDocument();
    expect(screen.getByText("Recovery score fell")).toBeInTheDocument();
  });

  it("recipe page renders structured meal recommendation context", async () => {
    renderWithProviders(<RecipeListPage />);

    expect(await screen.findByText("Current Meal Recommendation Context")).toBeInTheDocument();
    expect(await screen.findByText("Why this meal fit today")).toBeInTheDocument();
    expect(screen.getByText("Fits current prep capacity")).toBeInTheDocument();
    expect(screen.getByText("Protein Oats · rank 2")).toBeInTheDocument();
  });

  it("dashboard logs support-plan feedback against the current intervention", async () => {
    renderWithProviders(<MemberDashboard />);

    expect(await screen.findByText("Risk Drivers")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Accept meal recommendation" }));

    await waitFor(() => {
      expect(apiMocks.logSupportPlanFeedback.mock.calls[0]?.[0]).toEqual({
        intervention_id: "77",
        run_id: "123",
        event_type: "accepted",
        source: "member_dashboard",
        recommendation_kind: "meal",
        recommendation_id: "88",
        payload: {
          recommendation_title: "Turkey and Rice Bowl",
          support_plan_generated_at: "2026-04-05T12:00:00Z",
        },
      });
    });
  });

  it("recipe page logs recommended recipe views with intervention context", async () => {
    apiMocks.getRecommendedRecipes.mockResolvedValue([recommendedRecipe]);

    renderWithProviders(<RecipeListPage />);

    const recipeTitle = await screen.findByText("Spinach Yogurt Bowl");
    const recipeLink = recipeTitle.closest("a");
    if (!recipeLink) throw new Error("Expected recommended recipe link");
    fireEvent.click(recipeLink);

    await waitFor(() => {
      expect(apiMocks.logSupportPlanFeedback.mock.calls[0]?.[0]).toEqual({
        intervention_id: "77",
        run_id: "123",
        event_type: "viewed",
        source: "recipe_list_recommended",
        recommendation_kind: "recipe",
        recommendation_id: "101",
        payload: {
          recipe_title: "Spinach Yogurt Bowl",
          recipe_rank: 1,
          support_plan_meal_recipe_id: "88",
          support_plan_meal_title: "Turkey and Rice Bowl",
        },
      });
    });
  });

  it("dashboard renders a fallback state when no structured support plan exists", async () => {
    apiMocks.getSupportPlan.mockResolvedValueOnce(emptyPlan);

    renderWithProviders(<MemberDashboard />);

    expect(await screen.findByText("No structured support plan yet")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Run a scenario or submit a check-in to generate a structured support plan with risk drivers, linked recommendations, and change reasons.",
      ),
    ).toBeInTheDocument();
  });
});
