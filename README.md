# NüMe

> Become the new you, with NüMe.

NüMe is a personalized wellness platform that turns sleep, stress, activity, and check-ins into guidance you can actually use.

Product:
- Frontend: [nume-demo.com](https://nume-demo.com)
- API health: [api.nume-demo.com/health](https://api.nume-demo.com/health)

## What the Demo Shows

- A member-facing dashboard that adapts recommendations around sleep, stress, movement, and self-reported check-ins
- Support flows that adapt based on what is most likely to help each member next
- A traceable multi-agent backend that produces explainable support plans instead of opaque single-shot outputs
- An end-to-end deployment path: Cloudflare Pages frontend, FastAPI API, PostgreSQL, Docker Compose, Doppler secrets, and Cloudflare Tunnel
- A documented migration path toward Cloudflare Containers + Supabase while preserving Clerk and FastAPI

## Why It Is Useful For Hiring Managers

- Product thinking: the repo is not just a model demo, it is a user-facing workflow from onboarding through daily recommendations
- Full-stack ownership: frontend, backend, auth, persistence, deployment, and production routing all live in one system
- AI systems design: the orchestration layer separates coordination, specialist routing, validation, and traceability
- Practical deployment: this project is live on a real domain with a split frontend/API architecture instead of staying local-only

## Architecture

Current live deployment:

```text
Cloudflare Pages (React/Vite frontend)
        |
        v
  api.nume-demo.com
        |
Cloudflare Tunnel
        |
        v
FastAPI API -> PostgreSQL
        |
        +-> coordinator agent
        +-> student specialist
        +-> caregiver specialist
        +-> tools / shared models
```

Recommended target deployment:

```text
Cloudflare Pages (React/Vite frontend)
        |
        v
Cloudflare Worker / API route
        |
        v
Cloudflare Container (FastAPI API)
        |
        +-> Supabase Postgres
        +-> coordinator agent
        +-> specialist services
```

Core code layout:

- `apps/web` - React + Vite frontend
- `apps/api` - FastAPI backend
- `services/remote_specialists` - specialist agent services
- `services/tools` - API-facing tool layer
- `packages/shared-types` - shared Pydantic models
- `infra/seed` - demo data seeding

## Stack

- Frontend: React, TypeScript, Vite, Clerk
- Backend: FastAPI, SQLAlchemy, PostgreSQL
- AI layer: Google ADK-style multi-agent orchestration and specialist routing
- Infra: Docker Compose, Doppler, Cloudflare Pages, Cloudflare Tunnel

## Run Locally

Prereqs: Docker, Python 3.11+, Node 18+, Doppler CLI

```bash
git clone https://github.com/f-petrozzi/NuMe.git
cd NuMe
doppler setup
doppler run -- docker compose up -d db
doppler run -- docker compose run --rm api alembic upgrade head
doppler run -- docker compose up -d api web specialist-student specialist-caregiver
doppler run -- docker compose exec -T api python /workspace/infra/seed/seed.py
```

Local endpoints:

- Frontend: `http://localhost:8080`
- API docs: `http://localhost:8000/docs`

Notes:

- Secrets are managed through Doppler
- On a fresh database, run Alembic before starting the API
- The seed script provisions demo users and sample health data

## Deployment

Production is split intentionally:

- `nume-demo.com` serves the frontend from Cloudflare Pages
- `api.nume-demo.com` routes to the API through Cloudflare Tunnel

This repo no longer uses a NüMe-local `cloudflared` config. Tunnel routing is managed in the shared infrastructure stack.

The recommended next-step architecture is documented in [`docs/deployment/cloudflare-supabase.md`](/mnt/ssd/homelab/NüMe/docs/deployment/cloudflare-supabase.md).

## Selected Docs

- `docs/api-contracts.md` - request/response shapes
- `docs/architecture.md` - system design notes
- `docs/deployment/cloudflare-supabase.md` - staged Cloudflare + Supabase rollout plan
- `docs/tech-stack.md` - implementation choices
- `docs/setup/backend.md` - backend setup details
- `docs/setup/frontend.md` - frontend setup details
- `docs/setup/agents.md` - agent setup details
- `docs/prompts.md` - prompt/system behavior references
