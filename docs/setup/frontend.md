# Setup — Frontend

Current frontend location: `apps/web/`

The active app is the Vite + React frontend under `apps/web/`.

---

## What is wired now

- Vite + React + TypeScript
- React Router
- Tailwind + shadcn/ui
- React Query data layer
- Clerk-only authentication
- Mock API mode and live API mode

---

## Secrets and env

Use Doppler in normal development so secrets are injected at runtime:

```bash
cd apps/web
doppler run -- npm run dev
```

Required frontend secret:

```bash
VITE_CLERK_PUBLISHABLE_KEY=<your Clerk publishable key>
```

Optional frontend vars:

```bash
VITE_API_URL=http://localhost:8000
VITE_USE_MOCK_API=false
```

If you need local env files temporarily, copy `apps/web/.env.example` to `apps/web/.env.local`.

---

## Running locally

```bash
cd apps/web
npm install
doppler run -- npm run dev
```

The Vite dev server runs on `http://localhost:8080`.

---

## Auth behavior

- `VITE_CLERK_PUBLISHABLE_KEY` is required. Without it, the app shows a configuration error instead of a local login form.
- Login and registration use Clerk components only.
- Onboarding completion is written into Clerk `unsafeMetadata`.
- The frontend does not support password-based local auth anymore.

Live API mode with Clerk now requires matching backend secrets:

```bash
CLERK_JWT_KEY=
CLERK_FRONTEND_API_URL=
CLERK_AUTHORIZED_PARTIES=http://localhost:8080
CLERK_SECRET_KEY=
```

Notes:

- `CLERK_SECRET_KEY` is needed for first-time local user provisioning unless your Clerk session token includes an email claim.
- Set `VITE_USE_MOCK_API=true` only when you explicitly want mock API data without exercising backend auth.

---

## Frontend architecture rules

- `src/lib/api.ts`
  Single API boundary. No page should call `fetch` or `axios` directly.
- `src/lib/api-contracts.ts`
  Backend DTOs.
- `src/lib/types.ts`
  UI view models.
- `src/lib/api-mappers.ts`
  Translation between DTOs and UI models.
- `src/contexts/AuthContext.tsx`
  Clerk session sync and frontend auth state.

---

## Validation

Use these before handing off frontend auth or route changes:

```bash
npm run typecheck
npm run test
npm run build
```
