# NüMe Comprehensive Review

Status date: April 1, 2026

This document is based on direct code inspection of the current repository and a successful backend/agent test run. It is meant to be a self-contained project dossier that another LLM can use without re-reading the source tree. If older repo documents conflict with this file, treat this file as the more current implementation summary.

## Executive Summary

NüMe is a personalized wellness and care-coordination platform that combines a member-facing health product with a traceable multi-agent decision system. The product takes in user profile data, manual check-ins, wearable-style health signals, persona context, and accessibility preferences, then turns those inputs into a support plan that includes meal guidance, activity guidance, a wellness action, an empathy-first message, and staff-facing follow-up artifacts when risk is elevated.

It is not just a symptom tracker, a static dashboard, or a generic chatbot. The core concept is a care-operations workflow with a platform layer that owns state and policy, and an agent layer that interprets signals, stratifies risk, plans interventions, validates the result, and persists a trace of what happened.

The repo shows a full-stack implementation rather than only a model demo. It includes a React frontend, a FastAPI backend, PostgreSQL data persistence, Clerk authentication, demo-user impersonation, health-data ingestion, recipe ingestion and recommendation, multi-agent orchestration, remote specialist services, deployment configuration, seeding, and automated tests.

The most important long-term product idea is that NüMe is not supposed to remain a hard-coded persona system. The current persona categories are an MVP simplification for demo clarity and seeded scenarios. The actual vision is that NüMe learns a user's support profile from accumulated analytics, behavior, outcomes, and preferences over time, so the system effectively builds the persona from scratch instead of assigning the user to one of a few fixed buckets forever.

## Product Definition

NüMe is currently framed around four primary member personas:

- `student`: academic stress, disrupted routines, burnout risk, campus-resource alignment
- `caregiver`: chronic strain, sleep loss, burnout, respite-resource alignment
- `older_adult`: routine disruption, lower-friction support, readable and simplified guidance
- `accessibility_focused`: low-energy and accessibility-aware adaptation of support plans

These four personas should be understood as the current implementation scaffold, not the final conceptual model. They exist because the MVP needs explainable routing, seed data, and demo-friendly scenarios. The intended long-term direction is a dynamic persona layer created from ongoing analytics rather than a permanently assigned persona chosen during onboarding.

The system also supports three user roles:

- `member`: receives plans, views health and recipe tools, submits check-ins
- `coordinator`: reviews cases and active member journeys
- `admin`: can run demo scenarios and inspect trace data across runs

The project appears to have originated as a hackathon concept aimed at both empathy-centered social impact and technically sophisticated multi-agent architecture. That framing is still visible in the design: user benefit and judge-visible agent traceability are both first-class goals.

## Core Vision And Differentiator

The core long-term differentiator is longitudinal personalization.

The vision is that NüMe should infer who the user is from patterns, not just from a one-time intake form. In that model, persona is not a static label like student or caregiver. Instead, persona becomes an evolving support profile generated from:

- health and wearable trends over time
- repeated check-in behavior
- recovery and strain patterns
- adherence to prior recommendations
- which recommendations help or do not help
- accessibility and energy preferences as actually demonstrated in use
- shifting life context and routine stability

In other words, the more a person uses NüMe, the more specific and individualized the system becomes. The product gets better because it learns what strain looks like for that specific person, what kind of intervention language they respond to, what level of effort is realistic for them, and what combinations of nutrition, activity, recovery, and support are actually effective.

That is what makes the product unique conceptually. The present four-persona structure is best understood as the first interpretable version of a system whose eventual goal is adaptive persona formation and continuously improving recommendation quality through accumulated user history.

## What The Current Product Does

### Member Experience

- Onboarding collects profile basics, goal, activity level, dietary style, allergies, persona type, and accessibility preferences.
- The member dashboard shows the latest support plan, an empathy message, current risk level, recent signals, and the most recent intervention cards.
- A manual check-in flow collects mood, sleep hours, stress level, and an optional note.
- A health dashboard exposes wearable-style metrics, Garmin account connection, sync status, trends, sleep history, activity history, and a calorie log.
- A recipe workflow allows importing recipes from a URL, parsing pasted recipe text with AI, editing parsed output before saving, browsing saved recipes, and seeing recommended recipes based on intervention meal constraints.

### Staff And Demo Experience

- A coordinator dashboard shows case counts by status and a list of member cases with persona fit, risk level, and summary.
- An admin scenario runner triggers seeded demo scenarios and polls until the resulting trace completes.
- A traces list page shows recent agent runs.
- A trace detail page groups messages into coordinator output, parallel execution output, remote specialist output, validation-loop iterations, and final persisted actions.

### Demo Mode

- Privileged internal users can switch into seeded demo accounts from the UI.
- The frontend sets an `X-Demo-As` header.
- The backend honors that header only for allowlisted real users and swaps the effective user context to the chosen seeded demo account.

## Current User-Facing Surfaces

| Surface | Purpose | Important behavior |
|---|---|---|
| Login / Register | Authentication shell | Uses Clerk on the frontend and backend token verification |
| Onboarding | Creates member profile and accessibility preferences | Persona and accessibility choices directly influence later recommendations |
| Member Dashboard | Main support-plan view | Polls active runs and shows the latest intervention plus risk badge and empathy message |
| Check-In | Manual signal entry | Submits one atomic request that creates events, a normalized event, and an agent run |
| Health Dashboard | Wearable and nutrition view | Includes Garmin connect/sync, overview, trends, sleep, activities, and calorie logging |
| Recipes | Recipe ingestion and recommendation | Supports URL parsing, AI text parsing, manual review/edit, save, and recommendations |
| Coordinator Dashboard | Staff case management | Lists open and historical cases with persona and risk context |
| Scenario Runner | Demo control panel | Launches seeded situations and auto-opens the final trace |
| Trace Views | Explainability and observability | Shows agent-by-agent message output, loop iterations, A2A work, and final actions |

## End-To-End Run Lifecycle

The most important system flow is the support-plan generation pipeline:

1. A member submits a check-in or an admin launches a seeded scenario.
2. The backend writes raw events into `wearable_events`.
3. Those signals are bundled into a `normalized_events` row with a short summary.
4. An `agent_runs` row is created in `pending` state.
5. A background coordinator execution is launched.
6. The coordinator loads the user profile, accessibility preferences, recent signals, and persona-specific resources through the tool layer.
7. Three agents run in parallel: signal interpretation, risk stratification, and intervention planning.
8. The coordinator routes to a persona-specific specialist.
9. An empathy/check-in agent generates the user-facing tone.
10. A validation loop checks contradictions, accessibility mismatches, and other safety issues for up to three iterations.
11. The final plan is persisted as an intervention.
12. If risk is moderate or above, a case is created.
13. A notification record is queued and an audit log is written.
14. Every agent step is stored as an agent message so the frontend can render a full trace.

## Multi-Agent Architecture

NüMe uses an ADK-shaped architecture even though the current runtime is partly custom.

### Parallel Core Agents

- `SignalInterpretationAgent`: turns raw signals into structured findings with type, severity, confidence, and evidence
- `RiskStratificationAgent`: assigns risk level, urgency, escalation need, coordinator-review flag, confidence, and rationale
- `InterventionPlanningAgent`: generates a structured plan containing meal, activity, and wellness actions plus meal constraints and resources

### Persona Specialists

- `StudentSupportSpecialist`: remote specialist for student situations, focused on academic stress and campus support
- `CaregiverBurnoutSpecialist`: remote specialist for caregiver burden, respite, and escalation
- `AccessibilityAdaptation`: local fallback and default specialist path for non-student, non-caregiver personas

### Human-Centered And Safety Agents

- `EmpathyCheckinAgent`: converts system output into warm, supportive language instead of judgmental instruction
- `ValidationLoopAgent`: reviews the generated plan for contradictions, accessibility mismatch, policy problems, and unsupported actions; it can revise the plan and retry up to three times

### Traceability Model

- Every stage is logged into `agent_messages`
- Message types distinguish `parallel`, `local`, `a2a`, and `loop`
- The frontend renders those message groups separately so judges or reviewers can see what the system did

## How The Agent Runtime Actually Works

The repo still reflects its Google ADK hackathon origin, but the practical runtime is hybrid:

- There is an `adk_compat.py` layer that imports real Google ADK classes when available and otherwise falls back to lightweight dataclass stubs.
- The coordinator uses a custom `ThreadPoolExecutor` helper for parallel execution.
- Remote specialists are contacted over HTTP through `/invoke` endpoints rather than a full production A2A runtime.
- JSON generation currently goes through an OpenAI/Azure OpenAI-compatible client wrapper, not a hardcoded Gemini-only path.
- Default model selection in code falls back to `gpt-4.1-mini` unless environment variables point elsewhere.

This means the system is architected in an ADK-aligned way, but the implemented runtime prioritizes reliability and portability over strict SDK purity.

## Fallback And Resilience Behavior

The project does not assume model calls always succeed.

- Each main agent has deterministic fallback behavior when model generation fails.
- The signal agent can derive findings heuristically from sleep, stress, steps, mood, and note text.
- The risk agent can derive risk from the number and severity of findings.
- The intervention agent can synthesize a safe lightweight plan using goal, dietary style, allergies, and rough risk.
- If a remote specialist call fails, the coordinator generates a local fallback specialist output instead of aborting the run.
- The validation loop can still reduce intensity and simplify the plan even without an LLM.
- If a run crashes before tool initialization, a fallback failure path still marks the run as failed and records audit metadata.

This is important because the product is built to demonstrate not just agent reasoning, but also failure-aware orchestration and graceful degradation.

## Backend Platform Capabilities

The FastAPI backend is the system of record. Agents do not own persistence directly.

### Core Platform Areas

- Auth and session lookup
- Onboarding and profile management
- Accessibility preference storage
- Event ingestion and normalization
- Agent run creation and trace retrieval
- Case management
- Intervention persistence
- Notification persistence
- Persona-based resource lookup
- Audit logging
- Health-data storage and Garmin sync
- Nutrition logging and recipe management
- AI quota accounting and kill-switch controls

### Important API Behaviors

- `POST /api/events/checkin` is atomic: it creates raw signal events, creates a normalized event, creates an agent run, and dispatches the coordinator.
- `POST /api/scenarios/{id}/run` creates a seeded signal bundle, stores a normalized event, creates a run, and dispatches the coordinator.
- `GET /api/runs/{id}` returns the run plus messages, intervention, and case so the trace page can render one payload.
- `GET /api/interventions` returns the member’s recent support plans.
- `GET /api/resources` can be filtered by persona.
- `GET /api/quota/daily` exposes live cost-control counters for AI usage.

## Health And Wearable Subsystem

The health subsystem is more than a static dashboard.

- It stores daily metrics, sleep sessions, activities, sync runs, Garmin connection state, and calorie log entries.
- Garmin authentication and token caching are supported per user.
- The API can manually trigger a Garmin sync and also schedule periodic syncs with APScheduler when enabled.
- The sync engine upserts daily metrics, sleep sessions, and activities into PostgreSQL.
- A lightweight in-memory cache is used for health overview responses.
- Calorie logging supports manual entries plus an AI calorie-estimate helper.

The health overview summarizes steps, sleep, heart rate, and stress. The UI then expands that into trends, sleep-stage visualization, activity history, and food logging.

## Recipe And Nutrition Subsystem

The recipe feature set is unexpectedly deep for a wellness demo.

- Recipes can be parsed from URLs using HTML scraping, JSON-LD extraction, and recipe-specific plugin extraction.
- The URL parser includes basic SSRF-style safeguards by validating scheme, hostname, and private/reserved address resolution.
- Recipes can also be parsed from freeform pasted text using an LLM that outputs structured JSON.
- Parsed recipes are editable before saving, including tags, grouped ingredients, categories, sections, and normalized instruction steps.
- The backend seeds a template recipe library if none exists.
- Recommended recipes are matched against `meal_constraints` from the latest intervention.
- Meal-plan slots exist in the backend for future calendar-style meal planning.
- The recipe detail page annotates instruction text so hovering underlined ingredient references reveals quantities and sections.

This subsystem makes NüMe feel more like a real consumer wellness product rather than only an agent workflow demo.

## Auth, Roles, And Demo Access

Authentication is built around Clerk.

- The frontend uses Clerk React components and stores onboarding status in Clerk metadata.
- The backend verifies Clerk session tokens and can create or link local users on first sign-in.
- Seeded roles exist for members, coordinators, and admins.
- The app uses route guards so member pages, coordinator pages, and admin pages are role-specific.
- Privileged real accounts can impersonate seeded demo users through a controlled header-based demo mode.

The repo also includes logic for first-time provisioning when the backend needs to fetch a Clerk user’s email or username.

## Data Model Summary

The domain model is explicit and broad enough to support multiple product surfaces.

### Identity And Profile

- `users`
- `user_profiles`
- `accessibility_preferences`

### Signals And Agent Execution

- `wearable_events`
- `behavior_events`
- `normalized_events`
- `agent_runs`
- `agent_messages`
- `cases`
- `interventions`
- `notifications`
- `resources`
- `audit_logs`

### Health And Nutrition

- `health_daily_metrics`
- `health_sleep_sessions`
- `health_activities`
- `health_sync_runs`
- `garmin_connections`
- `health_calorie_log`
- `recipes`
- `meal_plan_slots`

### Cost Control

- `ai_rate_counters`

There is also a shared Pydantic domain-model package used across agents and the API to keep core types aligned.

## Engineering Characteristics Visible In The Repo

The project contains evidence of work across multiple engineering layers:

- Frontend application architecture with role-gated navigation, query polling, data mapping, and responsive UI flows
- Backend API design with async SQLAlchemy, Alembic migrations, DTO schemas, and route-level permissions
- Domain modeling for users, signals, interventions, cases, notifications, health metrics, recipes, and meal planning
- Agent orchestration design with parallel work, remote specialization, validation loops, and trace persistence
- Integration work around Clerk, Garmin, OpenAI/Azure-compatible model endpoints, and recipe ingestion
- Deployment and operations work through Docker Compose, CORS, readiness probes, environment-based config, and Cloudflare-oriented rollout planning
- Demo engineering through scenario seeding, synthetic data, internal impersonation, and judge-friendly trace surfaces
- Cost and safety controls through AI kill-switches, quota buckets, fail-closed rate limiting, and conservative fallbacks

## Testing And Verification

As of April 1, 2026, the backend and agent test suites pass:

- `58` tests passed in `5.26s`

The automated coverage includes:

- auth and Clerk syncing behavior
- database configuration
- event-ingest and run pipeline flows
- health endpoints
- recipe parsing and CRUD behavior
- rate limiting and quota logic
- agent-run dispatch plumbing
- validation-loop behavior and plan merging
- model-client configuration logic

Frontend automated coverage is currently light. There is only a minimal example test in the React app, so confidence in UI behavior still depends more on manual verification than on robust UI test coverage.

## Seeded Demo Content

The seed script creates a meaningful demo environment instead of only bare tables.

- `10` demo users total
- `8` member accounts across the four personas
- `2` staff accounts: coordinator and admin
- persona-specific resource records
- `14` days of health data for each seeded member
- three named demo scenarios: stressed student, exhausted caregiver, and older adult routine disruption

The seeded data is structured to create believable narratives, not random filler. For example, the student preset trends toward low sleep and high stress, while the caregiver preset trends toward fragmented recovery and high burden.

## Deployment State

The repo documents and supports two deployment stories.

### Current Live Shape

- frontend on `nume-demo.com`
- API on `api.nume-demo.com`
- FastAPI backend with PostgreSQL
- Docker Compose for local development
- Cloudflare Tunnel used in the current production split

### Recommended Next Shape

- Cloudflare Pages for the frontend
- Cloudflare Worker or API route in front
- Cloudflare Container for FastAPI
- Supabase Postgres as the database
- Clerk retained as the auth provider

The codebase is intentionally not being rewritten into Workers yet because the current backend relies on Python runtime features, SQLAlchemy, asyncpg, thread-based work, and APScheduler.

## Future Ideas And Roadmap

The repo already contains hints of likely next steps, and the current architecture suggests several strong future directions.

### Near-Term Logical Next Steps

- Replace the ADK compatibility layer and HTTP specialist shim with a fully wired Google ADK runtime and real A2A specialist servers.
- Move from Cloudflare Tunnel to the documented Cloudflare Container plus Supabase architecture.
- Turn in-process background execution into a more durable queue or worker system for reliability under higher traffic.
- Add stronger health checks and readiness for specialist services so orchestration does not race unready containers.
- Expand frontend automated testing so key user flows are validated end to end.

### Product Expansion Opportunities

- Add more wearable or health integrations beyond Garmin, such as Apple Health, Fitbit, Oura, or smartwatch ecosystems.
- Build a stronger consent and support-network model so escalation, outreach, and trusted-contact workflows are explicit rather than demo-oriented.
- Evolve the case-management experience to include assignment, coordinator notes, triage history, and follow-up workflows.
- Extend recipe and meal-planning features into grocery planning, pantry awareness, recurring meal suggestions, and adherence tracking.
- Replace static persona assignment with analytics-derived persona formation so the system continuously rebuilds the user’s support profile from observed behavior, trends, outcomes, and preference signals.
- Introduce stronger longitudinal personalization so recommendations compare against a user’s own baseline, not just simple threshold heuristics.
- Add more notification channels such as email, SMS, or push, ideally with delivery-state tracking beyond queued versus delivered.
- Expand observability with richer admin analytics, run performance metrics, failure dashboards, and trend reporting.
- Expose a more polished public trace visualization or ADK dev-style interface for demos, debugging, and explainability.

### Higher-Ambition Strategic Directions

- Turn NüMe into a broader support-operations platform where specialized agents coordinate not only wellness advice but also referrals, scheduling, social-support check-ins, and community-resource handoffs.
- Add organization or tenant support for schools, caregiving organizations, clinics, or senior-support programs.
- Introduce outcomes tracking so the platform can measure whether recommendations improved sleep, stress, adherence, or recovery over time.

## Important Clarifications For Any Future LLM Reader

Some repository docs contain historical or partially outdated information. The most important clarifications are:

- The frontend is currently a Vite + React SPA, not a Next.js app.
- The codebase still carries Google ADK terminology and optional imports, but current JSON generation is implemented through an OpenAI/Azure OpenAI-compatible client wrapper.
- The repo is no longer just a narrow “nutrition app” concept. It has evolved into a broader wellness and care-coordination platform with nutrition as one subsystem.
- Garmin integration exists in code, but its practical maturity still depends on environment configuration and deployment setup.
- The backend/agent code is well covered by tests; the frontend is much less so.

## Bottom Line

NüMe is a full-stack, multi-surface wellness and care-coordination platform whose most distinctive trait is the combination of user-facing product functionality, explainable multi-agent execution, and a longer-term vision for adaptive personalization. The repository demonstrates product design, API design, data modeling, auth, deployment planning, demo engineering, observability, and multi-agent systems work in one codebase. Its strongest conceptual differentiator is not the current four-persona MVP routing by itself, but the vision that NüMe will eventually construct each user’s support profile from their own analytics and become more accurate the longer that person uses it.
