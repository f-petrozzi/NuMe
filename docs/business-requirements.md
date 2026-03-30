# Business Requirements — NüMe

NüMe is a multi-agent care coordination platform that uses health signals (wearable-simulated or manually entered) to detect emerging strain, reason about it in the context of the user's persona, and deliver an empathy-first support plan with concrete wellness, meal, and activity recommendations.

It is not a fitness tracker. It is not a chatbot. It is a care operations system with an agentic intelligence layer built on Google ADK.

---

## In scope for hackathon MVP

| Requirement | Problem / user need | Primary user | Success metric | Priority |
|---|---|---|---|---|
| Single platform combining health signals and care coordination | Users currently need multiple apps; neither a wellness tracker nor a chatbot alone is sufficient | All personas | Users see current health signals and a personalized care plan on one dashboard | P0 |
| Onboarding with persona, goals, and preferences | Recommendations are not useful without knowing who the user is | All users | Every user completes onboarding before accessing the dashboard | P0 |
| Health signal ingestion via wearable simulator or manual check-in | Users need to submit data without requiring a real device for the hackathon demo | All users | Users can submit a signal event and trigger an agent run in under 30 seconds | P0 |
| Multi-agent orchestration using Google ADK | Platform must demonstrate real agentic architecture, not a wrapper around one LLM call | Platform / judges | ParallelAgent and LoopAgent execute and are visible in the trace dashboard | P0 |
| Persona-aware specialist reasoning | A stress signal means different things for a student vs a caregiver vs an older adult | All personas | Different personas produce different support plans from identical input signals | P0 |
| Remote A2A specialist invocation | Demonstrate distributed multi-agent collaboration for Google challenge alignment | Platform / judges | Student Support and Caregiver Burnout specialists are invoked through A2A and visible in the trace | P0 |
| Risk stratification at four levels | The platform must translate signals into urgency to decide what action to take | All users | Every agent run produces a risk level: low, moderate, high, or critical | P0 |
| Intervention planning with meal, activity, and wellness options | Users need concrete, persona-appropriate action recommendations, not just a diagnosis | All users | Every completed run produces at least one meal suggestion, one activity suggestion, and one wellness action | P0 |
| Empathy-first user-facing messaging | Clinical or punitive language reduces trust and engagement | All users | Messages are supportive and non-judgmental; no "you failed" framing | P0 |
| Validation loop with visible self-correction | Plans must be checked for contradictions and safety gaps before delivery | All users | Loop runs at least once per agent run; iterations and corrections are visible in trace | P0 |
| Support case creation for moderate or higher risk | High-risk users need a coordinator follow-up, not just a message | Coordinators | Cases are created in the database when risk is moderate or above | P0 |
| Member dashboard | Users need a calm, clear view of their current signals, support plan, and empathy message | Members | Dashboard loads a complete support plan within 10 seconds of a signal event | P0 |
| Care coordinator dashboard | Coordinators need to see which members need follow-up and why | Coordinators | Dashboard shows all open cases with persona type and risk level | P0 |
| Agent trace dashboard | Judges and operators need to inspect the multi-agent execution | Admins / judges | Trace shows agent sequence, parallel branches, A2A calls, loop iterations, and final action | P0 |
| Scenario runner for demo | Judges need reliable, repeatable demo triggers without live user setup | Judges / demo | Loading a seeded scenario and triggering the pipeline produces a complete plan and trace in under 30 seconds | P0 |
| Accessibility-adapted output for accessibility persona | Older adults and users with cognitive load constraints need simpler instructions | Accessibility persona | Plans for this persona use simplified language and reduced-step guidance | P1 |
| Pseudonymized data storage | Health data must not be tied to personally identifiable information | All users | Health, recommendation, and case tables contain no names or email addresses | P1 |
| Audit log of every agent run | Traceability is a first-class requirement, not an afterthought | Platform | Every agent run has a durable, queryable record with inputs, outputs, timestamps, and status | P1 |

---

## Back in MVP scope

These features were initially deferred but are back in scope for the hackathon MVP.

| Requirement | Priority |
|---|---|
| Garmin OAuth connection and background sync | P1 |
| Health data dashboard (steps, sleep, HR, HRV, stress, calories) | P1 |
| Recipe import from URL | P1 |
| Recipe import from pasted text | P1 |
| Recipe storage, search, and detail view | P1 |
| Meal planning with recipe linkage | P2 |
| Manual calorie log with AI calorie estimate | P2 |

---

## Out of scope for hackathon MVP (future phase)

| Requirement | Reason deferred |
|---|---|
| Apple Health integration | No iOS device available in hackathon context |
| Push notifications and reminders | Requires notification service and tokens; not needed for demo |
| Similar-user clustering | Requires a user base or synthetic cohort |
| Vector database for semantic search | Plain SQL sufficient for hackathon scale |
| Advanced collaborative filtering | Requires production data |
| Multi-role admin access | Single admin role sufficient |
| Senior Wellness and Accessibility Coach A2A specialists | Two A2A specialists enough to demonstrate the pattern |
