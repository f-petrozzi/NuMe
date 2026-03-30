# Setup — Backend (Fab)

You own: `apps/api/`, `infra/`, `packages/shared-types/`
Your branch: `feat/backend`

---

## What you're building

- FastAPI backend with all platform service endpoints
- PostgreSQL schema + Alembic migrations
- Garmin OAuth + background sync
- Recipe parsing (URL and paste)
- Docker Compose for the full stack
- Seed data

---

## Prerequisites

```bash
python 3.11+
postgresql (local or Docker)
pip install poetry  # or use pip directly
```

---

## Environment variables you need

Create `apps/api/.env` from `.env.example`:

```
DATABASE_URL=postgresql+asyncpg://nume:nume@localhost:5432/nume
CLERK_JWT_KEY=your-clerk-jwt-public-key
CLERK_FRONTEND_API_URL=https://your-instance.clerk.accounts.dev
CLERK_AUTHORIZED_PARTIES=http://localhost:8080
CLERK_SECRET_KEY=your-clerk-secret-key
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini   # deployment name used for recipe parsing + calorie estimates
GARMIN_USERNAME=your-garmin-email      # your personal Garmin credentials for bootstrap
GARMIN_PASSWORD=your-garmin-password
GARMIN_TOKEN_DIR=./garmin_tokens       # where OAuth tokens are cached per user
```

Variables others need from you (share with team once backend is running):
```
API_BASE_URL=http://localhost:8000     # Person 2 and 3 need this
```

---

## Running locally

```bash
# Start PostgreSQL
docker compose up db -d

# Install dependencies
cd apps/api
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Seed the database
python infra/seed/seed.py

# Start the API
uvicorn main:app --reload --port 8000
```

---

## Garmin bootstrap

Garmin requires an initial auth step before background sync works:

```bash
# Run once per user account to generate token cache
python scripts/garmin_bootstrap.py --user-id <user_id>
```

Tokens are cached in `GARMIN_TOKEN_DIR/<user_id>/`. After bootstrap, sync runs automatically on schedule and can be triggered manually via `POST /api/health/sync`.

---

## Verifying it works

```bash
# Health check
curl http://localhost:8000/health

# Protected routes now require a Clerk session token.
# Sign into the frontend with Clerk, then use that session against /api/auth/me and other protected endpoints.
```

---

## Your branch workflow

```bash
git checkout main
git pull
git checkout -b feat/backend

# work...

git add apps/api/ infra/ packages/shared-types/
git commit -m "your message"
git push origin feat/backend
```

Merge to `main` first — everyone else unblocks once your API is running.
