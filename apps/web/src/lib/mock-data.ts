import type { User, Signal, SupportPlan, Case, AgentRun, HealthSummary, Recipe, Scenario, AgentMessage } from "./types";

export const mockUser: User = {
  id: "u1",
  email: "student@nume.demo",
  full_name: "Alex Rivera",
  role: "member",
  persona: "student",
  onboarded: true,
};

export const mockAdmin: User = {
  id: "u3",
  email: "admin@nume.demo",
  full_name: "Dr. Sarah Chen",
  role: "admin",
  persona: undefined,
  onboarded: true,
};

export const mockSignals: Signal[] = [
  { id: "s1", user_id: "u1", signal_type: "sleep_hours", value: "5.2", unit: "hours", recorded_at: "2026-03-28T07:00:00Z" },
  { id: "s2", user_id: "u1", signal_type: "stress_level", value: "72", unit: "score", recorded_at: "2026-03-28T10:00:00Z" },
  { id: "s3", user_id: "u1", signal_type: "steps", value: "3200", unit: "steps", recorded_at: "2026-03-28T12:00:00Z" },
  { id: "s4", user_id: "u1", signal_type: "heart_rate", value: "82", unit: "bpm", recorded_at: "2026-03-28T10:30:00Z" },
  { id: "s5", user_id: "u1", signal_type: "check_in_mood", value: "4", unit: "scale_1_10", recorded_at: "2026-03-28T09:00:00Z" },
];

export const mockSupportPlan: SupportPlan = {
  meal: {
    title: "Anti-Stress Meal Plan",
    description: "Focus on magnesium-rich foods today: dark leafy greens, nuts, and whole grains. Try the spinach & walnut salad for lunch.",
    priority: "medium",
  },
  activity: {
    title: "Gentle Movement Break",
    description: "Your step count is low and stress is elevated. Take a 15-minute walk outside between classes. Fresh air and light movement reduce cortisol.",
    priority: "high",
  },
  wellness: {
    title: "Sleep Recovery Protocol",
    description: "You slept only 5.2 hours. Tonight, set a phone-down alarm at 10pm. Try the 4-7-8 breathing technique before bed.",
    priority: "high",
  },
  empathy_message: "Hey Alex — I can see last night was rough and today's been stressful. You're doing more than you realize. Let's focus on small wins today: one good meal, one short walk, and getting to bed a little earlier. You've got this. 💚",
  risk_level: "moderate",
  confidence: 0.82,
};

export const mockCases: Case[] = [
  { id: "c1", user_id: "u1", run_id: "r1", member_label: "Alex Rivera", member_email: "student@nume.demo", persona: "student", risk_level: "moderate", status: "open", summary: "Elevated stress + sleep deficit pattern over 3 days", created_at: "2026-03-28T10:30:00Z", updated_at: "2026-03-28T10:30:00Z" },
  { id: "c2", user_id: "u2", member_label: "Maria Santos", member_email: "caregiver@nume.demo", persona: "caregiver", risk_level: "high", status: "in_progress", summary: "Caregiver burnout indicators — declining self-care metrics", created_at: "2026-03-27T14:00:00Z", updated_at: "2026-03-28T09:00:00Z" },
  { id: "c3", user_id: "u4", member_label: "James Whitfield", member_email: "older_adult@nume.demo", persona: "older_adult", risk_level: "low", status: "closed", summary: "Routine check-in — all vitals within normal range", created_at: "2026-03-26T08:00:00Z", updated_at: "2026-03-27T16:00:00Z" },
  { id: "c4", user_id: "u5", member_label: "Priya Kapoor", member_email: "student2@nume.demo", persona: "student", risk_level: "critical", status: "open", summary: "Severe sleep deprivation + academic crisis indicators", created_at: "2026-03-28T06:00:00Z", updated_at: "2026-03-28T11:00:00Z" },
];

const traceMessages: AgentMessage[] = [
  { id: "m1", run_id: "r1", agent_name: "coordinator", agent_type: "local", content: "Starting care coordination pipeline for user u1 (student persona). Dispatching parallel analysis agents.", timestamp: "2026-03-28T10:30:00Z" },
  { id: "m2", run_id: "r1", agent_name: "signal_interpretation", agent_type: "parallel", content: "Analyzing recent signals: sleep=5.2h (below 7h threshold), stress=72 (elevated), steps=3200 (below 5000 target), mood=4/10 (low). Pattern: acute stress with sleep deficit.", timestamp: "2026-03-28T10:30:02Z", parent_id: "m1" },
  { id: "m3", run_id: "r1", agent_name: "risk_stratification", agent_type: "parallel", content: "Risk assessment: MODERATE (confidence: 0.82). Factors: 2+ days sleep < 6h, stress trending up, declining activity. Not yet critical but requires intervention.", timestamp: "2026-03-28T10:30:02Z", parent_id: "m1" },
  { id: "m4", run_id: "r1", agent_name: "intervention_planning", agent_type: "parallel", content: "Generated 3 interventions: (1) Anti-stress meal plan focusing on magnesium, (2) 15-min walk breaks between classes, (3) Sleep recovery protocol with phone-down alarm.", timestamp: "2026-03-28T10:30:02Z", parent_id: "m1" },
  { id: "m5", run_id: "r1", agent_name: "student_support", agent_type: "a2a", content: "A2A specialist response: Recommending campus counseling center (free for students), study group formation to reduce isolation, and academic advisor check-in for workload management.", timestamp: "2026-03-28T10:30:04Z", parent_id: "m1", is_a2a: true },
  { id: "m6", run_id: "r1", agent_name: "validation_loop", agent_type: "loop", content: "Iteration 1: Checking for contradictions in plan... Activity recommendation aligns with stress reduction goal. Meal plan supports sleep recovery. No conflicts detected.", timestamp: "2026-03-28T10:30:05Z", parent_id: "m1", loop_iteration: 1 },
  { id: "m7", run_id: "r1", agent_name: "validation_loop", agent_type: "loop", content: "Iteration 2: Cross-referencing with persona profile... Student schedule considered. Recommendations are feasible within typical class schedule. Plan approved.", timestamp: "2026-03-28T10:30:06Z", parent_id: "m1", loop_iteration: 2 },
  { id: "m8", run_id: "r1", agent_name: "empathy_checkin", agent_type: "local", content: "Generated empathy message tailored to student persona. Tone: supportive, non-judgmental, action-oriented. Includes acknowledgment of difficulty and concrete next steps.", timestamp: "2026-03-28T10:30:07Z", parent_id: "m1" },
  { id: "m9", run_id: "r1", agent_name: "coordinator", agent_type: "local", content: "Pipeline complete. Support plan delivered. Case c1 created with moderate risk. Notifications sent.", timestamp: "2026-03-28T10:30:08Z" },
];

export const mockAgentRun: AgentRun = {
  id: "r1",
  user_id: "u1",
  scenario: "stressed_student",
  status: "completed",
  started_at: "2026-03-28T10:30:00Z",
  completed_at: "2026-03-28T10:30:08Z",
  risk_level: "moderate",
  member_label: "Alex Rivera",
  member_email: "student@nume.demo",
  persona: "student",
  summary: "sleep 5.2h; stress 7.2/10; mood: low",
  final_action: {
    meal_suggestion: "Focus on magnesium-rich foods and a simple lunch you can actually fit between classes.",
    activity_suggestion: "Take a 15-minute outdoor walk between classes to break the stress cycle.",
    wellness_action: "Set a phone-down alarm tonight and protect one earlier bedtime window.",
    empathy_message: "Hey Alex, I can see this week has been heavy. Start with one small reset and let the rest be enough for today.",
  },
  case: mockCases[0],
  messages: traceMessages,
};

export const mockHealthSummary: HealthSummary = {
  steps: { current: 3200, goal: 8000, trend: -15 },
  sleep: { hours: 5.2, quality: "Poor", trend: -22 },
  heart_rate: { current: 82, resting: 68, trend: 5 },
  stress: { level: 72, trend: 18 },
};

export const mockRecipes: Recipe[] = [
  {
    id: "rec1",
    title: "Spinach & Walnut Power Salad",
    description: "A magnesium-rich salad to combat stress and support better sleep.",
    source_url: "",
    our_way_notes: "",
    tags: ["anti-stress", "quick", "high-magnesium"],
    prep_time: 10,
    cook_time: 0,
    servings: 1,
    ingredients: [
      {
        group: "Base",
        items: [
          { name: "fresh spinach", quantity: "3 cups", category: "Produce", section: "Base" },
          { name: "walnuts", quantity: "1/4 cup", category: "Pantry", section: "Base" },
          { name: "avocado, sliced", quantity: "1/4", category: "Produce", section: "Base" },
        ],
      },
      {
        group: "Dressing",
        items: [
          { name: "olive oil", quantity: "1 tbsp", category: "Pantry", section: "Dressing" },
          { name: "lemon juice", quantity: "1 tsp", category: "Produce", section: "Dressing" },
          { name: "sea salt", quantity: "Pinch", category: "Pantry", section: "Dressing" },
        ],
      },
    ],
    ingredient_items: [
      { name: "fresh spinach", quantity: "3 cups", category: "Produce", section: "Base" },
      { name: "walnuts", quantity: "1/4 cup", category: "Pantry", section: "Base" },
      { name: "avocado, sliced", quantity: "1/4", category: "Produce", section: "Base" },
      { name: "olive oil", quantity: "1 tbsp", category: "Pantry", section: "Dressing" },
      { name: "lemon juice", quantity: "1 tsp", category: "Produce", section: "Dressing" },
      { name: "sea salt", quantity: "Pinch", category: "Pantry", section: "Dressing" },
    ],
    instructions: [
      { group: "Assemble", steps: ["Wash and dry spinach", "Toast walnuts lightly in a dry pan", "Combine spinach, walnuts, and avocado in a bowl"] },
      { group: "Dress", steps: ["Whisk olive oil, lemon juice, and salt", "Drizzle over salad and toss gently"] },
    ],
  },
  {
    id: "rec2",
    title: "Calming Chamomile Oat Bowl",
    description: "A warm, soothing breakfast that promotes relaxation and sustained energy.",
    source_url: "",
    our_way_notes: "",
    tags: ["breakfast", "calming", "sleep-support"],
    prep_time: 5,
    cook_time: 10,
    servings: 1,
    ingredients: [
      {
        group: "Base",
        items: [
          { name: "rolled oats", quantity: "1/2 cup", category: "Pantry", section: "Base" },
          { name: "chamomile tea (brewed)", quantity: "1 cup", category: "Beverages", section: "Base" },
          { name: "honey", quantity: "1 tbsp", category: "Pantry", section: "Base" },
        ],
      },
      {
        group: "Toppings",
        items: [
          { name: "banana, sliced", quantity: "1", category: "Produce", section: "Toppings" },
          { name: "almond butter", quantity: "1 tbsp", category: "Pantry", section: "Toppings" },
          { name: "cinnamon", quantity: "to taste", category: "Pantry", section: "Toppings" },
        ],
      },
    ],
    ingredient_items: [
      { name: "rolled oats", quantity: "1/2 cup", category: "Pantry", section: "Base" },
      { name: "chamomile tea (brewed)", quantity: "1 cup", category: "Beverages", section: "Base" },
      { name: "honey", quantity: "1 tbsp", category: "Pantry", section: "Base" },
      { name: "banana, sliced", quantity: "1", category: "Produce", section: "Toppings" },
      { name: "almond butter", quantity: "1 tbsp", category: "Pantry", section: "Toppings" },
      { name: "cinnamon", quantity: "to taste", category: "Pantry", section: "Toppings" },
    ],
    instructions: [
      { group: "Cook", steps: ["Brew chamomile tea and pour into a saucepan", "Add oats and cook on medium for 8-10 minutes", "Stir in honey"] },
      { group: "Serve", steps: ["Transfer to a bowl", "Top with banana, almond butter, and cinnamon"] },
    ],
  },
];

export const mockScenarios: Scenario[] = [
  { id: "stressed_student", label: "Stressed Student", description: "Simulates a college student with poor sleep, high stress, and low activity", persona: "student" },
  { id: "exhausted_caregiver", label: "Exhausted Caregiver", description: "Simulates a caregiver showing burnout indicators and declining self-care", persona: "caregiver" },
  { id: "older_adult", label: "Stable Older Adult", description: "Simulates a healthy older adult with normal vitals for routine check-in", persona: "older_adult" },
];
