# NüMe

A multi-agent health coordination platform that turns wearable signals and behavioral patterns into adaptive, empathetic, actionable support — built on Google ADK.

---

## What it does

NüMe monitors your health signals (sleep, stress, steps, mood) and runs a team of AI agents in parallel to produce a personalized support plan. Based on your persona — stressed student, exhausted caregiver, older adult — it routes to the right specialist, validates the plan, and delivers empathy-first recommendations with a full traceable audit trail.

---

## Repo structure

```
apps/
  api/              ← FastAPI backend
  web/              ← Vite + React frontend
services/
  agents/           ← Google ADK local agent pipeline
  tools/            ← ADK tool layer — HTTP wrappers for the API
  remote_specialists/ ← A2A specialist servers
packages/
  shared-types/     ← Pydantic v2 models shared across all services
infra/
  seed/             ← Database seed script
scripts/
  garmin_bootstrap.py ← One-time Garmin OAuth setup
docs/
  api-contracts.md  ← All endpoint shapes
  setup/            ← Setup guides
    backend.md
    agents.md
    specialists.md
    frontend.md
```

---

## Secrets setup (Doppler — required before running anything)

Secrets are managed via [Doppler](https://doppler.com) — no `.env` files, no keys in the repo.

### Install Doppler CLI

**macOS:**
```bash
brew install dopplerhq/cli/doppler
```

**Ubuntu/Debian:**
```bash
curl -Ls --tlsv1.2 --proto "=https" --retry 3 https://cli.doppler.com/install.sh | sudo sh
```

### Authenticate and link project

```bash
doppler login
doppler setup   # links to the `nume` project (doppler.yaml auto-fills this)
```

### Verify

```bash
doppler secrets
# Should list all environment variables without showing values
```

After this, prefix every command with `doppler run --`:

```bash
doppler run -- uvicorn main:app --reload --port 8000
doppler run -- alembic upgrade head
doppler run -- python ../../infra/seed/seed.py
```

---

## Quick start (local)

**Prerequisites:** Docker, Python 3.11+, Node 18+, Doppler CLI

```bash
# 1. Clone the repo
git clone https://github.com/<your-username>/NuMe.git
cd NuMe

# 2. Set up Doppler (see above)
doppler setup

# 3. Start PostgreSQL
docker compose up db -d

# 4. Start the API
cd apps/api
pip install -r requirements.txt
doppler run -- alembic upgrade head
doppler run -- python ../../infra/seed/seed.py
doppler run -- uvicorn main:app --reload --port 8000

# 5. Verify
curl http://localhost:8000/health
# → {"status": "ok", "service": "nume-api"}
```

API docs: `http://localhost:8000/docs`

**Seeded demo accounts (linked by email when signing in with Clerk):**
| Email | Role |
|---|---|
| student@nume.demo | member |
| caregiver@nume.demo | member |
| admin@nume.demo | admin |

---

## Full stack (Docker Compose)

```bash
doppler run -- docker compose up
```

Starts: PostgreSQL, API (8000), specialist-student (8001), specialist-caregiver (8002), web (8080).

---

## Deployment (homelab + Cloudflare Tunnel)

The backend runs on the homelab via Docker Compose and is exposed publicly through the shared
homelab `cloudflared` service at the repo root.

Recommended public split:

- Frontend: Cloudflare Pages on `nume-demo.com`
- API: Cloudflare Tunnel on `api.nume-demo.com`

This repo no longer keeps a NüMe-local tunnel config. Manage the public hostname route from the
parent homelab Cloudflare Tunnel instead.

---

## Agent architecture

```
POST /api/runs/trigger
  ↓
coordinator (SequentialAgent)
  ├── ParallelAgent
  │   ├── SignalInterpretationAgent
  │   ├── RiskStratificationAgent
  │   └── InterventionPlanningAgent
  ├── EmpathyCheckinAgent
  ├── ValidationLoopAgent (LoopAgent)
  └── RemoteA2aAgent → StudentSupportSpecialist (8001)
                     → CaregiverBurnoutSpecialist (8002)
  ↓
services/tools/ → HTTP calls to API → PostgreSQL
```

---

## Key docs

| Doc | Purpose |
|---|---|
| `docs/api-contracts.md` | All endpoint shapes and request/response bodies |
| `docs/prompts.md` | System prompts for each agent |
| `docs/technical-requirements.md` | Full feature requirements and DB schema |
| `docs/setup/backend.md` | Backend setup |
| `docs/setup/agents.md` | ADK agent setup |
| `docs/setup/specialists.md` | A2A specialist setup |
| `docs/setup/frontend.md` | Frontend setup |
| `packages/shared-types/models.py` | Pydantic models for agent I/O |

---

## Environment variables

All secrets managed via Doppler (`nume` project). See `.env.example` for the full variable list.
