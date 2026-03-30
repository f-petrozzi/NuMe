# API Contracts — NüMe

Base URL: `http://localhost:8000`
Auth: `Authorization: Bearer <Clerk session token>` on protected endpoints

---

## Auth

Authentication is handled by Clerk. The API does not expose local password login or registration endpoints.

### GET /api/auth/me
```json
// Response 200
{ "id": 1, "email": "user@example.com", "role": "member", "has_profile": true }
```

---

## Onboarding & Profile

### POST /api/onboarding
```json
// Request
{
  "age_range": "18-24",
  "sex": "male",
  "height_cm": 175.0,
  "weight_kg": 70.0,
  "goal": "stress_reduction",
  "activity_level": "moderate",
  "dietary_style": "omnivore",
  "allergies": [],
  "persona_type": "student",
  "simplified_language": false,
  "large_text": false,
  "low_energy_mode": false
}

// Response 201 — UserProfile
{ "id": 1, "user_id": 1, "age_range": "18-24", "sex": "male", "height_cm": 175.0,
  "weight_kg": 70.0, "goal": "stress_reduction", "activity_level": "moderate",
  "dietary_style": "omnivore", "allergies": [], "persona_type": "student",
  "created_at": "2026-03-28T00:00:00Z" }
```

**Goal options:** `stress_reduction` | `better_sleep` | `weight_loss` | `energy_improvement` | `burnout_recovery`
**Persona options:** `student` | `caregiver` | `older_adult` | `accessibility_focused`

### GET /api/profile → UserProfile
### PUT /api/profile → UserProfile (partial update)
### GET /api/profile/accessibility → AccessibilityPreferences
### PUT /api/profile/accessibility → AccessibilityPreferences

---

## Events

### GET /api/events/recent?limit=20 ← used by get_recent_signals_tool
```json
// Response 200 — List[WearableEvent] ordered by recorded_at desc
[{ "id": 1, "user_id": 1, "source": "manual", "signal_type": "stress_level",
   "value": "8", "unit": "1-10", "recorded_at": "..." }]
```

### POST /api/events/checkin  ← preferred for manual check-ins
Atomic: creates raw wearable events + normalized event + agent run. Returns AgentRun so the
frontend can navigate directly to the trace.
```json
// Request
{
  "mood": 7,           // 1-10
  "sleep_hours": 6.5,  // 0-12
  "stress": 70,        // 0-100 (frontend percentage; stored as 1-10 internally)
  "note": "Feeling tired"  // optional
}
// Response 201 — AgentRun
{ "id": 3, "user_id": 1, "normalized_event_id": 5, "status": "pending",
  "started_at": "...", "completed_at": null, "risk_level": "" }
```

### POST /api/events/ingest  ← raw single-signal ingestion (no normalization, no run)
```json
// Request
{
  "signal_type": "stress_level",
  "value": "7",
  "unit": "1-10",
  "source": "manual"
}
// Response 201 — WearableEvent
{ "id": 1, "user_id": 1, "source": "manual", "signal_type": "stress_level",
  "value": "7", "unit": "1-10", "recorded_at": "2026-03-28T12:00:00Z" }
```

**Signal types:** `sleep_hours` | `sleep_quality` | `stress_level` | `heart_rate` | `steps` | `activity_level` | `check_in_mood` | `check_in_note`

### POST /api/events/simulate
```json
// Request
{ "scenario": "stressed_student" }
// Response 201 — NormalizedEvent
{ "id": 1, "user_id": 1, "signals": { "sleep_hours": "4.5", "stress_level": "8", ... },
  "summary": "sleep 4.5h; stress 8/10; mood: anxious", "created_at": "..." }
```

**Scenarios:** `stressed_student` | `exhausted_caregiver` | `older_adult`

---

## Audit Logs

### POST /api/audit-logs ← used by persist_audit_tool
```json
// Request
{ "action": "agent_completed", "entity_type": "agent_run", "entity_id": "3",
  "metadata": { "agent": "RiskStratification", "risk_level": "moderate" } }
// Response 201 — AuditLog
{ "id": 1, "user_id": 1, "action": "agent_completed", "entity_type": "agent_run",
  "entity_id": "3", "metadata": {...}, "created_at": "..." }
```

---

## Agent Runs

### POST /api/runs/trigger
`normalized_event_id` is **required**. Returns 422 if absent/null. Returns 404 if the event
does not exist or belongs to a different user. Prefer `POST /api/events/checkin` for check-ins
and `POST /api/scenarios/{id}/run` for scenario runner — use this endpoint only when you already
have a normalized event ID and want to re-trigger a run.
```json
// Request
{ "normalized_event_id": 1 }
// Response 201 — AgentRun
{ "id": 1, "user_id": 1, "normalized_event_id": 1, "status": "pending",
  "started_at": "...", "completed_at": null, "risk_level": "" }
```

### PUT /api/runs/:id ← used by coordinator to update status
```json
// Request (all fields optional)
{ "status": "completed", "risk_level": "moderate" }
// Response — AgentRun
```

### POST /api/runs/messages ← used by persist_audit_tool / coordinator
```json
// Request
{ "run_id": 3, "agent_name": "SignalInterpretation", "agent_type": "parallel",
  "input": {...}, "output": {...}, "iteration": 0, "duration_ms": 1200 }
// Response 201 — AgentMessage
```

### GET /api/runs → List[AgentRun]

### GET /api/runs/:id
```json
// Response 200 — RunTrace
{
  "run": { "id": 1, "user_id": 1, "status": "completed", "risk_level": "moderate", ... },
  "messages": [
    { "id": 1, "run_id": 1, "agent_name": "SignalInterpretation", "agent_type": "parallel",
      "input": {...}, "output": {...}, "iteration": 0, "duration_ms": 1200, "created_at": "..." }
  ]
}
```

**AgentRun.status:** `pending` | `running` | `completed` | `failed`
**AgentMessage.agent_type:** `local` | `a2a` | `parallel` | `loop`

---

## Cases

### POST /api/cases ← used by create_case_tool
```json
// Request
{ "user_id": 1, "run_id": 3, "risk_level": "moderate" }
// Response 201 — Case
```

### GET /api/cases → List[Case]
### GET /api/cases/:id → Case
### PUT /api/cases/:id/status
```json
// Request
{ "status": "in_progress" }
// Response — Case
{ "id": 1, "user_id": 1, "run_id": 1, "risk_level": "moderate",
  "status": "in_progress", "created_at": "...", "updated_at": "..." }
```

**Status:** `open` | `in_progress` | `closed`
**Risk level:** `low` | `moderate` | `high` | `critical`

---

## Interventions

### POST /api/interventions ← used by create_intervention_tool
```json
// Request
{ "user_id": 1, "run_id": 3, "meal_suggestion": "...", "activity_suggestion": "...",
  "wellness_action": "...", "empathy_message": "..." }
// Response 201 — Intervention
```

### GET /api/interventions → List[Intervention]
### GET /api/interventions/:id → Intervention
```json
{ "id": 1, "run_id": 1, "user_id": 1,
  "meal_suggestion": "...", "activity_suggestion": "...",
  "wellness_action": "...", "empathy_message": "...", "created_at": "..." }
```

---

## Notifications

### POST /api/notifications ← used by send_notification_tool
```json
// Request
{ "user_id": 1, "type": "intervention_ready", "content": "Your support plan is ready." }
// Response 201 — Notification
```

### GET /api/notifications → List[Notification]
### PUT /api/notifications/:id/delivered → Notification

---

## Resources

### GET /api/resources?persona=student → List[Resource]
```json
[{ "id": 1, "persona_type": "student", "category": "Mental Health",
   "title": "Student Counseling Services", "description": "...", "url": "" }]
```

---

## Scenarios

### GET /api/scenarios
```json
[
  { "id": "stressed_student", "name": "Stressed Student",
    "description": "Finals week...", "persona_type": "student" },
  { "id": "exhausted_caregiver", "name": "Exhausted Caregiver", ... },
  { "id": "older_adult", "name": "Older Adult Routine Disruption", ... }
]
```

### POST /api/scenarios/:scenario_id/run
```json
// Response 201
{ "scenario_id": "stressed_student", "normalized_event_id": 5, "run_id": 3 }
```

---

## Health

### GET /api/health/overview
```json
{
  "latest_date": "2026-03-28",
  "steps": 7842, "step_goal": 8000,
  "active_calories": 380, "total_calories": 2100,
  "resting_hr": 62, "avg_hr": 74,
  "body_battery_high": 85, "body_battery_low": 22,
  "stress_avg": 35, "active_minutes": 48,
  "sleep_hours": 7.2, "sleep_score": 78,
  "garmin_connected": false
}
```

### GET /api/health/daily?days=30 → List[DailyMetrics]
### GET /api/health/sleep?days=30 → List[SleepSession]
### GET /api/health/activities?limit=20 → List[Activity]
### GET /api/health/garmin/auth-status → GarminAuthStatus
### POST /api/health/sync → SyncResult (requires GARMIN_ENABLED=true)

### GET /api/health/calorie-log?log_date=2026-03-28 → List[CalorieLog]
### POST /api/health/calorie-log
```json
// Request
{ "log_date": "2026-03-28", "meal_type": "lunch", "food_name": "Grilled chicken",
  "calories": 350, "quantity": "1 serving", "notes": "", "ai_estimated": false }
```
### DELETE /api/health/calorie-log/:id → 204

### POST /api/health/calorie-log/ai-estimate
```json
// Request
{ "food_name": "Grilled chicken breast", "quantity": "6 oz" }
// Response
{ "food_name": "...", "quantity": "...", "estimated_calories": 280, "confidence": "high" }
```

---

## Recipes

### POST /api/recipes/parse-url
```json
// Request
{ "url": "https://www.allrecipes.com/recipe/..." }
// Response 200 — ParsedRecipe (for review before save)
{
  "title": "Classic Spaghetti Carbonara",
  "description": "...", "source_url": "https://...",
  "prep_minutes": 10, "cook_minutes": 20, "servings": 4,
  "tags": ["italian", "pasta", "quick"],
  "ingredients": [
    { "name": "spaghetti", "quantity": "400g", "category": "Pantry", "section": "" },
    { "name": "pancetta", "quantity": "150g", "category": "Meat", "section": "" }
  ],
  "instructions": "Boil pasta.\nFry pancetta.\n## Make the sauce\nWhisk eggs and cheese.",
  "photo_url": "https://..."
}
```

### POST /api/recipes/parse-text
```json
// Request
{ "text": "<pasted recipe text>" }
// Response 200 — ParsedRecipe (same structure as above)
```

### POST /api/recipes (save after review)
```json
// Request — RecipeIn (same fields as ParsedRecipe minus photo_url, add photo_filename)
{ "title": "...", "ingredients": [...], "instructions": "...", "tags": [...], ... }
// Response 201 — RecipeOut
```

### GET /api/recipes?q=pasta&tag=italian → List[RecipeOut]
### GET /api/recipes/:id → RecipeOut
### DELETE /api/recipes/:id → 204

### GET /api/recipes/meal-plan/slots?week_start=2026-03-25 → List[MealPlanSlot]
### POST /api/recipes/meal-plan/slots → MealPlanSlot
```json
// Request
{ "plan_date": "2026-03-28", "meal_type": "dinner",
  "recipe_id": 1, "custom_name": "", "notes": "" }
```
### DELETE /api/recipes/meal-plan/slots/:id → 204

---

## Error format

All errors follow:
```json
{ "detail": "Human-readable error message" }
```

HTTP status codes:
- 400 — bad request / validation error
- 401 — unauthenticated
- 403 — forbidden
- 404 — not found
- 409 — conflict (e.g. email already registered)
- 422 — unprocessable entity
- 502 — upstream service error (Gemini, Garmin)
