# Work Split — NüMe Hackathon

Four people. Each owns a clean domain with no overlapping files. Integration happens at the end.

---

## Step 0 — Fab does this before anyone else starts (~30–45 min)

Before the team splits, Fab sets up the foundation everyone depends on:

1. Create the full monorepo directory structure (empty folders + placeholder files)
2. Commit `packages/shared-types/` with core Pydantic models
3. Commit `.env.example` with all required variables
4. Commit `docker-compose.yml` stubs for all services
5. Commit `docs/api-contracts.md` so everyone knows what endpoints to code against

Shared types that must exist before anyone builds:
- `UserProfile`, `AccessibilityPreferences`
- `NormalizedEvent`, `SignalType`
- `AgentRunRecord`, `AgentMessage`
- `InterventionPlan` (meal_suggestion, activity_suggestion, wellness_action, empathy_message)
- `RiskLevel` enum (low, moderate, high, critical)
- `CaseRecord`, `NotificationRecord`
- `Recipe`, `RecipeIngredient`, `MealPlanSlot`
- `HealthDailyMetrics`, `HealthSleepSession`, `HealthActivity`

Once this is pushed to `main`, everyone branches off and works independently.

---

## Person 1 (Fab) — Backend, Garmin, and Recipe Parsing

**Branch:** `feat/backend`

**Directory ownership:** `apps/api/`, `infra/`, `packages/shared-types/`

**Deliverables:**

Backend platform services:
- SQLAlchemy models for all tables (see technical-requirements.md §6)
- Alembic migration for initial schema
- FastAPI routers: auth, profile, onboarding, events, agent runs, cases, interventions, notifications, resources, scenarios
- JWT auth middleware
- Wearable simulator endpoint (POST /api/events/simulate) — used when Garmin is not connected
- Seed script: 2 demo users, 2 demo scenarios, resource table, sample health data

Garmin integration:
- OAuth bootstrap: credential-based, MFA-capable, writes token cache per user
- Background sync: daily metrics, sleep, activities — upsert into local tables
- Manual sync trigger: POST /api/health/sync
- Health read endpoints: GET /api/health/overview, /daily, /sleep, /activities
- Calorie log: GET/POST/DELETE /api/health/calorie-log, GET /api/health/calorie-log/ai-estimate
- Garmin status: GET /api/health/garmin/auth-status

Recipe parsing:
- URL import: safe fetch → recipe-scrapers → JSON-LD extraction → grouped ingredient extraction
- Paste import: Gemini structured JSON extraction → normalize
- Endpoints: POST /api/recipes/parse-url, POST /api/recipes/parse-text
- Recipe CRUD: POST /api/recipes (save after review), GET /api/recipes, GET /api/recipes/:id

Docker + infra:
- `docker-compose.yml` — all services wired with healthchecks
- `infra/seed/seed.py` — runnable seed script
- `infra/migrations/` — Alembic migrations verified

**Does NOT build:** agents, A2A specialists, tool layer, frontend

**Setup guide:** `docs/setup/backend.md`

---

## Person 2 — Google ADK Local Agents

**Branch:** `feat/agents`

**Directory ownership:** `services/agents/`

**Deliverables:**
- `coordinator/` — SequentialAgent root; orchestrates the full pipeline
- `signal_interpretation/` — LlmAgent; analyzes signals, returns structured findings
- `risk_stratification/` — LlmAgent; assigns risk level and confidence
- `intervention_planning/` — LlmAgent; proposes meal, activity, wellness actions
- `empathy_checkin/` — LlmAgent; converts plan into supportive user-facing language
- `validation_loop/` — LoopAgent wrapping a validator LlmAgent; max 3 iterations
- ParallelAgent wiring across signal_interpretation, risk_stratification, intervention_planning
- Coordinator uses RemoteA2aAgent to call student_support or caregiver_burnout based on persona_type
- All agents use shared Pydantic models for typed input/output
- All agents call `persist_audit_tool` to log messages

**Coding against the API without Fab's server running:**
Use the mock API responses in `docs/api-contracts.md`. Run `json-server` or return hardcoded fixtures from tool stubs during development.

**Does NOT build:** A2A servers, tool layer HTTP calls, frontend, FastAPI

**Setup guide:** `docs/setup/agents.md`

---

## Person 3 — A2A Remote Specialists and Tool Layer

**Branch:** `feat/specialists`

**Directory ownership:** `services/remote_specialists/`, `services/tools/`

**Deliverables:**

ADK tool layer (`services/tools/`):
- `get_user_profile_tool.py`
- `get_recent_signals_tool.py`
- `create_case_tool.py`
- `create_intervention_tool.py`
- `send_notification_tool.py`
- `get_resources_tool.py`
- `persist_audit_tool.py`
- All tools call FastAPI via HTTP using `API_BASE_URL` from env
- All tools wrapped as ADK `FunctionTool`
- Tools handle HTTP errors gracefully (retry once, then raise)

Remote A2A specialists:
- `student_support/` — LlmAgent; academic stress interpretation, campus resource routing
- `caregiver_burnout/` — LlmAgent; caregiver burden interpretation, respite resource routing
- Each specialist exposed via `adk api_server --a2a` with an `agent_card.json`
- Student Support on port 8001, Caregiver Burnout on port 8002

**Coding against the API without Fab's server running:**
Tools should read `API_BASE_URL` from env. Point it at a local mock server or use the fixtures in `docs/api-contracts.md` during development.

**Does NOT build:** local ADK agents, FastAPI routes, frontend

**Setup guide:** `docs/setup/specialists.md`

---

## Person 4 — Frontend (Next.js)

**Branch:** `feat/frontend`

**Directory ownership:** `apps/web/`

**Deliverables:**
- Auth pages: login, register
- Onboarding: single-page form, submits to POST /api/onboarding
- Member dashboard: signal summary, support plan (meal, activity, wellness cards), empathy message, risk badge
- Health dashboard: overview cards (steps, sleep, HR, stress), trend charts, sleep history, activity feed
- Garmin connect UI: auth status banner, connect button, manual sync button
- Recipe list: text search, tag filter chips, recipe cards
- Recipe detail: grouped ingredients, grouped instruction sections, source link
- Recipe import form: URL input tab + paste text tab, review-before-save step
- Care coordinator dashboard: open cases table (persona, risk level, status)
- Trace dashboard: agent run list → run detail with message tree (parallel/A2A/loop visually distinct)
- Scenario runner: dropdown, trigger button, live status polling, auto-redirect to trace
- Manual check-in form: mood, sleep hours, stress level, optional note
- API client layer: `lib/api.ts` with typed wrappers for all endpoints
- React Query for all data fetching and scenario runner polling
- PWA setup: `next-pwa`, `manifest.json`, app icon

**Coding against the API without Fab's server running:**
Use MSW (Mock Service Worker) or hardcoded fixtures in `lib/api.ts` during development. The API contract in `docs/api-contracts.md` defines all response shapes.

**Does NOT build:** API routes, agents, tools

**Setup guide:** `docs/setup/frontend.md`

---

## Merge order

Merge to `main` in this order to avoid integration conflicts:

```
1. Fab merges feat/backend → main  (API is live, DB is seeded)
2. Person 3 merges feat/specialists → main  (tools now have a real API to call)
3. Person 2 merges feat/agents → main  (agents now have real tools)
4. Person 4 merges feat/frontend → main  (UI now has a real API)
```

Before each merge, the person should run their piece against the real API and confirm it works.

---

## File ownership map

No two people should ever edit the same file. If you need something from another domain, ask that person to add it.

```
apps/api/               → Fab only
apps/web/               → Person 4 only
services/agents/        → Person 2 only
services/remote_specialists/  → Person 3 only
services/tools/         → Person 3 only
packages/shared-types/  → Fab commits first; changes require team agreement
infra/                  → Fab only
docs/                   → anyone, no conflicts expected
```

---

## Dependency map

```
packages/shared-types  ←── everyone depends on this (Fab sets up first)
        │
        ├── apps/api  ←── services/tools (tools call API endpoints)
        │             ←── apps/web (frontend calls API endpoints)
        │
        ├── services/agents  ←── services/tools (agents use tools)
        │
        └── apps/web  — independent of agents; only talks to API
```
