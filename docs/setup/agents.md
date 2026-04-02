# Setup — ADK Local Agents (Person 2)

You own: `services/agents/`
Your branch: `feat/agents`

---

## What you're building

The local Google ADK agent pipeline:
- Care Coordinator Agent (root orchestrator)
- Signal Interpretation, Risk Stratification, Intervention Planning (run in parallel)
- Empathy and Check-In Agent
- Validation Loop Agent (LoopAgent, max 3 iterations)

You are NOT building the A2A remote specialists or the tool HTTP layer — that's Person 3.
You are NOT building any FastAPI routes or frontend.

---

## Prerequisites

```bash
python 3.11+
cd apps/api
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

The local coordinator now runs through real Google ADK primitives:
- `SequentialAgent` for the coordinator flow
- `ParallelAgent` for signal interpretation, risk stratification, and intervention planning
- `LlmAgent` for each local specialist step
- `LoopAgent` for validation and refinement

Azure OpenAI remains supported through ADK's `LiteLlm` adapter, so the local runtime does not require a provider change.

---

## Environment variables you need

Create `services/agents/.env`:

```
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini     # deployment name used by the coordinator pipeline
OPENAI_API_VERSION=2025-01-01-preview    # or AZURE_OPENAI_API_VERSION
OPENAI_BASE_URL=                         # optional; use for OpenAI-compatible /openai/v1 endpoints
API_BASE_URL=http://localhost:8000       # gets set by Fab once backend is running
STUDENT_SPECIALIST_URL=http://localhost:8001   # Person 3's A2A server
CAREGIVER_SPECIALIST_URL=http://localhost:8002  # Person 3's A2A server
```

Get `API_BASE_URL` from Fab once the backend is running.

---

## Running locally without the backend

While Fab's backend is still being built, use stub tools:

In `services/tools/`, Person 3 will provide real tools. Until then, create `services/agents/dev_stubs.py`:

```python
# Stub responses for local agent development
def get_user_profile_stub():
    return {"persona_type": "student", "goal": "stress_reduction", "dietary_style": "none"}

def get_recent_signals_stub():
    return {"sleep_hours": 4.5, "stress_level": 8, "steps": 800, "mood": "negative"}
```

Point your agent imports at stubs during dev, swap for real tools at integration.

---

## Running the agent pipeline

```bash
cd services/agents
python -m coordinator.run --user-id test-user-1 --scenario stressed_student
```

Expected output:
- Logs showing ParallelAgent dispatching 3 agents concurrently
- A2A call to Student Support Specialist
- LoopAgent running 1–3 validation iterations
- Final intervention plan printed to stdout
- agent_messages written to DB (once API is live)

Remote specialists remain on the current HTTP boundary in this repo. The local workflow is now real ADK; the A2A migration remains a separate step.

---

## Key architecture rules

- **Agents never import SQLAlchemy.** All DB access goes through tool calls.
- **ParallelAgent** must wrap signal_interpretation, risk_stratification, intervention_planning — not implemented as sequential calls.
- **LoopAgent** must be a real ADK LoopAgent — not a Python `for` loop.
- **RemoteA2aAgent** must be used for specialist calls — not a direct function import.

See `docs/prompts.md` for each agent's system prompt.
See `docs/api-contracts.md` for the data shapes agents receive and return.

---

## Your branch workflow

```bash
git checkout main
git pull
git checkout -b feat/agents

# work...

git add services/agents/
git commit -m "your message"
git push origin feat/agents
```

Merge after Fab and Person 3 have merged. Your agents need real tools to run end-to-end.
