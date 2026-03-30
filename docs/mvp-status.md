# NüMe MVP Status — 2026-03-29

Source of truth for what is built, what is wired, and what remains for a complete demo-day MVP.

---

## Legend

- `[x]` Done / confirmed working
- `[~]` Partially done or needs verification
- `[ ]` Not yet done

---

## Phase 1 — Infrastructure and Auth

- `[x]` FastAPI app boots with lifespan, CORS, structured logging
- `[x]` PostgreSQL schema via Alembic migrations (001_initial_schema)
- `[x]` Clerk auth: `verify_clerk_session_token` + `get_or_create_clerk_user`
- `[x]` `get_current_user` and `get_current_admin` FastAPI dependencies
- `[x]` Docker Compose wires `api`, `web`, `db`, `specialist-student`, `specialist-caregiver`
- `[~]` `get_current_coordinator` dependency — role exists in DB and seed; no dedicated guard yet
- `[ ]` Rate limiting on `POST /api/runs/trigger` and `POST /api/events/simulate`

---

## Phase 2 — Onboarding and User Profile

- `[x]` `POST /api/onboarding` — creates `user_profiles` + `accessibility_preferences`
- `[x]` `GET /api/profile`, `PUT /api/profile`
- `[x]` `GET /api/profile/accessibility`, `PUT /api/profile/accessibility`
- `[x]` Persona types: student, caregiver, older_adult, accessibility_focused
- `[x]` Goal options: stress_reduction, better_sleep, weight_loss, energy_improvement, burnout_recovery
- `[~]` Frontend onboarding form — page exists (`OnboardingPage.tsx`); needs verification that submit → redirect to dashboard works end-to-end
- `[ ]` Gate: redirect unonboarded users away from member dashboard

---

## Phase 3 — Health Signal Ingestion

- `[x]` `POST /api/events/ingest` — writes to `wearable_events`
- `[x]` `POST /api/events/simulate` — generates scenario bundle + `normalized_events` record
- `[x]` `GET /api/events/recent`
- `[x]` Normalization: `normalized_events` row created before agent dispatch
- `[~]` Frontend manual check-in form (`CheckInPage.tsx`) — page exists; needs end-to-end test
- `[ ]` Garmin OAuth + background sync (P1 — back in scope but not yet ported)

---

## Phase 4 — Agent Pipeline

- `[x]` Custom multi-agent orchestrator wired and running:
  - `execute_parallel` (ThreadPoolExecutor) for Signal Interpretation, Risk Stratification, Intervention Planning
  - A2A specialist selection by persona type (student → StudentSupport, caregiver → CaregiverBurnout, other → local Accessibility agent)
  - Empathy and Check-In agent
  - Validation Loop (up to 3 iterations)
- `[x]` `GeminiJsonClient` — direct Gemini 2.0 Flash calls with JSON output
- `[x]` `adk_compat.py` — structural bridge; imports real Google ADK when installed, falls back to dataclass stubs
- `[x]` All agent outputs persisted to `agent_messages` via `persist_run_message_tool`
- `[x]` Intervention, case, notification, and audit records written at end of run
- `[~]` Remote specialists (`specialist-student`, `specialist-caregiver`) — FastAPI services exist; need to confirm they are healthy in Docker Compose and reachable by coordinator
- `[ ]` Real Google ADK runtime installed and wired (currently falls back to custom orchestrator)
- `[ ]` Real ADK `adk api_server --a2a` for specialists (currently plain FastAPI `/invoke` endpoint)

---

## Phase 5 — Platform API (FastAPI)

- `[x]` `GET /api/auth/me`
- `[x]` `POST /api/runs/trigger`, `GET /api/runs`, `GET /api/runs/:id` (trace)
- `[x]` `PUT /api/runs/:id` (coordinator updates status + risk_level)
- `[x]` `POST /api/runs/messages`
- `[x]` `POST /api/cases`, `GET /api/cases`, `GET /api/cases/:id`, `PUT /api/cases/:id/status`
- `[x]` `POST /api/interventions`, `GET /api/interventions`, `GET /api/interventions/:id`
- `[x]` `POST /api/notifications`, `GET /api/notifications`, `PUT /api/notifications/:id/delivered`
- `[x]` `GET /api/resources?persona=...`
- `[x]` `GET /api/scenarios`, `POST /api/scenarios/:id/run`
- `[x]` `POST /api/audit-logs`
- `[x]` Health data endpoints: overview, daily, sleep, activities, calorie log, AI estimate
- `[~]` `GET /api/health/garmin/auth-status`, `POST /api/health/sync` — endpoints exist; Garmin integration not wired for demo

---

## Phase 6 — Frontend Screens (Vite/React)

- `[x]` Clerk auth integrated (`@clerk/clerk-react`)
- `[x]` Member Dashboard (`MemberDashboard.tsx`)
- `[x]` Coordinator Dashboard (`CoordinatorDashboard.tsx`)
- `[x]` Scenario Runner (`ScenarioRunner.tsx`)
- `[x]` Trace list (`TracesListPage.tsx`) and trace detail (`TraceView.tsx`)
- `[x]` Onboarding (`OnboardingPage.tsx`)
- `[x]` Manual Check-In (`CheckInPage.tsx`)
- `[x]` Health Dashboard (`HealthDashboard.tsx`)
- `[x]` Recipe list and detail (`RecipeListPage.tsx`, `RecipeDetailPage.tsx`)
- `[~]` Role-based routing — coordinator role exists in seed and backend; frontend routing guard by role needs verification
- `[ ]` Trace view distinguishes parallel / loop / a2a / local visually — needs demo-day verification

---

## Phase 7 — Seed Data and Demo Scenarios

- `[x]` `infra/seed/seed.py` — 10 demo users (8 members + coordinator + admin) across all 4 personas
- `[x]` 14 days of health data per member (deterministic by preset)
- `[x]` Resources seeded for all 4 persona types
- `[x]` Scenario definitions: `stressed_student`, `exhausted_caregiver`, `older_adult`
- `[~]` Seed registers users with email only — Clerk users not pre-created; demo needs manual Clerk sign-up or a `clerk_user_id` pre-seed step
- `[ ]` Verify end-to-end: scenario runner → agent run → trace visible in UI in < 30 seconds

---

## Phase 8 — Recipes and Meal Planning

- `[x]` Recipe parse from URL (`POST /api/recipes/parse-url`)
- `[x]` Recipe parse from pasted text (`POST /api/recipes/parse-text`)
- `[x]` Recipe save, list, detail, delete
- `[x]` Meal plan slots (create, list by week, delete)
- `[~]` Calorie log AI estimate (`POST /api/health/calorie-log/ai-estimate`) — endpoint exists; Gemini call needs smoke test

---

## Known Gaps to Resolve Before Demo Day

| Gap | Severity | Notes |
|---|---|---|
| Seed users have no Clerk account — `/api/auth/me` won't find them without a matching `clerk_user_id` | High | Need Clerk dev-instance pre-seeded users or a seed script that calls Clerk Management API |
| `get_current_coordinator` guard not implemented — coordinator dashboard may be accessible to any authenticated user | Medium | Add role check or at minimum gate in frontend |
| Rate limiting absent on run/simulate endpoints | Low | Add `slowapi` limiter before demo |
| Real ADK runtime not installed | Low for demo | Custom orchestrator is fully functional; install ADK only if Google judges need it |
| Specialist services healthcheck in Docker Compose | Medium | Add `healthcheck:` entries so coordinator doesn't call an unready specialist |
| Scenario runner end-to-end smoke test not documented | High | Run once before demo day; fix any 422/500 errors |

---

## Out of Scope (not expected for hackathon demo)

- Live Garmin OAuth / webhook sync
- Apple Health integration
- Push notifications (live delivery)
- Vector database / semantic search
- Similar-user clustering
- Persistent conversational memory
- Multi-tenant / multi-org admin
