# NüMe Personalization Layer Update Plan

Last verified: 2026-04-05

This document is the durable handoff plan for replacing the current thin, prompt-heavy personalization flow with a shared personalization/state layer, deterministic scoring and ranking, and structured support-plan outputs.

If context is compacted or reset, resume from this file first.

## Execution Status

Current execution state as of 2026-04-05:

- Ticket 1 is complete and verified with `scripts/verify_ticket_01_schema.sh`
- Ticket 2 is complete and verified with `scripts/verify_ticket_02_personalization_context.sh`
- Ticket 3 is complete and verified with `scripts/verify_ticket_03_risk_normalization.sh`
- Ticket 4 is complete and verified with `scripts/verify_ticket_04_recipe_nutrition_fields.sh`
- Ticket 5 is complete and verified with `scripts/verify_ticket_05_recipe_ranking.sh`
- Ticket 6 is complete and verified with `scripts/verify_ticket_06_activity_wellness_planner.sh`
- Ticket 7 is complete and verified with `scripts/verify_ticket_07_support_plan_endpoint.sh`
- Ticket 8 is complete and verified with `scripts/verify_ticket_08_frontend_support_plan_cutover.sh`
- Do not start Ticket 9 or later until explicitly requested

Last verified command:

- `scripts/verify_ticket_08_frontend_support_plan_cutover.sh`

## Goal

Replace the current `profile + recent raw signals + prompt tuning` approach with:

- A shared `PersonalizationContext` / `PersonalizationStateSnapshot`
- Deterministic state features, risk subscores, and candidate ranking
- Structured persisted support plans
- A real frontend contract for the current support plan
- Feedback logging that can later support learned ranking

## Product Principles

- Keep LLMs for interpretation, adaptation, explanation, and empathetic copy
- Use deterministic logic for state building, risk scoring, eligibility checks, constraints, ranking, and change detection
- Do not use `persona_type` as the primary personalization layer
- Keep `persona_type` for onboarding metadata, coarse routing, and resource lookup only
- Start with interpretable scores, not unsupervised clustering
- Build logs first, then consider ML later

## Environment Assumptions

- The API Python environment already exists at `apps/api/.venv`
- Do not create a second API virtualenv unless the user explicitly requests it
- Secrets are managed through Doppler using the `dev` config
- Prefer verification commands and scripts that can be run with Doppler-injected env vars
- Production deployment runs on Cloudflare, so verification scripts should not hardcode assumptions that only work in one local container layout unless the script is explicitly local-only
- Where possible, make scripts work from env vars such as:
  - `API_URL`
  - `INTERNAL_API_TOKEN`
  - `SMOKE_USER_EMAIL`
  - any additional per-ticket settings

## Verified Current State

These points were verified directly in the codebase on 2026-04-04.

### Coordinator input is too thin

- `services/agents/coordinator/agent.py`
  - `_load_run_context()` only loads:
    - `profile = tool_provider.get_user_profile(...)`
    - `raw_signals = tool_provider.get_recent_signals(...)`
    - `resources = tool_provider.get_resources(persona_type)`
  - It flattens signals into a single dict with:
    - `signals = {item["signal_type"]: item["value"] for item in raw_signals}`
- `services/agents/tooling.py`
  - `ToolProvider` exposes `get_user_profile()` and `get_recent_signals()`
  - There is no shared personalization context tool in use

### Live runs do not use the real health tables as the main source of truth

- `services/tools/get_recent_signals_tool.py`
  - `get_recent_signals()` calls `GET /api/events/recent`
- `apps/api/routers/events.py`
  - `/api/events/recent` returns recent `WearableEvent` rows only
  - `/api/events/checkin` writes only:
    - `check_in_mood`
    - `sleep_hours`
    - `stress_level`
    - optional `check_in_note`
  - Then it creates a `NormalizedEvent` summary and schedules the coordinator
- `apps/api/garmin_sync.py`
  - Garmin sync writes a `NormalizedEvent` snapshot of health data
  - It does not write `WearableEvent` rows for the synced health snapshot
  - Since the coordinator currently reads `/api/events/recent`, Garmin health data is not reliably the same input path as live check-ins

### Risk fallback is biased upward

- `services/agents/risk_stratification/agent.py`
  - `_derive_findings()` currently adds:
    - `{"type": "negative_checkin", "severity": "moderate"}`
    - whenever `signals.get("check_in_mood")` or `signals.get("check_in_note")` exists
  - This means any check-in can become a distress signal
- `services/agents/signal_interpretation/agent.py`
  - Fallback logic is slightly better than risk fallback
  - It only emits `negative_checkin` for certain negative mood/note tokens
  - But risk fallback still independently re-derives findings from the raw signals

### `persona_type` is still treated like the primary user state

- `apps/api/models/user.py`
  - `UserProfile.persona_type` is a stored field
- `apps/api/routers/profile.py`
  - onboarding writes `persona_type` directly
- `services/agents/coordinator/agent.py`
  - specialist routing depends on `persona_type`
- `apps/api/models/agents.py`
  - `Resource.persona_type` is how resources are scoped

Conclusion:

- Keep `persona_type`
- Demote it from primary personalization logic
- Do not remove it from onboarding, specialists, or resources

### Planning is too generic and too text-centric

- `services/agents/intervention_planning/agent.py`
  - fallback produces generic meal/activity/wellness suggestions
  - `meal_constraints` are heuristically derived tags
  - no catalog retrieval or ranking exists before plan composition
- `services/agents/coordinator/agent.py`
  - `_finalize_run()` reduces the final plan to:
    - `meal_suggestion`
    - `activity_suggestion`
    - `wellness_action`
    - `empathy_message`
    - `meal_constraints`
  - then persists via `tool_provider.create_intervention(...)`

### Intervention persistence is flat

- `apps/api/models/agents.py`
  - `Intervention` stores:
    - `meal_suggestion`
    - `activity_suggestion`
    - `wellness_action`
    - `empathy_message`
    - `meal_constraints`
  - There is no persisted `recipe_id`, `snapshot_id`, ranked alternatives, or risk subscores
- `apps/api/routers/interventions.py`
  - `/api/interventions` creates and returns only the flat record

### Dashboard contract is stitched together from old data

- `apps/web/src/lib/api.ts`
  - `getSupportPlanLive()` fetches:
    - `/api/interventions`
    - `/api/runs`
  - It uses the latest intervention plus matching run risk level
- `apps/web/src/lib/api-mappers.ts`
  - `mapInterventionToSupportPlan()` flattens strings into three cards
- `apps/web/src/lib/types.ts`
  - `SupportPlan` is only:
    - `meal`
    - `activity`
    - `wellness`
    - `empathy_message`
    - `risk_level`
    - optional `confidence`
- `apps/web/src/pages/MemberDashboard.tsx`
  - the dashboard is built around that minimal shape

### Recipe recommendation is tag-overlap only

- `apps/api/models/recipes.py`
  - recipes do not yet have nutrition or effort metadata
- `apps/api/routers/recipes.py`
  - `GET /api/recipes/recommended`
  - loads the latest intervention
  - reads `meal_constraints`
  - ranks template recipes by tag overlap only
- `apps/web/src/pages/RecipeListPage.tsx`
  - page copy explicitly says recommendations come from the latest intervention and its meal constraints

## Target Architecture

### Shared runtime object

Add a shared `PersonalizationContext` / `PersonalizationStateSnapshot` that includes:

- Static profile
  - goal
  - dietary style
  - allergies
  - activity level
  - demographics already stored
  - accessibility preferences
- Dynamic state
  - sleep debt
  - stress load
  - recovery score
  - activity capacity
  - prep capacity
  - calorie balance
  - protein gap
  - adherence score
  - routine stability
  - note sentiment summary
  - recent check-in summary
- Archetype scores
  - `student_overload`
  - `caregiver_burden`
  - `low_energy_recovery`
  - `routine_rebuild`
  - `accessibility_support`
  - `performance_ready`
- Recent context
  - 1-day, 7-day, and 30-day health aggregates
  - calorie log summaries
  - recipe usage and repetition
  - intervention outcomes
  - user feedback on prior plans

### State and planning flow

New flow:

1. Build snapshot from deterministic sources
2. Score state and archetypes
3. Score risk using deterministic subscores
4. Retrieve eligible meal/activity/wellness candidates
5. Rank candidates deterministically
6. Let the LLM explain and adapt the chosen options
7. Persist structured support-plan objects plus compatibility text fields

### LLM role after refactor

LLMs should:

- Explain why the selected support plan fits today
- Rewrite rationale in accessible language if needed
- Adapt tone and empathy
- Summarize change from yesterday using deterministic diff inputs

LLMs should not:

- invent risk levels
- invent eligibility
- invent constraint handling
- choose recipes directly from the whole catalog without ranking

## Existing Data Sources To Use

Use these as inputs to the snapshot builder:

- `apps/api/models/user.py`
  - `UserProfile`
  - `AccessibilityPreferences`
- `apps/api/models/health.py`
  - `HealthDailyMetrics`
  - `HealthSleepSession`
  - `HealthActivity`
  - `HealthCalorieLog`
  - `GarminConnection`
- `apps/api/models/events.py`
  - `WearableEvent`
  - `NormalizedEvent`
- `apps/api/models/agents.py`
  - `AgentRun`
  - `Intervention`
  - `Case`
  - `AuditLog`
- `apps/api/models/recipes.py`
  - `Recipe`
  - `MealPlanSlot`

Important:

- Query the health tables directly for snapshots
- Do not depend on Garmin's emitted `NormalizedEvent` as the main health source
- `NormalizedEvent` can remain a trace artifact, but not the source of runtime truth

## Recommended New Modules

These names are intentionally concrete so the work can resume cleanly after context loss.

### API

- `apps/api/models/personalization.py`
  - `PersonalizationStateSnapshot`
  - `ActivityTemplate`
  - `WellnessTemplate`
  - `SupportPlanFeedbackEvent`
- `apps/api/personalization.py`
  - snapshot builder
  - state feature derivation
  - archetype scoring
- `apps/api/risk_scoring.py`
  - deterministic risk subscore calculation
- `apps/api/recipe_ranking.py`
  - recipe ranking logic
- `apps/api/catalog_ranking.py`
  - activity and wellness ranking logic
- `apps/api/support_plan.py`
  - response assembly for current support plan
- `apps/api/routers/personalization.py`
  - internal or authenticated endpoint for current snapshot/context
- `apps/api/routers/support_plan.py`
  - `GET /api/support-plan/current`
  - feedback event POST endpoints

### Agent tooling

- `services/tools/get_personalization_context_tool.py`
- update `services/agents/tooling.py` to expose it

### Agent pipeline

- update `services/agents/coordinator/agent.py`
- update `services/agents/risk_stratification/agent.py`
- update `services/agents/intervention_planning/agent.py`
- extend `services/agents/schemas.py`

## Proposed Schema Additions

### `personalization_state_snapshots`

Recommended columns:

- `id`
- `user_id`
- `run_id` nullable
- `source` string
  - `live_checkin`
  - `scenario`
  - `scheduled_refresh`
- `profile_static` JSONB
- `dynamic_state` JSONB
- `archetype_scores` JSONB
- `feature_windows` JSONB
  - 1-day
  - 7-day
  - 30-day
- `inputs_summary` JSONB
  - recent check-ins
  - calorie summaries
  - recent recipe usage
  - recent intervention outcomes
- `created_at`

Notes:

- Store computed features for traceability
- Do not store only a pointer to live source rows
- Snapshots need to be inspectable later when debugging plan quality

### Extend `interventions`

Keep the existing text fields. Add:

- `state_snapshot_id`
- `recipe_id`
- `activity_template_id`
- `wellness_template_id`
- `risk_subscores` JSONB
- `why_chosen` JSONB
- `alternatives_considered` JSONB
- `why_changed_from_previous` JSONB or `Text`

Reason:

- the dashboard and recipe page can migrate without breaking old traces
- compatibility fields can be removed later if desired

### `activity_templates`

Recommended columns:

- `id`
- `title`
- `description`
- `duration_minutes`
- `intensity`
- `accessibility_tags` JSONB
- `equipment_tags` JSONB
- `time_cost_level`
- `fatigue_sensitivity`
- `contraindication_tags` JSONB
- `metadata` JSONB
- `active`

### `wellness_templates`

Recommended columns:

- `id`
- `title`
- `description`
- `category`
- `duration_minutes`
- `accessibility_tags` JSONB
- `time_cost_level`
- `fatigue_sensitivity`
- `metadata` JSONB
- `active`

### `support_plan_feedback_events`

Recommended columns:

- `id`
- `user_id`
- `run_id` nullable
- `intervention_id`
- `event_type`
  - `viewed`
  - `accepted`
  - `skipped`
  - `completed`
  - `recipe_cooked`
  - `calorie_logged_after_recommendation`
  - `manual_override`
- `payload` JSONB
- `created_at`

## Risk Model

Replace prompt-over-findings with deterministic scoring plus explanation.

### New subscore groups

- `physiological_strain`
  - poor sleep
  - elevated stress
  - low body battery
  - HR / HRV strain where available
- `emotional_strain`
  - mood score
  - note sentiment
  - distress phrases
- `recovery_debt`
  - recent sleep deficit
  - accumulated low recovery days
  - activity and rest imbalance
- `adherence_risk`
  - missed calorie logging
  - skipped plans
  - repetitive failed recommendations
  - routine instability

### Output shape

Return:

- `risk_level`
- `urgency`
- `confidence`
- `subscores`
- `drivers`
- `rationale`

Mapping:

- low
- moderate
- high
- critical

Important:

- LLM explains `drivers` and `rationale`
- deterministic code decides `risk_level`

## Check-in Normalization Rules

Current `CheckInRequest` already sends:

- `mood: int`
- `sleep_hours: float`
- `stress: int`
- `note: str`

Implementation rules:

- keep `mood` numeric and normalize to a known scale
- keep `stress` numeric and normalized
- treat note sentiment separately from mood
- do not mark all check-ins as negative
- preserve raw text for traceability
- include check-in aggregates in the snapshot, not only the latest raw values

## Recipe Ranking Model

### Extend recipe schema

Add to `Recipe` and DTOs:

- `calories`
- `protein_grams`
- `carbs_grams`
- `fat_grams`
- `fiber_grams`
- `prep_effort`
- `equipment_tags`
- `cost_level`

Fallback:

- if structured nutrition is missing, estimate from parsed ingredients later
- do not block the refactor on perfect nutrition parsing

### Deterministic recipe scoring dimensions

- dietary compatibility
- allergy exclusion
- meal constraint fit
- calorie target fit
- protein target fit
- prep capacity fit
- time-of-day fit
- novelty / repetition penalty
- recent history penalty
- accessibility fit

Important:

- `protein_gap` is a target feature, but current calorie logs only store calories
- if protein intake is not logged yet, use recipe-side protein scoring first and defer fully accurate protein-gap estimation

## Activity and Wellness Ranking

Use deterministic ranking against:

- fatigue / recovery state
- prep capacity / time scarcity
- accessibility toggles
- routine stability
- novelty
- contraindications
- prior completion feedback

Planner output should include:

- chosen candidate ID
- short explanation
- alternatives considered

## Proposed Support Plan API

Add:

- `GET /api/support-plan/current`

Recommended response shape:

```json
{
  "generated_at": "2026-04-04T12:00:00Z",
  "run": {
    "id": 123,
    "status": "completed"
  },
  "state_snapshot": {
    "id": 45,
    "created_at": "2026-04-04T11:59:00Z",
    "dynamic_state": {
      "sleep_debt": 0.62,
      "stress_load": 0.71,
      "recovery_score": 0.34,
      "activity_capacity": 0.41,
      "prep_capacity": 0.29,
      "calorie_balance": -180,
      "protein_gap": 25,
      "adherence_score": 0.58,
      "routine_stability": 0.37
    },
    "archetype_scores": {
      "student_overload": 0.74,
      "caregiver_burden": 0.05,
      "low_energy_recovery": 0.69,
      "routine_rebuild": 0.52,
      "accessibility_support": 0.21,
      "performance_ready": 0.08
    }
  },
  "risk": {
    "level": "moderate",
    "urgency": "next_day",
    "confidence": 0.83,
    "subscores": {
      "physiological_strain": 0.71,
      "emotional_strain": 0.63,
      "recovery_debt": 0.78,
      "adherence_risk": 0.34
    },
    "drivers": [
      "Sleep has been below baseline for three days",
      "Stress is elevated and body battery is suppressed"
    ],
    "rationale": "Moderate risk driven mostly by recovery debt and physiological strain."
  },
  "plan": {
    "meal": {
      "recipe_id": 88,
      "title": "Turkey and Rice Bowl",
      "description": "High-protein, low-prep lunch",
      "why_chosen": [
        "Fits current prep capacity",
        "Improves protein coverage without high effort"
      ],
      "alternatives_considered": [17, 23, 41]
    },
    "activity": {
      "template_id": 5,
      "title": "Ten-Minute Reset Walk"
    },
    "wellness": {
      "template_id": 11,
      "title": "Two-Minute Grounding Reset"
    },
    "empathy_message": "Today looks heavier than usual, so the plan stays deliberately low-friction.",
    "rationale": "Low-prep, low-friction choices selected to support recovery and consistency.",
    "why_changed_from_yesterday": [
      "Recovery score fell",
      "Prep capacity is lower than yesterday",
      "Yesterday's meal recommendation was skipped"
    ]
  }
}
```

### Compatibility rules

During migration:

- keep `/api/interventions`
- keep `/api/runs/{id}` trace response
- keep populating legacy text fields in `Intervention`
- extend DTOs with optional structured fields if needed
- remove `mapInterventionToSupportPlan()` only after the dashboard cutover is complete

## Ticket Verification Rule

At the end of every ticket, add or update a reusable verification script under `scripts/`.

Purpose:

- avoid copy-pasting many commands after each ticket
- make it easy to rerun validation after context loss
- let the user send one script output back for confirmation

Required behavior:

- every ticket must leave behind a script that validates the work done in that ticket
- if the app is expected to remain runnable end-to-end after that ticket, the script must exercise the application end-to-end, not just unit tests
- if the ticket is an intermediate schema or plumbing step that cannot yet provide meaningful end-to-end behavior, the script must still:
  - run the best available targeted checks
  - print clearly what is being verified
  - print clearly what is intentionally not yet covered
- scripts must exit nonzero on failure
- scripts should prefer the existing API venv at `apps/api/.venv`
- scripts should be runnable from the repo root
- scripts should be designed so the user can run one command and paste the output back

Recommended naming:

- `scripts/verify_ticket_01_schema.sh`
- `scripts/verify_ticket_02_personalization_context.sh`
- `scripts/verify_ticket_03_risk_normalization.sh`
- and so on

Recommended execution style:

- local dev example:
  - `doppler run --config dev -- scripts/verify_ticket_XX_<slug>.sh`
- if Doppler env is already injected in the shell:
  - `scripts/verify_ticket_XX_<slug>.sh`

Recommended contents of each ticket script:

- environment preflight
- migration step if required
- targeted backend tests
- targeted frontend typecheck/test/build when relevant
- HTTP smoke flow for the feature path changed by the ticket when the app should still work end-to-end

Reuse guidance:

- if a ticket naturally overlaps old smoke coverage patterns, reuse the useful parts of prior smoke logic rather than rewriting from scratch
- the older one-off ADK/A2A smoke scripts were intentionally removed, but their ideas are still valid as templates for future ticket-specific verification scripts

## Ticket List

These are the execution tickets. Follow them in order unless explicitly parallelized below.

### Ticket 1: `007_personalization_state_snapshots_and_structured_interventions`

Goal:

- Add the snapshot table
- Extend interventions with structured plan metadata
- Preserve old text fields

Primary files:

- `apps/api/models/agents.py`
- `apps/api/models/personalization.py` if created
- `apps/api/models/__init__.py`
- `apps/api/routers/interventions.py`
- `apps/api/schemas/agents.py`
- `apps/api/alembic/versions/007_personalization_state_snapshots_and_structured_interventions.py`

Verification script:

- `scripts/verify_ticket_01_schema.sh`

Acceptance criteria:

- migrations apply cleanly
- old intervention endpoints still work
- structured fields are nullable and backward compatible
- add a reusable verification script for this ticket

### Ticket 2: `Personalization context builder`

Goal:

- Build and expose the shared personalization context
- Replace coordinator reliance on `get_recent_signals()`

Primary files:

- `apps/api/personalization.py`
- `apps/api/routers/personalization.py`
- `services/tools/get_personalization_context_tool.py`
- `services/agents/tooling.py`
- `services/agents/coordinator/agent.py`
- optionally `services/tools/get_health_snapshot_tool.py`

Verification script:

- `scripts/verify_ticket_02_personalization_context.sh`

Implementation notes:

- snapshot builder should read the DB-backed health tables directly
- coordinator state should include:
  - `state_snapshot_id`
  - `dynamic_state`
  - `archetype_scores`
  - `signals` compatibility view during transition

Acceptance criteria:

- a live run can build a snapshot and proceed
- coordinator no longer depends only on `/api/events/recent`
- add a reusable verification script for this ticket

### Ticket 3: `Check-in normalization and risk subscores`

Goal:

- stop treating all check-ins as negative
- move risk to deterministic subscores plus explanation

Primary files:

- `apps/api/routers/events.py`
- `apps/api/schemas/events.py`
- `services/agents/signal_interpretation/agent.py`
- `services/agents/risk_stratification/agent.py`
- `services/agents/schemas.py`
- `apps/api/risk_scoring.py`

Acceptance criteria:

- positive or neutral check-ins do not automatically create `negative_checkin`
- risk output includes subscores and drivers
- existing pipeline tests are updated
- add a reusable verification script for this ticket

### Ticket 4: `008_recipe_nutrition_fields`

Goal:

- add nutrition and effort fields to recipes

Primary files:

- `apps/api/models/recipes.py`
- `apps/api/schemas/recipes.py`
- `apps/api/routers/recipes.py`
- `apps/web/src/lib/api-contracts.ts`
- `apps/web/src/pages/RecipeListPage.tsx`
- `apps/api/alembic/versions/008_recipe_nutrition_fields.py`

Acceptance criteria:

- existing recipe CRUD still works
- templates and user recipes can hold the new fields
- add a reusable verification script for this ticket

### Ticket 5: `Meal ranking service`

Goal:

- replace tag overlap with deterministic ranking

Primary files:

- `apps/api/recipe_ranking.py`
- `apps/api/routers/recipes.py`
- `services/agents/intervention_planning/agent.py`

Implementation notes:

- keep `GET /api/recipes/recommended`
- change internals only at first
- ranking should use snapshot features, not only intervention tags

Acceptance criteria:

- recommendations are generated from structured ranking
- latest intervention `meal_constraints` is no longer the sole ranking input
- add a reusable verification script for this ticket

### Ticket 6: `009_activity_wellness_catalogs_and_planner_rewrite`

Goal:

- add activity and wellness catalogs
- move planner to retrieve-rank-compose

Primary files:

- `apps/api/models/personalization.py`
- `apps/api/catalog_ranking.py`
- `services/agents/intervention_planning/agent.py`
- `services/agents/coordinator/agent.py`
- `services/agents/schemas.py`
- `services/tools/create_intervention_tool.py`
- `apps/api/routers/interventions.py`
- `apps/api/alembic/versions/009_activity_wellness_catalogs.py`

Acceptance criteria:

- selected activity and wellness IDs are persisted
- planner output includes `why_chosen` and `alternatives_considered`
- add a reusable verification script for this ticket

### Ticket 7: `Support plan endpoint and trace compatibility`

Goal:

- create a single current support-plan endpoint
- preserve trace and intervention compatibility

Primary files:

- `apps/api/support_plan.py`
- `apps/api/routers/support_plan.py`
- `apps/api/schemas/agents.py`
- `apps/api/routers/runs.py`
- `apps/api/main.py`

Acceptance criteria:

- dashboard can fetch one structured object
- run traces still load
- old clients still function during transition
- add a reusable verification script for this ticket

### Ticket 8: `Frontend support-plan cutover`

Goal:

- switch the frontend to the new support-plan endpoint

Primary files:

- `apps/web/src/lib/api.ts`
- `apps/web/src/lib/api-contracts.ts`
- `apps/web/src/lib/api-mappers.ts`
- `apps/web/src/lib/types.ts`
- `apps/web/src/pages/MemberDashboard.tsx`
- `apps/web/src/pages/RecipeListPage.tsx`

Implementation notes:

- remove the current `/api/interventions + /api/runs` stitch-up in `getSupportPlanLive()`
- replace minimal `SupportPlan` with a structured type
- show risk drivers and recipe details

Acceptance criteria:

- dashboard uses `GET /api/support-plan/current`
- recipe page reads structured meal recommendation context
- `mapInterventionToSupportPlan()` is deleted or fully dead code
- add a reusable verification script for this ticket

### Ticket 9: `010_support_plan_feedback_events`

Goal:

- add feedback logging and wire it into ranking inputs later

Primary files:

- `apps/api/models/personalization.py`
- `apps/api/routers/support_plan.py`
- `apps/api/schemas/agents.py` or a new support-plan schema module
- `apps/web/src/lib/api.ts`
- `apps/web/src/pages/MemberDashboard.tsx`
- `apps/web/src/pages/RecipeListPage.tsx`
- `apps/api/alembic/versions/010_support_plan_feedback_events.py`

Acceptance criteria:

- feedback events are persisted
- recommendation interaction can be tied back to specific interventions
- add a reusable verification script for this ticket

## Recommended Execution Order

### Phase 1

- Ticket 1
- Ticket 2
- Ticket 3

Reason:

- these fix the state model and risk quality before recommendation work

### Phase 2

- Ticket 4
- Ticket 5

Reason:

- meal ranking can land independently once recipe metadata exists

Parallelism:

- Ticket 4 and the non-dependent parts of Ticket 5 can run in parallel

### Phase 3

- Ticket 6
- Ticket 7

Reason:

- planner rewrite and support-plan contract need the structured persistence layer

### Phase 4

- Ticket 8

Reason:

- frontend should cut over only after the real endpoint exists

### Phase 5

- Ticket 9

Reason:

- feedback is more useful once the new structured support plan is live

## Tests To Add Or Extend

### API tests

Extend:

- `apps/api/tests/test_pipeline.py`
- `apps/api/tests/test_recipes.py`
- `apps/api/tests/test_health.py`
- `apps/api/tests/test_agent_runner.py`

Add:

- `apps/api/tests/test_support_plan.py`
- `apps/api/tests/test_personalization.py`
- `apps/api/tests/test_risk_scoring.py`

Suggested cases:

- snapshot builder aggregates 1-day, 7-day, and 30-day windows correctly
- neutral check-in does not become `negative_checkin`
- risk subscores map to correct risk levels
- recipe ranking respects allergies and low-prep constraints
- current support-plan endpoint returns linked objects and change reasons
- intervention persistence still fills legacy text fields

Verification policy:

- after each ticket, prefer running the ticket-specific script first
- use direct test commands only as fallback or while developing the script

### Web tests

Current web test coverage is minimal:

- `apps/web/src/test/example.test.ts`

Add:

- `apps/web/src/test/support-plan.test.ts`

Suggested cases:

- dashboard renders structured support-plan payload
- risk drivers render correctly
- linked recipe details render correctly
- fallback state renders when no support plan exists

## Important Compatibility Constraints

- Keep `persona_type` in onboarding and profile schemas
- Keep specialist routing by `persona_type` in the coordinator
- Keep resource lookup keyed by `persona_type`
- Keep legacy intervention text fields during the migration
- Keep `/api/interventions` and `/api/runs/{id}` compatible until the frontend cutover is complete
- Do not block the refactor on perfect nutrition extraction
- Do not block the refactor on ML

## Known Open Questions

These do not block Phase 1, but they should be resolved during implementation.

- Should `PersonalizationStateSnapshot` live in `models/agents.py` or a new `models/personalization.py` file?
  - Recommendation: use a new `models/personalization.py` for clarity
- Should support-plan schemas live in `schemas/agents.py` or a new `schemas/support_plan.py` file?
  - Recommendation: create a dedicated `schemas/support_plan.py` if the DTO gets large
- How much nutrition estimation should be automated in Phase 2?
  - Recommendation: schema first, parser/estimator second

## Fast Resume Checklist

If work resumes after context loss:

1. Read this file.
2. Re-open these files first:
   - `services/agents/coordinator/agent.py`
   - `services/agents/risk_stratification/agent.py`
   - `services/agents/intervention_planning/agent.py`
   - `apps/api/routers/events.py`
   - `apps/api/routers/interventions.py`
   - `apps/api/routers/recipes.py`
   - `apps/api/models/agents.py`
   - `apps/api/models/health.py`
   - `apps/api/models/recipes.py`
   - `apps/web/src/lib/api.ts`
   - `apps/web/src/pages/MemberDashboard.tsx`
3. Inspect `scripts/` and identify the latest ticket verification script.
4. Start with Ticket 1 unless it is already complete.
5. Keep compatibility fields and routes until the frontend is fully migrated.
6. Use deterministic state and ranking logic first, LLM composition second.

## Definition Of Done

The refactor is complete when:

- coordinator runs are built from a shared personalization snapshot
- risk is deterministic and explainable
- meals, activities, and wellness actions are retrieve-rank-compose
- interventions persist structured selected objects and rationale
- dashboard uses `/api/support-plan/current`
- recipe recommendations are snapshot-aware and nutrition-aware
- feedback events are logged and available for future ranking improvements
