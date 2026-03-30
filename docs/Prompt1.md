You are a senior staff engineer, distributed systems architect, and Google Agent Development Kit implementation lead.

Build a production-grade hackathon MVP called NüMe.

NüMe is a multi-agent care coordination platform built on Google ADK from day one. It uses wearable signals, behavioral patterns, profile context, and accessibility preferences to detect emerging strain, coordinate specialist reasoning, validate its own recommendations, and trigger practical support actions.

This must be implemented as a real Google ADK system, not a generic “AI app” and not a normal web app with one chatbot.

NON-NEGOTIABLE IMPLEMENTATION REQUIREMENTS

1. Use Google ADK explicitly in the implementation.
2. Use Python ADK as the primary agent framework.
3. Use real ADK workflow primitives:
   - root orchestrator agent
   - specialist agents
   - ParallelAgent
   - LoopAgent
4. Use real ADK A2A support for remote specialists.
5. Use MCP or MCP-like tools through ADK tool abstractions.
6. Build the final architecture immediately. Do not stage this as “simple now, expand later.”
7. Do not simulate the architecture with plain functions if ADK provides the mechanism.
8. Do not collapse everything into one monolithic agent.
9. Build a serious business platform under the agents:
   - persistence
   - policy checks
   - case management
   - audit logging
   - observability
   - traceability
10. Produce actual code, not a conceptual scaffold.

BUSINESS MISSION

NüMe supports:
- stressed students
- exhausted caregivers
- older adults
- users needing accessible wellness support

The platform should:
- ingest signals from wearables, check-ins, and behavior events
- normalize them into support-relevant events
- run specialist reasoning in parallel
- route to the correct remote persona specialist through A2A
- validate conflicts and safety through a loop
- take real actions
- persist a full trace
- expose dashboards for member, coordinator, and admin users

THIS IS A CARE COORDINATION PLATFORM, NOT A FITNESS APP

The system is care-coordination-first.
Nutrition, movement, routine, and self-care can appear as interventions, but they are not the core architecture.
The core architecture is:
- signal interpretation
- persona-aware reasoning
- risk stratification
- intervention planning
- empathy and accessibility
- escalation and support action
- auditability and traceability

FINAL TARGET ARCHITECTURE

Build the system with these layers:

1. EXPERIENCE LAYER
- member web app
- care coordinator dashboard
- admin and trace dashboard
- scenario runner / demo controls
- accessibility-friendly UI

2. CORE PLATFORM SERVICES LAYER
These are the system of record and must be durable services:
- auth and RBAC service
- user profile service
- accessibility preferences service
- consent and permissions service
- event ingestion service
- case management service
- interventions service
- notifications / outreach service
- resource and referral service
- audit logging service
- analytics / dashboard service

Important:
Agents do not directly own persistent workflow state.
Agents interpret, recommend, and trigger.
Platform services persist, enforce policy, and record workflow outcomes.

3. AGENTIC CONTROL LAYER USING GOOGLE ADK
Implement the following agents as explicit ADK agents.

A. Care Coordinator Agent
Role:
- root orchestrator agent
Responsibilities:
- receive normalized event or support request
- choose which specialists to invoke
- run independent specialists with ParallelAgent
- invoke remote specialists through A2A when persona-specific expertise is needed
- collect outputs
- run LoopAgent-based validation and refinement
- choose final action path
- assemble final explanation
- hand off actions to platform services

B. Data Intake Agent
Role:
- ingestion and normalization agent
Responsibilities:
- parse wearable signals
- parse manual check-ins
- parse behavioral events
- normalize raw inputs into structured support events
Outputs examples:
- stress_spike_detected
- sleep_decline_3_days
- low_activity_pattern
- missed_medication
- negative_checkin
- social_withdrawal_risk

C. Signal Interpretation Agent
Role:
- convert normalized events into support-relevant findings
Responsibilities:
- analyze sleep, stress, activity, adherence, routine disruption, and anomaly patterns
Outputs:
- structured findings with confidence, severity, and supporting evidence

D. Persona Context Agent
Role:
- contextual reasoning by user type
Responsibilities:
- reinterpret the same event differently for student, caregiver, older adult, or accessibility-focused user
- enrich findings using profile, history, and current support context

E. Risk Stratification Agent
Role:
- urgency and intervention priority
Responsibilities:
- assign risk level
- determine follow-up urgency
- determine escalation need
- output confidence score
Outputs examples:
- low concern
- moderate concern
- high concern
- coordinator review required

F. Intervention Planning Agent
Role:
- choose next-best actions
Responsibilities:
- propose supportive actions such as:
  - supportive message
  - recovery-oriented daily plan
  - simple self-care plan
  - campus or community support recommendation
  - caregiver respite resource
  - check-in request
  - support case creation
  - coordinator task
  - trusted-contact suggestion subject to consent

G. Empathy and Check-In Agent
Role:
- human-centered messaging
Responsibilities:
- convert findings into supportive, non-judgmental, emotionally appropriate language
- avoid cold, clinical, or punitive wording

H. Accessibility Adaptation Agent
Role:
- usability and inclusive output adaptation
Responsibilities:
- adapt the final plan for:
  - large text
  - simplified language
  - low-energy mode
  - older-adult-friendly presentation
  - lower-complexity instructions
  - voice-ready format

I. Escalation and Support Network Agent
Role:
- action trigger agent
Responsibilities:
- create support case
- assign coordinator follow-up
- notify trusted contact if policy and consent allow
- queue outreach
- generate daily support plan
- recommend resources
- persist planned actions through service calls

J. Audit and Explanation Agent
Role:
- explainability and trace
Responsibilities:
- produce structured rationale
- summarize why action was chosen
- persist trace data for UI and operators

K. Validation Loop Agent
Role:
- self-correction and safety review
Responsibilities:
- detect contradictions between agents
- detect unsupported escalation
- detect missing evidence
- detect accessibility mismatch
- detect policy violation
- rerun selected specialists if needed
- revise, approve, or halt the plan

ADK-SPECIFIC IMPLEMENTATION REQUIREMENTS

Use Google ADK explicitly.

1. Build the local main workflow with ADK agents.
2. Use ParallelAgent for the first independent reasoning phase.
3. Use LoopAgent for iterative validation and refinement.
4. Use ADK A2A support for remote persona specialists.
5. Prefer the easiest documented A2A exposure path for Python:
   - expose remote specialists with to_a2a(root_agent) where suitable
   - or use adk api_server --a2a with agent cards where beneficial
6. Use RemoteA2aAgent or equivalent ADK A2A client patterns for consuming remote specialists.
7. Use ADK tool integration patterns for external tools and actions.
8. Keep the architecture faithful to ADK, not just inspired by it.

REMOTE A2A SPECIALISTS

These must be implemented as separate remote specialist agents and invoked explicitly through A2A:

1. Student Support Specialist
Responsibilities:
- academic stress interpretation
- burnout-sensitive support
- campus support pathway selection

2. Caregiver Burnout Specialist
Responsibilities:
- caregiver burden interpretation
- realistic intervention choices
- respite or support escalation recommendations

3. Senior Wellness Specialist
Responsibilities:
- routine disruption analysis
- low-complexity plan shaping
- outreach and stability recommendations

Optional fourth remote specialist:
4. Accessibility Coach Specialist
Responsibilities:
- accessibility-first adaptation advice for complex cases

A2A DEMO REQUIREMENT

The main system must visibly do this:
- detect user persona and case need
- discover/select the appropriate remote specialist
- invoke the specialist through A2A
- merge specialist output into the plan
- continue into validation and action

PARALLELAGENT REQUIREMENT

The initial independent reasoning stage must use ParallelAgent across these sub-agents:
- Signal Interpretation Agent
- Persona Context Agent
- Intervention Planning Agent
- Accessibility Adaptation Agent

The root coordinator must merge the outputs.

LOOPAGENT REQUIREMENT

After the first merged plan is produced, run a LoopAgent-controlled validation cycle.
The loop must:
- inspect current plan
- check conflict, confidence, policy, and safety
- rerun selected specialists when needed
- stop when the plan is safe and supported
- stop early if safety cannot be established

The loop must not be cosmetic.
It must be reflected in logs, trace storage, and UI.

TOOLING AND MCP LAYER

Implement an ADK-compatible tool layer for grounding and action.

Required tools:
- wearable data connector or simulator
- manual check-in ingestion tool
- behavior event ingestion tool
- resource directory lookup tool
- notification tool
- case creation tool
- coordinator task creation tool
- audit persistence tool
- optional reminder or calendar tool

If practical, expose external capabilities through MCP and use ADK’s MCP integration patterns.
At minimum, structure the tool layer so ADK agents consume tools rather than inventing actions in pure text.

ACTIONABILITY REQUIREMENT

For successful scenarios, the system must perform real actions such as:
- create case in database
- create intervention record
- send supportive notification
- assign coordinator follow-up
- queue outreach
- store audit trace
- update dashboard-visible state

The system must not stop at generating recommendations.

TRACEABILITY REQUIREMENT

Persist and expose:
- agent runs
- agent inputs and outputs
- parallel branch activity
- A2A invocation history
- loop iterations and reruns
- final action chosen
- rationale summary
- timestamps
- statuses
- errors and retries

The trace dashboard must clearly show:
- which agents ran
- which ran in parallel
- when remote specialists were called
- what the loop corrected or rejected
- what final action was taken

This is a first-class feature, not an afterthought.

DATA MODEL

Create durable models and schema for:
- users
- user_profiles
- accessibility_preferences
- consent_settings
- wearable_events
- behavior_events
- normalized_events
- cases
- interventions
- support_contacts
- notifications
- resources
- agent_runs
- agent_messages
- audit_logs

TECH STACK

Use this stack unless there is a compelling implementation reason not to:

Frontend:
- Next.js
- TypeScript
- Tailwind CSS
- accessible component design

Backend / platform services:
- FastAPI
- Python 3.10+
- PostgreSQL
- SQLAlchemy or equivalent ORM
- Pydantic for schemas

Agent framework:
- Google ADK for Python

Queues / async:
- Redis or lightweight background queue if useful

Infra:
- Docker Compose for local dev
- deployment-ready structure for Google Cloud / Cloud Run

Observability:
- structured logging
- persisted trace records
- clean demo-friendly trace UI

MONOREPO STRUCTURE

Create this monorepo:

/
  apps/
    web/
    api/
  services/
    agents/
      coordinator/
      data_intake/
      signal_interpretation/
      persona_context/
      risk_stratification/
      intervention_planning/
      empathy_checkin/
      accessibility_adaptation/
      escalation_support/
      audit_explanation/
      validation_loop/
    remote_specialists/
      student_support/
      caregiver_burnout/
      senior_wellness/
      accessibility_coach/
    tools/
  packages/
    shared-types/
    config/
    ui/
  infra/
    docker/
    seed/
    deployment/
  docs/
    architecture/
    api-contracts/
    demo-scenarios/
    operations/
  tests/

UI REQUIREMENTS

Build these screens:
1. Member dashboard
- current support status
- recent wellness signals
- recommended plan
- empathy-first message
- accessibility-aware display

2. Care coordinator dashboard
- open cases
- recent alerts
- interventions
- follow-up tasks
- user-level summary

3. Admin / trace dashboard
- agent runs
- A2A calls
- loop iterations
- errors and retries
- action outcomes

4. Scenario runner
- load a seeded scenario
- trigger orchestration
- inspect outcome and trace

SCENARIOS TO IMPLEMENT END TO END

1. Stressed Student
Input:
- sleep decline
- stress spike
- negative check-in
Expected behavior:
- Data Intake normalizes event
- ParallelAgent runs initial specialists
- Student Support Specialist is invoked through A2A
- LoopAgent validation runs
- final supportive plan is produced
- resource suggestion is added
- notification and trace are persisted

2. Exhausted Caregiver
Input:
- disrupted sleep
- low activity
- burnout-like check-in
Expected behavior:
- Caregiver Burnout Specialist is invoked through A2A
- risk is elevated
- coordinator follow-up or support task is created
- empathy-first message is generated
- trace is stored

3. Older Adult Support Risk
Input:
- routine disruption
- low activity
- missed reminder response
Expected behavior:
- Senior Wellness Specialist is invoked through A2A
- accessibility adaptation is applied
- support case is created
- outreach or check-in is queued
- trace is stored

4. Accessibility-Focused User
Input:
- stress or disruption event plus accessibility preferences
Expected behavior:
- plan is adapted for simplified language / low-complexity output
- trace shows accessibility influence clearly

ENGINEERING QUALITY REQUIREMENTS

- strong typing
- clear interfaces between agents, tools, and platform services
- no spaghetti logic
- policy gate every sensitive action
- idempotent action execution
- structured logs
- input validation
- basic retries / graceful degradation for tool failures
- unit tests for agent logic
- integration tests for end-to-end scenarios
- working seed data
- clean README
- local run instructions
- environment variables documented
- production-minded code organization

DELIVERABLES

Produce:
1. working monorepo
2. ADK-based agent implementation
3. A2A remote specialist implementation
4. DB schema and migrations
5. seeded demo data
6. frontend dashboards
7. trace UI
8. test suite
9. README with setup and run commands
10. architecture doc
11. API contract doc
12. demo script for judges

EXECUTION ORDER

Work in this exact order and actually create files and code:

1. write final architecture summary
2. generate monorepo structure
3. define shared domain models
4. define DB schema and migrations
5. define platform service contracts
6. implement core platform services
7. implement ADK root coordinator
8. implement local ADK specialist agents
9. implement remote A2A specialists
10. wire ParallelAgent workflow
11. wire LoopAgent validation workflow
12. implement tool layer
13. persist traces and audit records
14. implement dashboards
15. add seed scenarios
16. add tests
17. add docs and run instructions

IMPORTANT BUILD RULES

- Do not defer core architecture to “phase 2”
- Do not replace ADK with a homemade orchestration layer
- Do not fake A2A with ordinary function calls
- Do not omit traceability
- Do not leave placeholder-only files unless absolutely unavoidable
- Prefer working vertical slices, but each slice must still respect the final architecture
- Keep the codebase faithful to the final ADK architecture from the start

OUTPUT STYLE

For each milestone:
- create files
- write code
- explain design choices briefly
- list assumptions
- list next concrete steps

Begin now with:
1. final architecture summary
2. repository structure
3. shared domain models
4. database schema
5. API contract draft
6. core implementation foundation