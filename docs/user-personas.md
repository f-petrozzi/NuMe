# User Personas — NüMe

NüMe uses persona type as the primary routing key for specialist agent selection and intervention framing. All four personas share the same core architecture — only the specialist reasoning path and output framing change.

Persona type is set during onboarding and stored in `user_profiles.persona_type`.

---

## Persona 1: Stressed Student

**Who they are:** University student balancing coursework, social life, and basic self-care. Often sleep-deprived and stressed around exams and deadlines. May not recognize burnout early.

**Primary signals that indicate strain:**
- Sleep hours below 6
- Stress level 7 or above
- Negative or flat mood check-in
- Low step count / low activity
- Skipped routines or check-ins

**What they need:**
- Acknowledgment that the pressure is real
- Low-burden support (not a 5-step wellness plan)
- Campus resource suggestions (counseling, tutoring, peer support)
- Gentle re-entry points for sleep and routine
- Short, encouraging language

**Remote A2A specialist invoked:** Student Support Specialist

**Example intervention framing:**
> "Your sleep and stress signals suggest you're in a high-pressure stretch. Today's plan is designed to reduce load, not add to it — a short reset activity, a meal that won't take energy to decide, and one check-in reminder for tonight."

---

## Persona 2: Exhausted Caregiver

**Who they are:** Adult caring for a family member (child, parent, or partner with health needs). Self-care is deprioritized. Burnout builds silently. Time and energy are both scarce.

**Primary signals that indicate strain:**
- Consistently poor sleep
- Very high stress
- Low or zero activity
- Mood check-ins expressing exhaustion, guilt, or numbness
- Missed or skipped check-ins

**What they need:**
- Recognition that their situation is genuinely hard
- Realistic, micro-effort interventions (not gym workouts)
- Respite and support resources (caregiver hotlines, support groups, meal delivery)
- Coordinator follow-up when risk is high
- Trusted-contact or escalation path when consent allows

**Remote A2A specialist invoked:** Caregiver Burnout Specialist

**Example intervention framing:**
> "You're carrying a lot right now. Your signals suggest your own recovery is being depleted. Today's plan focuses on the smallest possible steps to give you back a little space — and flags a resource that might help with the weight you're carrying."

---

## Persona 3: Older Adult

**Who they are:** Adult 65+ managing routine, health, and independence. May have limited mobility, cognitive load concerns, or social isolation. Routine disruption is an early warning sign.

**Primary signals that indicate strain:**
- Significant drop in steps or activity
- Sleep disruption
- Missed check-ins or reminder non-response
- Low mood or notes indicating social withdrawal

**What they need:**
- Low-complexity, step-by-step guidance
- Safe, low-impact movement recommendations
- Routine reinforcement, not overhaul
- Coordinator or trusted-contact summary when appropriate
- Simplified language; optional large-text display

**Remote A2A specialist invoked:** (Senior Wellness Specialist — future phase; falls back to local Intervention Planning + Accessibility Adaptation for MVP)

**Example intervention framing:**
> "We noticed a change in your routine over the past few days. Today's plan is simple and designed to be easy to follow — one short activity, a meal suggestion, and a check-in reminder for this evening."

---

## Persona 4: Accessibility-Focused User

**Who they are:** User with chronic illness, disability, or condition that creates fatigue, cognitive load, or mobility limitations. Standard wellness plans are often not usable. Pacing is critical.

**Primary signals that indicate strain:**
- Energy-based check-in low
- Activity disruption
- High stress with low capacity

**What they need:**
- Fatigue-aware planning (energy budgeting, not step counts)
- Simplified language and reduced-complexity instructions
- Adaptive pacing: "do one, rest, do one"
- Low-impact or seated alternatives
- No pressure framing; opt-out friendly

**Remote A2A specialist invoked:** (Accessibility Coach Specialist — future phase; handled by Accessibility Adaptation Agent locally for MVP)

**Example intervention framing:**
> "Today's plan is built around your current energy. Each suggestion has a low-effort version. Do what feels possible — that's the whole goal."

---

## How persona affects the pipeline

| Stage | How persona is used |
|---|---|
| Signal normalization | Adds persona context to normalized event payload |
| Parallel reasoning | All local specialists receive persona type in their input |
| A2A routing | Coordinator selects specialist based on `persona_type` field |
| Intervention planning | Meal, activity, and wellness options filtered by persona constraints |
| Accessibility adaptation | Triggered automatically for `older_adult` and `accessibility_focused`; optional for others |
| Empathy messaging | Tone and framing adjusted by persona and risk level |
