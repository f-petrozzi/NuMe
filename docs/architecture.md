# Architecture — NüMe

---

## Overview

NüMe has three layers. The experience layer is what users see. The platform services layer is the system of record. The agentic control layer is the intelligence layer built on Google ADK.

Agents do not own state. Agents read from and write to platform services via ADK tool calls. Platform services own persistence, policy enforcement, and workflow continuity.

---

## Layer 1: Experience Layer (Vite/React SPA)

Four screens:

```
Member Dashboard
  └── Current signals summary
  └── Support plan (meal, activity, wellness)
  └── Empathy message
  └── Risk badge
  └── Link to trace

Care Coordinator Dashboard
  └── Open cases list (persona, risk level, status)
  └── Click to view member summary and intervention

Trace / Admin Dashboard
  └── Agent run list
  └── Click run → message tree view
        ├── Parallel branch: Signal Interpretation
        ├── Parallel branch: Risk Stratification
        ├── Parallel branch: Intervention Planning
        ├── A2A call: Student Support OR Caregiver Burnout
        ├── Loop iteration 1 → Validation
        ├── Loop iteration 2 (if needed)
        └── Final action: intervention + case + notification

Scenario Runner
  └── Dropdown: select seeded scenario
  └── Trigger button
  └── Live status polling (React Query)
  └── Auto-navigate to trace on completion
```

---

## Layer 2: Platform Services Layer (FastAPI)

These are REST endpoints consumed by agents (as ADK tools) and by the frontend.

```
GET    /api/auth/me              ← Clerk-authenticated session lookup

POST   /api/onboarding
GET    /api/profile
PUT    /api/profile

POST   /api/events/ingest          ← raw signal event
POST   /api/events/simulate        ← wearable simulator (for demo)
GET    /api/events/recent          ← last N normalized events for user

POST   /api/runs/trigger           ← kick off Care Coordinator Agent
GET    /api/runs/:id               ← full trace with agent messages
GET    /api/runs                   ← list of runs for user or all (admin)

GET    /api/cases                  ← coordinator: list open cases
GET    /api/cases/:id
PATCH  /api/cases/:id              ← update status

GET    /api/interventions/:run_id  ← meal, activity, wellness, empathy message

GET    /api/resources              ← persona-filtered resource list
GET    /api/notifications          ← queued notifications for user

GET    /api/scenarios              ← list seeded scenarios
POST   /api/scenarios/:id/run      ← convenience: simulate + trigger
```

---

## Layer 3: Agentic Control Layer (Google ADK)

### Execution flow

```
POST /api/runs/trigger
    │
    ▼
Care Coordinator Agent (root, SequentialAgent)
    │
    ├─ Step 1: get_user_profile_tool + get_recent_signals_tool
    │
    ├─ Step 2: ParallelAgent
    │     ├── Signal Interpretation Agent  →  findings: [stress_spike, sleep_decline_3d]
    │     ├── Risk Stratification Agent    →  risk: high, confidence: 0.82
    │     └── Intervention Planning Agent  →  draft plan: meal, activity, wellness
    │
    ├─ Step 3: A2A dispatch (based on persona_type)
    │     ├── persona=student    → RemoteA2aAgent → Student Support Specialist
    │     ├── persona=caregiver  → RemoteA2aAgent → Caregiver Burnout Specialist
    │     └── (other personas: Accessibility Adaptation Agent runs locally)
    │
    ├─ Step 4: Empathy and Check-In Agent
    │     └── Converts plan into supportive user-facing language
    │
    ├─ Step 5: LoopAgent (Validation Loop, max 3 iterations)
    │     └── Validation Loop Agent checks each iteration:
    │           - Contradictions between findings and plan
    │           - Accessibility mismatches
    │           - Policy violations (escalation without consent)
    │           - Low-confidence findings with unsupported actions
    │         → If issues found: refine plan, rerun relevant specialist
    │         → If safe: approve and exit loop
    │         → If unsafe after 3 iterations: halt and flag for coordinator
    │
    └─ Step 6: Escalation and action
          ├── create_intervention_tool    (always)
          ├── create_case_tool            (if risk >= moderate)
          ├── send_notification_tool      (always: queued message to member)
          └── persist_audit_tool          (always)
```

### Agent definitions

| Agent | ADK type | Lives in |
|---|---|---|
| Care Coordinator | `SequentialAgent` (root) | `services/agents/coordinator/` |
| Signal Interpretation | `LlmAgent` | `services/agents/signal_interpretation/` |
| Risk Stratification | `LlmAgent` | `services/agents/risk_stratification/` |
| Intervention Planning | `LlmAgent` | `services/agents/intervention_planning/` |
| Empathy and Check-In | `LlmAgent` | `services/agents/empathy_checkin/` |
| Validation Loop | `LoopAgent` wrapping a `LlmAgent` | `services/agents/validation_loop/` |
| Student Support | `LlmAgent` exposed via `adk api_server --a2a` | `services/remote_specialists/student_support/` |
| Caregiver Burnout | `LlmAgent` exposed via `adk api_server --a2a` | `services/remote_specialists/caregiver_burnout/` |

---

## Data flow diagram

```
User submits check-in or scenario runner fires
        │
        ▼
POST /api/events/ingest
        │
        ▼
wearable_events / behavior_events tables
        │
        ▼
Normalization: normalized_events record created
        │
        ▼
POST /api/runs/trigger → agent_runs record created (status: running)
        │
        ▼
Care Coordinator Agent starts
  (reads profile + signals via tools)
        │
    ParallelAgent
  ┌───┴───┐───────────┐
  ▼       ▼           ▼
Signal  Risk      Intervention
Interp  Strat     Planning
  └───┬───┘───────────┘
      ▼
  Results merged by Coordinator
      │
  A2A specialist call
      │
  Empathy Agent
      │
  LoopAgent validation
      │
  Final plan assembled
      │
  ┌───┼───┐
  ▼   ▼   ▼
Case Notif Intervention
 DB   DB    DB
      │
  agent_runs updated (status: completed)
  audit_logs written
      │
      ▼
Frontend polls /api/runs/:id → displays trace + plan
```

---

## Monorepo structure

```
/
  apps/
    web/                    ← Vite/React SPA frontend
    api/                    ← FastAPI backend
  services/
    agents/
      coordinator/
      signal_interpretation/
      risk_stratification/
      intervention_planning/
      empathy_checkin/
      validation_loop/
    remote_specialists/
      student_support/      ← runs as separate ADK A2A server
      caregiver_burnout/    ← runs as separate ADK A2A server
    tools/                  ← ADK FunctionTool definitions
  packages/
    shared-types/           ← Pydantic models shared across agents and API
  infra/
    docker/                 ← Dockerfiles
    seed/                   ← seed data scripts
    migrations/             ← Alembic migrations
  docs/
  tests/
```

---

## Design principles

1. **Agents are not the system of record.** Agents interpret, recommend, and trigger. FastAPI services persist and enforce policy.
2. **Every sensitive action is policy-gated.** Case creation, notifications, and escalation check consent and risk thresholds via tool logic.
3. **Traceability is first-class.** Every agent message is persisted. The trace UI is a core deliverable, not an afterthought.
4. **ADK-aligned structure.** Code is organized around `ParallelAgent`, `LoopAgent`, and `RemoteA2aAgent` naming and structure. Current execution uses a custom Python orchestrator (`execute_parallel` via `ThreadPoolExecutor`, direct Gemini API via `GeminiJsonClient`, HTTP `httpx` for A2A). `adk_compat.py` bridges to real Google ADK when the SDK is installed — real ADK runtime is a planned upgrade.
5. **Demo-first scope.** Every architectural decision is validated against: "can this be demonstrated in 30 seconds to a judge?"
