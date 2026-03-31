# Cloudflare + Supabase Rollout

This is the recommended next-step architecture for NüMe as of 2026-03-30.

## Recommendation

Keep the current backend in FastAPI for now.

Deploy the stack as:

```text
Cloudflare Pages (apps/web)
        |
        v
Cloudflare Worker / API route
        |
        v
Cloudflare Container (apps/api)
        |
        +-> Supabase Postgres
        +-> existing Python coordinator + specialists
```

Keep Clerk as the auth provider.

Do not rewrite the backend to Workers yet. The current app depends on FastAPI, SQLAlchemy, `asyncpg`, thread-based execution, APScheduler, and a full Python container runtime. Cloudflare Containers are the practical Cloudflare-native path for this codebase.

## What Changed In The Repo

- FastAPI no longer auto-creates tables on startup.
- Alembic now supports a dedicated `DATABASE_MIGRATION_URL`.
- Runtime DB config is Supabase-aware:
  - pooled runtime connections for persistent containers
  - transaction-pool compatibility when needed later
  - explicit pool sizing and timeouts
- CORS is now explicit via `CORS_ALLOWED_ORIGINS`.
- `/readyz` now verifies database connectivity for container health checks.

## Connection Strategy

Use separate connection strings for runtime and migrations.

- `DATABASE_URL`
  Runtime connection string used by FastAPI.
- `DATABASE_MIGRATION_URL`
  Connection string used by Alembic.

Recommended Supabase mapping:

- API runtime on Cloudflare Containers:
  use a direct Postgres connection or the Supabase session pooler.
- Alembic migrations:
  use a direct connection or the session pooler only.
- Future serverless or highly bursty edge jobs:
  use the Supabase transaction pooler and set `DATABASE_POOL_MODE=transaction`.

Notes:

- Supabase transaction pooling does not support prepared statements.
- The app handles that by disabling asyncpg statement caching when it detects `:6543` or when `DATABASE_POOL_MODE=transaction`.

## Required Environment Variables

API runtime:

```bash
APP_ENV=production
DATABASE_URL=
DATABASE_MIGRATION_URL=
DATABASE_POOL_MODE=auto
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT_SECONDS=30
DATABASE_POOL_RECYCLE_SECONDS=1800
DATABASE_STATEMENT_CACHE_SIZE=100
DATABASE_COMMAND_TIMEOUT_SECONDS=60
CORS_ALLOWED_ORIGINS=https://nume-demo.com,https://www.nume-demo.com
API_BASE_URL=https://api.nume-demo.com
CLERK_JWT_KEY=
CLERK_FRONTEND_API_URL=
CLERK_JWKS_URL=
CLERK_AUTHORIZED_PARTIES=https://nume-demo.com,https://www.nume-demo.com
CLERK_SECRET_KEY=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_ENDPOINT=
OPENAI_API_VERSION=
AZURE_OPENAI_DEPLOYMENT=
STUDENT_SPECIALIST_URL=
CAREGIVER_SPECIALIST_URL=
```

Pages frontend:

```bash
VITE_API_URL=https://api.nume-demo.com
VITE_USE_MOCK_API=false
VITE_CLERK_PUBLISHABLE_KEY=
```

## Migration Policy

Use Alembic only.

Do not rely on app startup to create schema.

Production rule:

1. Apply migrations.
2. Deploy the API revision that expects that schema.
3. Shift traffic.

Recommended CI/CD migration command:

```bash
cd apps/api
alembic upgrade head
```

## Manual Rollout Steps

### 1. Move The Database To Supabase

1. Create a Supabase project.
2. Copy the direct or session-pooled Postgres URL for `DATABASE_MIGRATION_URL`.
3. Copy the runtime URL for `DATABASE_URL`.
4. Run:

```bash
cd apps/api
alembic upgrade head
python ../../infra/seed/seed.py
```

5. Point a non-production API instance at Supabase first.

### 2. Keep Clerk, Tighten Production Inputs

1. Keep the existing Clerk instance.
2. Add production frontend origins and redirect URLs for:
   - `https://nume-demo.com`
   - `https://www.nume-demo.com`
3. Set backend verification inputs:
   - `CLERK_FRONTEND_API_URL`
   - `CLERK_JWT_KEY` or `CLERK_JWKS_URL`
   - `CLERK_AUTHORIZED_PARTIES`
4. Keep `CLERK_SECRET_KEY` available for first-time user provisioning if the session token does not include email or username claims.

### 3. Move The API Off Tunnel

Recommended path:

1. Keep the current API deployment running while Supabase is validated.
2. Provision the Cloudflare Container deployment for `apps/api`.
3. Front it with a Cloudflare Worker/API route and the final API hostname.
4. Set the container env vars listed above.
5. Use `/health` for liveness and `/readyz` for readiness.
6. Cut DNS or route traffic from the Tunnel-backed API to the new endpoint.
7. Remove the old Tunnel path only after soak.

If Cloudflare Containers risk is unacceptable for the first cut, keep the API on its current host and still complete the Supabase migration first. The runtime changes in this repo support that intermediate step cleanly.

### 4. Keep CI/CD Responsibilities Clear

Run in CI or deploy automation:

- `alembic upgrade head`
- image build
- deploy new API revision

Run locally:

- `docker compose up db -d`
- `docker compose run --rm api alembic upgrade head`
- `docker compose up api web specialist-student specialist-caregiver`
- `docker compose exec -T api python /workspace/infra/seed/seed.py`

Run inside Cloudflare runtime:

- FastAPI app only
- no schema bootstrap

## Rollout Order

1. Land the runtime and config changes in this repo.
2. Create Supabase and apply migrations.
3. Validate FastAPI against Supabase in a non-production environment.
4. Confirm Clerk auth and onboarding against Supabase-backed data.
5. Provision the Cloudflare Container route.
6. Switch traffic.
7. Remove the old Tunnel path.

## Risks

- Cloudflare Containers are still a staged product surface, so preserve rollback.
- In-process background tasks are acceptable for current scope but are not a durable job system.
- Supabase transaction pooling is not a drop-in replacement for persistent SQLAlchemy app servers unless the client is configured correctly.
- Demo access is currently controlled by hardcoded allowlists and should be externalized later.
