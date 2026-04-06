# NüMe Update Plan 2: Precision Coach Architecture

Last verified: 2026-04-05

This document supersedes the first draft of `docs/updateplan2.md`.

It is the follow-on execution plan after `docs/updateplan.md` Tickets 1-9.

This file is intended to be self-contained enough that a future LLM or engineer can pick it up without relying on prior chat context.

## Purpose

The goal of this phase is to turn NüMe from a structured support-plan app into a wearable-first precision coach that behaves like:

- a nutrition coach
- a personal trainer
- a recovery and wellness coach

The product should feel like all sections of the app are driven by one coherent model of the user rather than three loosely related recommendation cards.

## Product North Star

NüMe should eventually do all of the following in one unified loop:

- use wearable and health-table data as the primary source of truth when available
- use check-ins mainly for subjective context and for users without wearables
- estimate energy needs adaptively from real behavior and outcomes, not from a static formula only
- recommend meals from real linked recipes that the user can open and cook immediately
- recommend workouts from real structured workout plans that the user can open and follow
- connect nutrition, exercise, recovery, and wellness to the same underlying state
- explain clearly why the current day’s plan fits the user’s metrics, goals, and recent behavior
- improve over time from adherence, outcomes, and recovery changes

## Core Architectural Conclusion

Do not try to solve this with one giant model or “a true TDEE LLM.”

The correct architecture is:

- deterministic physiology and planning engines for:
  - adaptive TDEE
  - calorie and macro targets
  - nutrient gap estimation
  - recovery and readiness
  - workout progression and safety
  - ranking and selection
- a shared longitudinal user state model
- linked structured objects for meals and workouts
- LLMs or agents only for:
  - explanation
  - coaching language
  - orchestration
  - summarization
  - fallback copy adaptation

Precision comes primarily from:

- better data quality
- better longitudinal feedback loops
- better target formulas
- better ranking inputs

Not from raw model size.

## What “Extremely Precise” Actually Requires

If the app is supposed to know the user extremely well, it needs a complete picture across these categories.

### 1. Static and Slowly Changing Inputs

- age
- sex
- height
- current body weight
- body composition if available
  - body fat percent
  - lean mass
  - waist measurements if used later
- medical, injury, and medication constraints
- dietary style
- allergies and exclusions
- food dislikes and preferences
- cooking ability
- budget
- equipment access
- schedule and time constraints
- training background
- lifestyle context
  - student
  - caregiver
  - shift work
  - sedentary office work

### 2. Goal Inputs

- maintain weight
- lose weight
- gain weight
- gain muscle
- improve performance
- improve endurance
- improve recovery
- improve energy
- rebuild routine
- reduce stress
- target pace of change
  - slow
  - moderate
  - aggressive within safe bounds
- training frequency target
- meal preparation realism

### 3. Physiological and Behavioral Inputs

- daily or regular weight trend
- body composition trend if available
- calorie intake
- macro intake
- nutrient intake if the app wants “balanced diet” percentages
- steps
- workouts
- active calories
- total calories burned proxies
- sleep duration
- sleep architecture and sleep score
- HR, resting HR, HRV, stress, body battery, respiration, SpO2
- soreness, hunger, energy, mood, motivation
- adherence:
  - what was actually eaten
  - what workouts were completed
  - what was skipped
  - what was delayed

### 4. Response Over Time

- how body weight changes relative to intake and activity
- how recovery responds to workout load
- how hunger, energy, and adherence respond to calorie targets
- which meals keep the user full and consistent
- which workouts overload the user versus help them progress

## Important Product Truths

These are key architectural truths that should shape the implementation.

### One meal recommendation is not enough for full-day nutrition precision

If the app wants to tell a user:

- daily nutrient percentages
- whether their diet is balanced
- whether they are hitting micronutrient goals

then the app needs at least one of:

- complete food logging
- a full-day planned menu
- a full-week meal plan

A single recommended meal cannot support precise whole-day nutrition claims.

### Static TDEE formulas are not enough

If the app wants to be highly accurate on calorie targets, it needs:

- baseline estimation
- ongoing adaptive correction from:
  - intake
  - weight trend
  - wearable activity
  - adherence quality

### Check-ins should not dominate when wearables exist

Manual check-ins are still useful, but primarily for:

- subjective energy
- soreness
- hunger
- stress perception
- mood
- barriers
- symptoms not captured by devices

When Garmin and health-table data exist, those should be primary for physiological state.

## Current Repo Baseline After Tickets 1-9

This is the verified baseline this plan starts from.

### Already present

- health tables:
  - `HealthDailyMetrics`
  - `HealthSleepSession`
  - `HealthActivity`
  - `HealthCalorieLog`
- Garmin Connect sync through `apps/api/garmin_sync.py`
- shared personalization snapshots in `apps/api/personalization.py`
- derived state already includes:
  - `sleep_debt`
  - `stress_load`
  - `recovery_score`
  - `activity_capacity`
  - `prep_capacity`
  - `calorie_balance`
  - `adherence_score`
  - `routine_stability`
- structured support plan endpoint:
  - `GET /api/support-plan/current`
- structured intervention persistence
- recipe nutrition fields:
  - calories
  - protein
  - carbs
  - fat
  - fiber
  - prep effort
  - cost level
- deterministic recipe ranking that already uses some nutrition and recovery state
- activity and wellness catalogs
- support-plan feedback events
- dashboard and recipe page already consume structured support-plan data

### Current important limitations

- no adaptive TDEE or weight-trend engine
- no body-composition model
- no ingredient-level nutrient engine
- no daily nutrient percentage engine
- `protein_gap` is not fully implemented as a meaningful target-driven input yet
- planner still chooses meal candidates from template recipes instead of prioritizing approved user recipes
- dashboard does not yet synthesize all domains into one coach-quality explanation
- exercise recommendations are still much less sophisticated than meal recommendations

## Scientific Standard

This phase should be built to a higher bar than “good heuristics.”

Definition of scientifically backed for this product:

- every major deterministic rule family must map to a named evidence source
- recommendation logic must be versioned and auditable
- the app must distinguish:
  - evidence-backed rules
  - implementation heuristics
  - LLM-generated wording
- no meal or workout recommendation should be produced without:
  - the metrics used
  - the derived targets used
  - the selected linked object
  - the explanation shown to the user
- weak data should reduce confidence and narrow recommendations

## Scientific Anchors

Use these as primary starting sources:

- U.S. Dietary Guidelines for Americans, 2025-2030
  - https://odphp.health.gov/our-work/nutrition-physical-activity/dietary-guidelines/current-dietary-guidelines
- U.S. Physical Activity Guidelines for Americans, 2nd edition
  - https://odphp.health.gov/our-work/nutrition-physical-activity/physical-activity-guidelines/current-guidelines
- American Heart Association statement on sleep duration/quality and cardiometabolic health
  - https://professional.heart.org/en/guidelines-statements/sleep-duration-and-quality-impact-on-lifestyle-behaviors-and-cardiometabolice367

Supporting evidence families to formalize during implementation:

- DRI-based energy and nutrient target methods
- sports nutrition evidence only where clearly appropriate
- ACSM-style progression logic for exercise prescription
- conservative readiness and overload logic

## Safety Boundaries

This product must not drift into unsupported medical advice.

Explicit boundaries:

- no diagnosis
- no medication-sensitive therapeutic nutrition rules
- no condition-specific treatment diets unless later clinician workflows are added
- no aggressive exercise progression for users with unresolved injury or red flags
- no false precision when intake or weight data quality is poor

Required behavior under low-confidence conditions:

- lower-confidence recommendations
- more conservative calorie and workout guidance
- simpler meals and simpler exercise
- clearer explanation that the system needs more data for tighter precision

## Garmin Reality and Constraints

This section is critical for future implementation.

### Current state

The app currently uses:

- Garmin Connect login through the unofficial `garminconnect` Python library
- token files persisted locally via the library auth flow
- not the official Garmin Developer Program APIs

Current sync already pulls:

- steps
- step goal
- active calories
- total calories
- resting HR
- average HR
- body battery high/low
- stress
- intensity minutes
- floors climbed
- SpO2
- HRV weekly average
- HRV status
- VO2 max
- active minutes
- sleep sessions with stages, score, respiration, and SpO2
- completed activities with:
  - type
  - duration
  - distance
  - calories
  - HR
  - elevation
  - speed
  - training load

### What can likely be expanded with the current unofficial auth stack

Because the app already has working Garmin Connect auth, it may be possible to pull more Garmin-derived data through the same unofficial path if the library exposes stable methods and the user account surfaces those objects.

Candidate expansion areas:

- richer activity detail
- more recovery/readiness-like fields
- body composition or scale-linked data
- wellness and hydration data
- workouts or scheduled workouts
- exercise details for completed strength sessions
- additional historical summaries

Do not assume these are all available until observed working with the current library and account.

### What is blocked without official Garmin program access

Do not architect core product behavior around these until official access exists:

- stable official Garmin Health API integration
- stable official Garmin Activity API ingestion
- stable official Training API push of workouts to watch devices
- webhook and enterprise data guarantees

### Design rule

Near-term implementation should:

- exploit the current unofficial Garmin Connect path where practical
- treat it as brittle and subject to change
- keep Garmin-derived objects normalized into local DB tables
- avoid coupling business-critical logic directly to ad hoc library responses

Long-term implementation can later add official Garmin program integrations as a separate track.

## Required Data Model For A True Coach

The app needs a more complete set of core runtime objects.

### `CoachProfile`

Canonical user baseline:

- demographics
- anthropometrics
- injuries/constraints
- equipment
- dietary style
- allergies
- cooking realism
- accessibility needs
- schedule and budget constraints
- training background

### `CoachGoals`

Canonical goal object:

- primary goal
- secondary goals
- target pace of change
- target timeline
- training frequency target
- meal effort tolerance

### `BodyTrendState`

Longitudinal body state:

- weight trend
- estimated rate of change
- body composition trend if available
- confidence in current body trend

### `EnergyModel`

Adaptive energy engine:

- baseline estimated maintenance
- adaptive TDEE estimate
- observed intake trend
- observed burn trend
- target calorie band
- confidence score
- reason codes for target changes

### `NutritionTargets`

Structured nutrition targets:

- calorie target band
- protein target range
- carb target range or strategy if appropriate
- fat floor or range
- fiber target
- hydration target if later supported
- optional micronutrient target framework

### `RecoveryReadiness`

Current readiness state:

- sleep quality
- sleep debt
- physiological strain
- emotional strain
- recovery score
- readiness band
- confidence and data source mix

### `ExerciseContext`

Training context:

- recent workouts
- recent load
- soreness or subjective strain if reported
- readiness modifiers
- progression stage
- recommended intensity ceiling

### `CoachRecommendationContext`

Single object used by all recommendation surfaces:

- profile
- goals
- body trend
- energy model
- nutrition targets
- recovery readiness
- exercise context
- adherence history
- source-of-truth metadata

## Recommendation Source Of Truth Rules

### Meal recommendations

Priority order:

1. approved user recipes
2. approved acquired recipes from trusted sources
3. system templates as fallback

Rules:

- a recommended meal should be backed by a real `recipe_id`
- dashboard must link directly to the recipe detail page
- no dashboard meal should be dead-end text if a real recipe exists

### Exercise recommendations

Priority order:

1. structured workout plans matched to readiness and goals
2. conservative fallback activities when data is sparse

Rules:

- a recommended workout should be a real linked object
- it should include:
  - duration
  - intensity
  - modality
  - progression level
  - constraints
  - reasons selected

### Wellness recommendations

Rules:

- remain aligned with the same readiness and recovery state
- avoid competing with meal and workout recommendations

## Dashboard Contract

The dashboard should eventually answer all of these in one coherent place:

- what does the data say about me today?
- how confident is the app in that?
- why is this calorie or nutrition guidance right for me today?
- why is this exact recipe the best fit?
- why is this exact workout or activity the best fit?
- what changed since yesterday or last week?
- what should I do next?

It should read like one coach with multiple specialties, not multiple disconnected widgets.

## Execution Status

Current execution state as of 2026-04-05:

- Tickets 1-9 from `docs/updateplan.md` are complete
- This precision-coach phase is not started

Last verified command:

- `scripts/verify_ticket_09_support_plan_feedback_events.sh`

## Execution Tickets

These tickets continue numbering from the first plan.

### Ticket 10: `011_evidence_registry_and_guardrails`

Goal:

- create a versioned evidence registry for nutrition, exercise, sleep, recovery, and energy rules
- define confidence scoring, contraindications, fallback behavior, and audit metadata

Primary files:

- `apps/api/evidence/registry.py` or similar new module
- `apps/api/personalization.py`
- `apps/api/risk_scoring.py`
- `apps/api/schemas/agents.py` or new evidence schema module
- `apps/api/tests/`

Implementation notes:

- every major rule family should have:
  - `source_id`
  - `source_name`
  - `version`
  - `scope`
  - `confidence_class`
- recommendation outputs should carry rule version and confidence metadata

Acceptance criteria:

- every deterministic rule family has a named evidence source id
- low-data and safety fallbacks are explicit
- recommendation responses can expose evidence and confidence metadata
- add a reusable verification script for this ticket

### Ticket 11: `012_coach_profile_and_goal_canonical_model`

Goal:

- normalize user profile, constraints, and goals into canonical coach objects
- stop scattering goal semantics across ad hoc fields

Primary files:

- `apps/api/models/user.py`
- `apps/api/personalization.py`
- `apps/api/schemas/`
- `apps/web/src/`
- new migration under `apps/api/alembic/versions/` if needed

Implementation notes:

- preserve existing onboarding compatibility
- canonicalize:
  - primary goal
  - secondary goals
  - pace preference
  - training frequency realism
  - cooking realism
  - equipment access

Acceptance criteria:

- a single normalized coach-goals object exists
- state and ranking code read from the normalized goal object
- legacy fields remain backward compatible during migration
- add a reusable verification script for this ticket

### Ticket 12: `013_adaptive_body_metrics_and_energy_model`

Goal:

- build the missing adaptive TDEE and body-trend engine
- replace static calorie logic with longitudinal estimation

Primary files:

- `apps/api/models/health.py`
- `apps/api/personalization.py`
- `apps/api/energy_model.py` or similar new module
- `apps/api/tests/test_personalization.py`
- `apps/api/tests/test_health.py`
- new migration under `apps/api/alembic/versions/`

Implementation notes:

- add first-class support for:
  - regular weigh-ins
  - weight trend
  - optional body fat/body composition entries later
- derive:
  - baseline maintenance estimate
  - adaptive TDEE estimate
  - target calorie band
  - confidence score
- update targets from:
  - intake trend
  - burn/activity trend
  - weight trend

Acceptance criteria:

- the app can estimate adaptive TDEE from longitudinal data
- calorie targets are not purely static or formula-only
- state output includes confidence and reasons for target changes
- add a reusable verification script for this ticket

### Ticket 13: `014_food_composition_and_nutrient_engine`

Goal:

- support whole-day nutrient precision rather than only calories and macros
- build the foundation for daily nutrient percentages and balanced-diet logic

Primary files:

- `apps/api/models/recipes.py`
- `apps/api/routers/recipes.py`
- `apps/api/nutrition_composition.py` or similar new module
- `apps/api/tests/test_recipes.py`
- new migration under `apps/api/alembic/versions/`

Implementation notes:

- current recipe records only support calories, macros, fiber, and effort
- to support daily nutrient percentages, the app eventually needs:
  - ingredient normalization
  - ingredient-level nutrient data
  - recipe nutrient rollups
  - intake comparison against daily targets
- near-term scope can start with:
  - more robust macro and fiber rollups
  - optional micronutrient framework scaffolding

Acceptance criteria:

- nutrient rollup logic exists at least beyond the current minimal fields
- architecture supports future daily nutrient percentage calculations
- documentation clearly distinguishes current versus future nutrient precision
- add a reusable verification script for this ticket

### Ticket 14: `015_wearable_first_signal_precedence_and_data_confidence`

Goal:

- make wearables the primary physiological input when available
- reduce check-ins to subjective context and fallback coverage

Primary files:

- `apps/api/personalization.py`
- `apps/api/routers/events.py`
- `services/agents/coordinator/agent.py`
- `services/tools/get_personalization_context_tool.py`
- `apps/api/tests/test_personalization.py`

Implementation notes:

- wearable-derived inputs should dominate:
  - sleep
  - burn/activity
  - readiness proxies
  - physiological strain
- check-ins should still inform:
  - mood
  - note sentiment
  - soreness
  - hunger
  - perceived stress
  - barriers
- state should carry source-of-truth metadata and confidence

Acceptance criteria:

- physiological state prefers Garmin and health-table signals when available
- check-ins remain available as subjective context or fallback
- support-plan output can explain what data sources drove the plan
- add a reusable verification script for this ticket

### Ticket 15: `016_deep_garmin_connect_ingestion_current_auth_track`

Goal:

- expand Garmin-derived data collection using the existing unofficial Garmin Connect auth path
- normalize any additional stable fields into local tables without depending on official Garmin business APIs

Primary files:

- `apps/api/garmin_sync.py`
- `apps/api/models/health.py`
- `apps/api/routers/health.py`
- `apps/api/tests/test_health.py`
- new migration under `apps/api/alembic/versions/`

Implementation notes:

- current auth is based on the unofficial `garminconnect` library and persisted token files
- only sync fields/endpoints that are observed working in tests or manual verification
- candidate investigation areas:
  - richer activity details
  - workout/exercise details for completed sessions
  - more readiness/recovery fields
  - body composition or scale-linked data
  - hydration or wellness fields if stable
- keep the implementation resilient to endpoint instability

Acceptance criteria:

- additional Garmin-derived signals are normalized into local DB tables or structured JSON fields
- unstable endpoints do not break the core sync pipeline
- product-critical logic still operates on local normalized data, not raw library responses
- add a reusable verification script for this ticket

### Ticket 16: `017_nutrition_target_engine`

Goal:

- derive explicit calorie and nutrient targets from goals, body trend, intake, burn, and recovery
- move from generic “high protein” logic to explicit target bands and deficits

Primary files:

- `apps/api/personalization.py`
- `apps/api/nutrition_targets.py` or similar new module
- `apps/api/recipe_ranking.py`
- `apps/api/tests/test_personalization.py`
- `apps/api/tests/test_recipes.py`

Implementation notes:

- targets should include at least:
  - calorie target band
  - protein target range
  - carb strategy or range if appropriate
  - fat floor or range
  - fiber target
  - meal-size preference driven by recovery and activity context
- start adults-only unless more specific population support is explicitly added
- conservative fallback behavior is required when body data or intake data is sparse

Acceptance criteria:

- recipe ranking uses explicit targets rather than only tag-derived priorities
- calorie burn and intake materially influence meal selection
- recovery state materially influences meal profile and prep demand
- add a reusable verification script for this ticket

### Ticket 17: `018_recipe_source_policy_and_review_queue`

Goal:

- treat approved user recipes as the primary recommendation pool
- keep system templates as fallback
- support trusted-site acquisition plus review before eligibility

Primary files:

- `apps/api/models/recipes.py`
- `apps/api/routers/recipes.py`
- `apps/api/recipe_ranking.py`
- `apps/web/src/pages/RecipeListPage.tsx`
- `apps/web/src/pages/RecipeDetailPage.tsx`
- new migration under `apps/api/alembic/versions/`

Implementation notes:

- add source and approval metadata such as:
  - `source_type`
  - `approval_status`
  - `acquired_from_domain`
  - `reviewed_at`
- imported or agent-acquired recipes should not become recommendation candidates until approved
- allow trusted-site acquisition to stage recipes for review/editing

Acceptance criteria:

- approved user recipes rank ahead of templates when fit is comparable
- unapproved recipes are visible for review but are not recommendation-eligible
- trusted-site acquisition flows into a review queue instead of silently changing the plan pool
- add a reusable verification script for this ticket

### Ticket 18: `019_recipe_linked_support_plan_meals_and_daily_actionability`

Goal:

- ensure every recommended meal is actionable
- make the dashboard meal open directly to a cookable recipe page

Primary files:

- `apps/api/support_plan.py`
- `apps/api/routers/support_plan.py`
- `apps/web/src/pages/MemberDashboard.tsx`
- `apps/web/src/pages/RecipeDetailPage.tsx`
- `apps/web/src/lib/types.ts`
- `apps/web/src/lib/api-mappers.ts`

Implementation notes:

- the support-plan meal object should always include a routeable `recipe_id` when recipe-backed
- the recipe detail page should clearly show when it is the active recommendation
- dashboard dead-end text-only meal cards should be removed where real recipes exist

Acceptance criteria:

- users can open the recommended recipe directly from the dashboard
- recipe detail includes the full cook flow:
  - ingredients
  - instructions
  - metadata
- the support plan clearly links the selected meal to the recipe object
- add a reusable verification script for this ticket

### Ticket 19: `020_evidence_based_meal_ranking_v2`

Goal:

- rank meals using energy fit, nutrient fit, recovery fit, prep fit, and variety together
- make meal selection explainable in user language

Primary files:

- `apps/api/recipe_ranking.py`
- `apps/api/personalization.py`
- `services/agents/intervention_planning/agent.py`
- `apps/api/tests/test_recipes.py`
- `apps/api/tests/test_support_plan.py`

Implementation notes:

- scoring should consider:
  - calorie fit to target band
  - protein adequacy
  - macro strategy fit
  - fiber and satiety support
  - low-prep need under low recovery
  - recent repetition
  - dietary style and allergy enforcement
  - adherence and habit fit where known
- the system should be able to say why the winning recipe beat alternatives

Acceptance criteria:

- nutrition facts matter more than superficial tag overlap
- ranking output exposes reason components for the selected meal
- planner persists the selected recipe id and rationale so the dashboard can explain it
- add a reusable verification script for this ticket

### Ticket 20: `021_exercise_readiness_and_completed_workout_parsing`

Goal:

- derive exercise readiness from recent activity, recovery, and Garmin-derived history
- parse completed workouts more deeply where the current Garmin Connect path allows it

Primary files:

- `apps/api/models/health.py`
- `apps/api/personalization.py`
- `apps/api/activity_readiness.py` or similar new module
- `apps/api/garmin_sync.py`
- `apps/api/tests/test_health.py`

Implementation notes:

- exercise readiness should use at least:
  - recent workouts
  - recent load
  - sleep score and sleep duration
  - body battery or equivalent
  - stress
  - resting/average HR trends where available
- if completed workout details can be parsed through the current Garmin path, store them locally
- if not, fall back cleanly to summary-level logic

Acceptance criteria:

- exercise readiness is a structured derived object
- readiness changes when recent strain or recovery changes
- workout history has richer structure when the Garmin Connect path exposes it
- add a reusable verification script for this ticket

### Ticket 21: `022_structured_exercise_plan_catalog_and_progression`

Goal:

- make exercise recommendations behave like meal recommendations
- recommend real structured workout plans with progression metadata and deep links

Primary files:

- `apps/api/models/personalization.py` or new workout-plan models
- `apps/api/catalog_ranking.py`
- `services/agents/intervention_planning/agent.py`
- `apps/web/src/pages/MemberDashboard.tsx`
- `apps/web/src/pages/HealthDashboard.tsx`
- new migration under `apps/api/alembic/versions/`

Implementation notes:

- workout plans should encode:
  - modality
  - duration
  - intensity
  - progression level
  - goal tags
  - contraindications
  - required equipment
- selected exercise plans should be persisted linked objects, not only text strings

Acceptance criteria:

- the selected exercise recommendation is a real linked object
- the user can open it directly from the dashboard
- progression metadata exists for future adaptive training loops
- add a reusable verification script for this ticket

### Ticket 22: `023_dashboard_coach_synthesis`

Goal:

- make the dashboard read like one coherent coach
- tie body state, energy targets, meals, exercise, and wellness into one explanation

Primary files:

- `apps/api/support_plan.py`
- `apps/api/schemas/agents.py` or a new dashboard schema module
- `apps/web/src/pages/MemberDashboard.tsx`
- `apps/web/src/lib/types.ts`
- `apps/web/src/test/support-plan.test.tsx`

Implementation notes:

- dashboard should clearly communicate:
  - what metrics drove today’s plan
  - how confident the app is
  - what changed from the prior plan
  - how the meal and workout align together
- the top-level message should explain the whole plan, not just the individual cards

Acceptance criteria:

- dashboard clearly states which metrics drove today’s plan
- meal, exercise, and wellness sections reference the same underlying coach state
- confidence and source-of-truth status are visible when useful
- add a reusable verification script for this ticket

### Ticket 23: `024_weekly_adaptive_coach_loop`

Goal:

- move from one-off daily suggestions toward a true adaptive coaching loop
- use adherence, weight trend, completed meals, completed workouts, and recovery drift over time

Primary files:

- `apps/api/personalization.py`
- `apps/api/support_plan.py`
- `apps/api/routers/support_plan.py`
- `apps/api/models/personalization.py`
- `apps/web/src/pages/MemberDashboard.tsx`

Implementation notes:

- weekly adaptation should account for:
  - weight trend versus target
  - adherence trend
  - repeated skipped meals
  - repeated skipped workouts
  - recovery instability
- the app should be able to explain why targets or plans changed

Acceptance criteria:

- feedback and completion data influence future ranking and plan composition
- the system can explain how today’s plan changed from recent outcomes
- weekly summaries are possible without a new architecture rewrite
- add a reusable verification script for this ticket

### Ticket 24: `025_scientific_validation_and_human_review`

Goal:

- validate the coach against named scenarios before making strong scientific claims
- create a repeatable human review workflow

Primary files:

- `apps/api/tests/`
- `apps/web/src/test/`
- `scripts/`
- `docs/`

Implementation notes:

- add deterministic evaluation scenarios for:
  - poor sleep plus high burn
  - low recovery plus high stress
  - calorie surplus plus low activity
  - negative weight-trend mismatch
  - repeated workout strain with low readiness
  - users without wearable data
- require review of:
  - energy model changes
  - macro target logic
  - progression rules

Acceptance criteria:

- evidence scenarios have deterministic expected outputs
- rule changes can be reviewed by version
- scientific product claims are bounded to what the engine actually implements
- add a reusable verification script for this ticket

## Recommended Order

### Phase A: Foundations

- Ticket 10
- Ticket 11
- Ticket 12
- Ticket 13
- Ticket 14

Reason:

- these establish evidence mapping, canonical goals, adaptive energy logic, nutrient architecture, and source-of-truth policy

### Phase B: Data Depth

- Ticket 15

Reason:

- deepen Garmin-derived state only after the confidence and source-of-truth architecture are clear

### Phase C: Meal Coach

- Ticket 16
- Ticket 17
- Ticket 18
- Ticket 19

Reason:

- these turn meal recommendations into target-driven, recipe-backed, actionable nutrition coaching

### Phase D: Exercise Coach

- Ticket 20
- Ticket 21

Reason:

- these elevate activity suggestions into true workout recommendations tied to readiness and progression

### Phase E: Unified Product

- Ticket 22
- Ticket 23
- Ticket 24

Reason:

- synthesis, adaptation, and validation should land after the underlying models and linked objects are in place

## Near-Term Scope Recommendation

If the team wants the highest-value near-term slice, build these first:

1. Ticket 12: adaptive body metrics and energy model
2. Ticket 14: wearable-first precedence and data confidence
3. Ticket 16: nutrition target engine
4. Ticket 17: recipe source policy and review queue
5. Ticket 18: recipe-linked support-plan meals and dashboard actionability

This set gets the app materially closer to:

- precise meal selection
- wearable-first reasoning
- actionable recipe recommendations

without waiting for the entire trainer stack.

## Explicit Non-Goals For This Phase

These should not block execution unless explicitly requested:

- clinician-facing medical nutrition therapy
- disease-specific exercise protocols
- full micronutrient perfection from day one
- perfect official Garmin integration before improving the coach
- relying on one giant model to replace deterministic physiology logic

## Definition Of Done

This precision-coach phase is complete when:

- wearable data is the primary physiological driver whenever available
- check-ins mainly supply subjective context or fallback coverage
- the app has an adaptive energy model based on longitudinal intake, weight, and activity
- meal recommendations are selected from approved recipe objects and open directly to the recipe detail view
- nutrition targets are explicit, auditable, and grounded in named sources
- exercise recommendations are based on real activity and recovery context and link to structured workout plans
- the dashboard tells one integrated story across energy, nutrition, recovery, exercise, and wellness
- the system can credibly function as a personal trainer, nutrition coach, and wellness guide within the supported scope

## Future Roadmap

These items matter, but they should follow the execution tickets above rather than block them.

### Roadmap 1: Official Garmin Program Integration

- migrate from unofficial Garmin Connect dependence where possible
- add official Health API ingestion if program access is approved
- add official Activity API / FIT workflows if approved
- add official Training API push of workouts to devices if approved

### Roadmap 2: Deeper Nutrition Coaching

- full-day meal planning
- weekly meal planning
- grocery-list generation
- pantry substitutions
- stronger micronutrient modeling
- nutrient timing around workouts where justified

### Roadmap 3: Deeper Exercise Coaching

- progressive weekly workout blocks
- deload logic
- modality-specific tracks
  - walking
  - strength
  - cycling
  - mobility
  - hybrid
- goal tracks:
  - fat loss
  - strength
  - energy
  - general health
  - routine rebuild

### Roadmap 4: Real-Time Readiness

- real-time wearable signal integration where available
- more responsive same-day plan adjustments
- event-driven workout and nutrition coaching

### Roadmap 5: Higher-Rigor Trust Layer

- clinician review workflows
- evidence changelog surfaced internally
- audit views showing how recommendations were generated
- clearer confidence labeling for users

## Fast Resume Checklist

If work resumes after context loss:

1. Read `docs/updateplan.md`.
2. Read this file fully.
3. Re-open these first:
   - `apps/api/personalization.py`
   - `apps/api/recipe_ranking.py`
   - `apps/api/support_plan.py`
   - `apps/api/garmin_sync.py`
   - `apps/api/routers/recipes.py`
   - `apps/api/routers/health.py`
   - `apps/api/models/health.py`
   - `services/agents/intervention_planning/agent.py`
   - `apps/web/src/pages/MemberDashboard.tsx`
   - `apps/web/src/pages/RecipeDetailPage.tsx`
4. Start with Ticket 10 unless explicitly redirected.
