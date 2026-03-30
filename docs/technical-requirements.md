# Technical Requirements — NüMe MVP

This document translates approved business requirements into specific technical requirements for the hackathon MVP. All items are achievable in one day by 4 Codex instances and 1 Claude instance working in parallel.

---

## 1. Authentication and Identity

| Requirement | Priority | MVP |
|---|---|---|
| Require authentication before accessing any dashboard or triggering any agent run | P0 | MVP |
| Use Clerk for identity — Clerk-hosted sign-in, session token verified by backend via PyJWT | P0 | MVP |
| Backend resolves Clerk session token → internal user row (get_or_create on first login) | P0 | MVP |
| Health, case, and recommendation tables must reference internal user ID only — no names or emails | P0 | MVP |
| Support roles: member, coordinator, admin — admin has separate dashboard access | P1 | MVP |
| Support account deletion (soft delete, immediate deactivation) | P2 | Future |

**Acceptance criteria:** A user cannot reach any app screen without a valid Clerk session. Health tables contain no PII columns. Backend auth.py uses `verify_clerk_session_token` + `get_or_create_clerk_user`.

---

## 2. Onboarding and User Profile

| Requirement | Priority | MVP |
|---|---|---|
| Require onboarding completion before the member dashboard is accessible | P0 | MVP |
| Onboarding collects: age range, sex, height, weight, primary goal, activity level, dietary style, allergies, persona type | P0 | MVP |
| Persona type is one of: student, caregiver, older_adult, accessibility_focused | P0 | MVP |
| Store accessibility preferences: simplified_language, large_text, low_energy_mode | P1 | MVP |
| Allow users to update profile and goal after onboarding | P1 | MVP |
| Goal options: stress_reduction, better_sleep, weight_loss, energy_improvement, burnout_recovery | P0 | MVP |

**Acceptance criteria:** Onboarding is a single-page form. Submitting it creates user_profile and redirects to dashboard.

---

## 3. Health Signal Ingestion

| Requirement | Priority | MVP |
|---|---|---|
| Accept health signal events via POST /api/events/ingest | P0 | MVP |
| Supported signal types: sleep_hours, sleep_quality, stress_level, heart_rate, steps, activity_level, check_in_mood, check_in_note | P0 | MVP |
| Provide a wearable simulator endpoint (POST /api/events/simulate) that generates a realistic signal bundle for a named scenario | P0 | MVP |
| Provide a manual check-in form in the member UI | P0 | MVP |
| Persist all raw signal events to wearable_events or behavior_events table | P0 | MVP |
| Normalize raw events into a normalized_events record before agent dispatch | P0 | MVP |
| Real Garmin OAuth integration | P2 | Future |

**Acceptance criteria:** Submitting a manual check-in or triggering a simulation creates normalized event records and queues an agent run.

---

## 4. Agent System — Google ADK

All agents must be implemented as real Google ADK agents using the Python ADK SDK. Do not simulate ADK with plain functions or generic LLM calls.

### 4.1 Agent roster

| Agent | Type | Role |
|---|---|---|
| Care Coordinator | Root / SequentialAgent | Orchestrates the full pipeline; dispatches parallel phase, collects results, runs loop, triggers escalation |
| Signal Interpretation | Specialist (local) | Analyzes normalized signals and produces structured findings (stress_spike, sleep_decline, etc.) |
| Risk Stratification | Specialist (local) | Assigns risk level (low / moderate / high / critical), urgency, confidence score |
| Intervention Planning | Specialist (local) | Proposes meal suggestion, activity recommendation, wellness action based on findings and persona |
| Empathy and Check-In | Specialist (local) | Converts findings into supportive, non-judgmental user-facing language |
| Validation Loop | LoopAgent | Checks plan for contradictions, policy violations, accessibility mismatches; refines or halts |
| Student Support Specialist | Remote A2A | Academic stress interpretation, campus resource routing, burnout-sensitive planning |
| Caregiver Burnout Specialist | Remote A2A | Caregiver burden interpretation, respite resource routing, realistic micro-intervention planning |

### 4.2 Execution model

| Requirement | Priority | MVP |
|---|---|---|
| Use ParallelAgent to run Signal Interpretation, Risk Stratification, and Intervention Planning concurrently | P0 | MVP |
| Use LoopAgent for validation phase (max 3 iterations before forced approval or halt) | P0 | MVP |
| Coordinator selects the correct A2A specialist based on persona type and dispatches via RemoteA2aAgent | P0 | MVP |
| Each agent receives a structured input dict and returns a structured output dict | P0 | MVP |
| Agent must not own persistent state — all reads and writes go through platform service API calls (tools) | P0 | MVP |
| Every agent run, input, output, and iteration must be persisted to agent_runs and agent_messages tables | P0 | MVP |

**Acceptance criteria:** Running a scenario produces a trace with distinct parallel branch records and at least one loop iteration record. A2A invocation is logged separately from local agent calls.

### 4.3 ADK tool layer

| Tool | Purpose |
|---|---|
| ingest_signal_tool | Write normalized event to DB via API |
| get_user_profile_tool | Read user profile and accessibility preferences |
| get_recent_signals_tool | Read last N signal events for a user |
| create_case_tool | Create a support case record |
| create_intervention_tool | Persist the final intervention plan |
| send_notification_tool | Write a notification record (no live push in MVP) |
| get_resources_tool | Look up persona-appropriate resources from a static resource table |
| persist_audit_tool | Write an audit log entry |

**Acceptance criteria:** No agent constructs a DB query directly. All state changes go through tool calls.

---

## 5. Platform Services (FastAPI)

| Service area | Requirement | Priority |
|---|---|---|
| Auth | JWT issue and validation | P0 |
| User profile | CRUD for user_profiles and accessibility_preferences | P0 |
| Event ingestion | POST /api/events/ingest, POST /api/events/simulate | P0 |
| Agent dispatch | POST /api/runs/trigger — kicks off coordinator agent for a user | P0 |
| Case management | CRUD for cases (create, read, update status) | P0 |
| Interventions | Write and read intervention records | P0 |
| Notifications | Write notification records (queued, delivered status) | P1 |
| Resources | Seeded resource table; GET /api/resources?persona=student | P1 |
| Trace | GET /api/runs/:id — full trace with agent messages | P0 |
| Audit log | Append-only audit_logs; no delete endpoint | P1 |

**Acceptance criteria:** All agent tool calls resolve to one of these service endpoints. No agent imports SQLAlchemy directly.

---

## 6. Database Schema

Tables required for MVP:

- `users` — id, email (hashed or pseudonymized), clerk_user_id, role, created_at
- `user_profiles` — id, user_id, age_range, sex, height_cm, weight_kg, goal, activity_level, dietary_style, allergies, persona_type, created_at
- `accessibility_preferences` — user_id, simplified_language, large_text, low_energy_mode
- `wearable_events` — id, user_id, source (simulated|manual|garmin_future), signal_type, value, unit, recorded_at
- `behavior_events` — id, user_id, event_type, payload (JSON), recorded_at
- `normalized_events` — id, user_id, signals (JSON), summary, created_at
- `agent_runs` — id, user_id, normalized_event_id, status, started_at, completed_at, risk_level
- `agent_messages` — id, run_id, agent_name, agent_type (local|a2a|parallel|loop), input (JSON), output (JSON), iteration, duration_ms, created_at
- `cases` — id, user_id, run_id, risk_level, status (open|in_progress|closed), created_at, updated_at
- `interventions` — id, run_id, user_id, meal_suggestion, activity_suggestion, wellness_action, empathy_message, created_at
- `notifications` — id, user_id, type, content, status (queued|delivered), created_at
- `resources` — id, persona_type, category, title, description, url
- `audit_logs` — id, user_id, action, entity_type, entity_id, metadata (JSON), created_at

**Additional tables proven pattern:**
- `health_daily_metrics` — user_id, metric_date, steps, step_goal, active_calories, total_calories, resting_hr, avg_hr, body_battery_high, body_battery_low, stress_avg, intensity_minutes_moderate, intensity_minutes_vigorous, floors_climbed, spo2_avg, hrv_weekly_avg, hrv_status, vo2_max, active_minutes, raw_json, synced_at — unique on (user_id, metric_date)
- `health_sleep_sessions` — user_id, sleep_date, sleep_start, sleep_end, duration_seconds, deep_seconds, light_seconds, rem_seconds, awake_seconds, sleep_score, avg_spo2, avg_respiration, raw_json, synced_at — unique on (user_id, sleep_date)
- `health_activities` — user_id, garmin_activity_id, activity_type, activity_name, start_time, duration_seconds, distance_meters, calories, avg_hr, max_hr, elevation_gain_meters, avg_speed_mps, training_load, raw_json, synced_at — unique on (user_id, garmin_activity_id)
- `health_sync_runs` — user_id, status, sync_type, started_at, finished_at, metrics_upserted, activities_upserted, sleep_upserted, error_text, details_json
- `health_calorie_log` — user_id, log_date, meal_type, food_name, calories, quantity, notes, ai_estimated, created_at
- `recipes` — user_id, title, description, source_url, our_way_notes, prep_minutes, cook_minutes, servings, tags (JSONB), ingredients (JSONB), instructions (text), photo_filename, created_at
- `meal_plan_slots` — user_id, plan_date, meal_type, recipe_id (FK nullable), custom_name, notes, created_at

Use Alembic for migrations. Seed data must be committed.

---

## 7. Frontend (Vite/React SPA)

| Screen | Required content | Priority |
|---|---|---|
| Member dashboard | Current signal summary, most recent support plan (meal, activity, wellness), empathy message, risk badge, link to trace | P0 |
| Care coordinator dashboard | Open cases list with persona type, risk level, created_at, status; click to view member summary | P0 |
| Trace / admin dashboard | Agent run list; click run to see full message tree with parallel branches, A2A calls, loop iterations, final action | P0 |
| Scenario runner | Dropdown of seeded scenarios; trigger button; live status polling; auto-navigate to trace on completion | P0 |
| Onboarding | Single-page form; redirects to member dashboard on submit | P0 |
| Manual check-in | Short form (mood, sleep hours, stress level, note); submits signal event and triggers run | P1 |

**Stack:** Vite + React + TypeScript, React Router, Clerk React SDK, shadcn/ui, Tailwind CSS, TanStack Query for polling.

**Acceptance criteria:** All screens render without error on first load. Trace view clearly distinguishes parallel vs sequential vs A2A vs loop agent messages.

---

## 8. Demo Scenarios (seeded)

Two scenarios must be fully seeded and runnable through the scenario runner:

**Scenario 1: Stressed Student**
- Signals: sleep 4.5h, stress 8/10, mood negative, 800 steps
- Expected: Student Support Specialist invoked via A2A; moderate-high risk; campus resource included; case created

**Scenario 2: Exhausted Caregiver**
- Signals: sleep 5h, stress 9/10, activity low, check-in "completely drained"
- Expected: Caregiver Burnout Specialist invoked via A2A; high risk; respite resource; coordinator case created; empathy message warm

**Scenario 3 (optional): Older Adult Routine Disruption**
- Signals: steps very low, sleep fragmented, missed morning check-in
- Expected: risk elevated; simplified plan; accessibility adaptations applied

---

## 9. Security and Reliability

| Requirement | Priority |
|---|---|
| Rate limit AI-triggering endpoints (POST /api/runs/trigger, POST /api/events/simulate) | P1 |
| Secrets in environment variables only; no hardcoded keys | P0 |
| Graceful degradation if Gemini API is unavailable (log error, return partial plan) | P1 |
| Structured JSON logging for all agent calls and tool executions | P1 |
| Docker Compose local dev with no external service dependencies beyond Gemini API | P0 |

---

## 9b. Garmin Integration (proven pattern)

The Garmin integration already worked end-to-end in Nest. This is a port job. Adapt by replacing `person` column with `user_id` FK and swapping aiosqlite for SQLAlchemy async + PostgreSQL.

| Requirement | Priority |
|---|---|
| Garmin OAuth bootstrap: credentials in env vars, MFA-capable, writes oauth1_token + oauth2_token per user to token cache directory | P1 |
| Background scheduled sync: daily metrics, sleep, activities, upsert into local tables | P1 |
| Manual sync trigger: POST /api/health/sync | P1 |
| All health reads come from local DB only — never live from Garmin | P0 |
| Store: steps, step_goal, active_calories, total_calories, resting_hr, avg_hr, body_battery_high/low, stress_avg, intensity_minutes, floors, spo2_avg, hrv_weekly_avg, hrv_status, vo2_max, active_minutes | P1 |
| Store sleep: duration, deep/light/rem/awake seconds, sleep_score, avg_spo2, avg_respiration | P1 |
| Store activities: activity_type, name, start_time, duration, distance, calories, avg_hr, max_hr, training_load | P1 |
| Sync audit table: status, sync_type, started_at, finished_at, metrics_upserted, error_text | P1 |
| Garmin auth status endpoint: GET /api/health/garmin/auth-status | P1 |
| Fallback: if Garmin not connected, app works in manual entry mode | P0 |

**DB tables (adapt `person` → `user_id`):**
- `health_daily_metrics` — unique on (user_id, metric_date), upsert on sync
- `health_sleep_sessions` — unique on (user_id, sleep_date)
- `health_activities` — unique on (user_id, garmin_activity_id)
- `health_sync_runs` — append-only audit
- `health_calorie_log` — manual food log with AI estimate support

**Acceptance criteria:** User connects Garmin, sync runs, daily metrics appear in dashboard. If Garmin is disconnected, manual entry still works.

---

## 9c. Recipe Parsing (proven pattern)

The full recipe pipeline already worked in Nest. This is a port job.

| Requirement | Priority |
|---|---|
| Import recipe from URL: safe fetch → recipe-scrapers → JSON-LD extraction → grouped ingredient extraction → review UI → save | P1 |
| Import recipe from pasted text: send to Gemini → structured JSON → normalize → review UI → save | P1 |
| URL safety: validate scheme/hostname, reject private/local destinations, enforce byte limit | P1 |
| Instruction extraction priority: JSON-LD recipeInstructions → scraper list → scraper text | P1 |
| Ingredient extraction priority: known grouped HTML (Tasty Recipes, WP Recipe Maker) → scraper groups → scraper raw | P1 |
| Quantity splitting: separate leading quantity text from ingredient name via regex | P1 |
| Recipe photo: support upload and remote image URL import; content-type + magic-byte validation | P2 |
| Review-before-save: parsed result shown to user for review before writing to DB | P0 |
| Duplicate detection | P2 (future) |

**DB schema:**
```
recipes:
  id, title, description, source_url, our_way_notes,
  prep_minutes, cook_minutes, servings, tags (JSON array),
  ingredients (JSON array of {name, quantity, category, section}),
  instructions (newline text, ## for section headers),
  photo_filename, user_id, created_at
```

**Acceptance criteria:** 90%+ of standard recipe URLs parse successfully. Pasted text produces a reviewable structured result. Grouped ingredients and instruction sections are preserved.

---

## 9d. Recipe Display and Search (proven pattern)

| Requirement | Priority |
|---|---|
| Recipe list with text search by title | P1 |
| Tag chip filtering | P1 |
| Recipe cards: photo, total time, servings | P1 |
| Recipe detail: title, image, time, servings, tags, grouped ingredients, grouped instructions, notes, source link | P1 |
| Ingredient section grouping (section field) | P1 |
| Instruction section headers (## prefix lines render unnumbered) | P1 |
| Ingredient reference highlighting in instructions (tap/hover shows quantity) | P2 |

---

## 9e. Meal Planning (proven pattern)

| Requirement | Priority |
|---|---|
| Weekly meal plan slots: plan_date + meal_type (breakfast/lunch/dinner/snack) | P2 |
| Link slot to recipe from recipe catalog | P2 |
| Custom meal name when no recipe selected | P2 |
| Display recipe title and description from linked recipe | P2 |
| Grocery list generation from linked recipe ingredients | P2 |

**DB schema:**
```
meal_plan_slots:
  id, user_id, plan_date, meal_type, recipe_id (FK nullable),
  custom_name, notes, created_at
```

---

## 10. Explicit future phase items

- Live Garmin OAuth + webhook sync
- Recipe parsing from URL
- Apple Health
- Push notifications
- Vector database + semantic search
- Similar-user clustering
- Multi-role admin
- Persistent conversational memory
- Advanced recovery logic (HRV-based)
- Senior Wellness and Accessibility Coach A2A specialists
