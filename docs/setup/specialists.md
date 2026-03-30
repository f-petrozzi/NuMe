# Setup — A2A Specialists and Tool Layer (Person 3)

You own: `services/remote_specialists/`, `services/tools/`
Your branch: `feat/specialists`

---

## What you're building

Two things:

**1. ADK tool layer** — Python functions that wrap FastAPI HTTP calls, exposed as ADK `FunctionTool` objects. These are what the local agents use to read/write data. You own this layer; agents import from it.

**2. Remote A2A specialists** — Two LlmAgents exposed as standalone A2A servers. The Care Coordinator calls these over the A2A protocol based on the user's persona type.

You are NOT building local orchestration agents — that's Person 2.
You are NOT building FastAPI routes — that's Fab.
You are NOT building frontend — that's Person 4.

---

## Prerequisites

```bash
python 3.11+
pip install google-adk httpx
```

---

## Environment variables you need

Create `services/tools/.env` and `services/remote_specialists/.env`:

```
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini     # deployment name used by the specialist services
API_BASE_URL=http://localhost:8000       # Fab's backend — needed for all tools
```

Get `API_BASE_URL` from Fab once the backend is running.

---

## Running tools without the backend

Tools make HTTP calls to `API_BASE_URL`. While Fab's backend is building, you can:

```bash
# Option 1: run a simple JSON mock server
npx json-server --watch docs/api-contracts.json --port 8000

# Option 2: return hardcoded responses in tool functions during dev
# wrap in try/except and return fixture data if connection fails
```

---

## Running the A2A specialist servers

```bash
# Student Support Specialist — runs on port 8001
cd services/remote_specialists/student_support
adk api_server --a2a --port 8001

# Caregiver Burnout Specialist — runs on port 8002
cd services/remote_specialists/caregiver_burnout
adk api_server --a2a --port 8002
```

Each specialist needs an `agent_card.json` in its directory. The agent card tells the Care Coordinator what this specialist does and how to call it.

---

## Tool requirements

Each tool in `services/tools/` must:
- Accept typed parameters matching the shapes in `docs/api-contracts.md`
- Call the corresponding FastAPI endpoint via `httpx`
- Retry once on connection error, then raise
- Be wrapped as `FunctionTool(your_function)`

Example structure:
```python
# services/tools/create_case_tool.py
import httpx
from google.adk.tools import FunctionTool

def create_case(user_id: str, risk_level: str, run_id: str) -> dict:
    response = httpx.post(f"{API_BASE_URL}/api/cases", json={...})
    response.raise_for_status()
    return response.json()

create_case_tool = FunctionTool(create_case)
```

---

## Specialist system prompts

See `docs/prompts.md` → "Student Support Specialist" and "Caregiver Burnout Specialist" for the exact system prompts to use.

---

## Your branch workflow

```bash
git checkout main
git pull
git checkout -b feat/specialists

# work...

git add services/remote_specialists/ services/tools/
git commit -m "your message"
git push origin feat/specialists
```

Merge after Fab merges the backend. Your tools need a real API to call.
Person 2 (agents) merges after you — they need your tools.
