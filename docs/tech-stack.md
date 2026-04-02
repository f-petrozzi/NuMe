# Tech Stack — NüMe

All choices are optimized for hackathon velocity: well-documented, AI-friendly, and parallelizable across 4 Codex instances.

---

## Frontend

| Layer | Choice | Notes |
|---|---|---|
| Framework | Vite + React 18 (SPA) | React Router for client-side routing; no SSR |
| Language | TypeScript | Strong typing for agent message shapes |
| Styling | Tailwind CSS | Fast, no design system setup needed |
| Components | shadcn/ui | Pre-built accessible components, copy-paste friendly |
| Auth (client) | @clerk/clerk-react | Clerk React SDK; backend receives Clerk session token |
| State | React Query (TanStack Query) | Polling for run status on scenario runner |
| Charts | Recharts | Signal trend display on member dashboard |

---

## Backend

| Layer | Choice | Notes |
|---|---|---|
| Framework | FastAPI (Python 3.11+) | Async, Pydantic-native, fast to write |
| ORM | SQLAlchemy 2.0 (async) | Works with both SQLite and PostgreSQL |
| Schema validation | Pydantic v2 | Shared with ADK agent I/O schemas |
| Migrations | Alembic | Simple one-command migrations |
| Auth | Clerk + PyJWT verification | Clerk-hosted sign-in with backend session token verification |
| Database | PostgreSQL (default) / SQLite (local fallback) | PostgreSQL preferred; SQLite acceptable for demo day |

---

## Agent Framework

| Layer | Choice | Notes |
|---|---|---|
| Agent SDK | Google ADK for Python | Required for Google challenge alignment |
| LLM | Azure OpenAI `gpt-4.1-mini` | Routed through ADK `LiteLlm`, preserving the current provider |
| Local agents | Real ADK `SequentialAgent`, `ParallelAgent`, `LoopAgent`, `LlmAgent` | Custom code is limited to state seeding, fallback parsing, trace persistence, and specialist/tool glue |
| Remote specialists | HTTP POST to specialist FastAPI services (`/invoke`) | Student Support + Caregiver Burnout run as separate FastAPI services; `adk api_server --a2a` target when real ADK is wired |
| A2A client | `RemoteA2aAgent` interface + `httpx` boundary | Coordinator keeps the current specialist boundary for now; full A2A migration is deferred |
| Tool pattern | ADK `FunctionTool` wrapping FastAPI service calls | Agents never touch the DB directly |

---

## Infrastructure

| Layer | Choice | Notes |
|---|---|---|
| Local dev | Docker Compose | One `docker compose up` starts everything |
| Services in Compose | `api` (FastAPI), `web` (Vite/React), `db` (PostgreSQL), `specialist-student` (A2A server), `specialist-caregiver` (A2A server) | |
| Environment | Doppler or `.env` with Clerk, Azure OpenAI/OpenAI-compatible endpoint settings, and DB settings | |
| Cloud target | Cloudflare Pages + Cloudflare Containers + Supabase | FastAPI stays in a container; Clerk remains the auth provider |

---

## Observability

| Layer | Choice | Notes |
|---|---|---|
| Logging | `structlog` (Python) | JSON-formatted structured logs |
| Agent tracing | `agent_runs` + `agent_messages` tables | Custom trace persistence in PostgreSQL |
| Trace UI | Custom Next.js trace dashboard | Shows parallel branches, loop iterations, A2A calls |

---

## Not in this stack (and why)

| What | Why not |
|---|---|
| Redis / Celery | Agent runs are synchronous for MVP; no background queue needed |
| LangChain / LangGraph | ADK is the framework; mixing orchestration layers creates confusion |
| Pinecone / pgvector | No semantic search in MVP; plain SQL is sufficient |
| Next.js | App is a Vite/React SPA; Next.js was planned but never adopted |
| NextAuth / Auth0 | Clerk is already the chosen auth provider for the product |
| Prisma | SQLAlchemy is already in Python backend; no need for a second ORM |
| Workers rewrite (now) | Current FastAPI + SQLAlchemy + asyncpg runtime is a better fit for Cloudflare Containers than an immediate Workers rewrite |
