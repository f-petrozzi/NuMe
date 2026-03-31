# NüMe Frontend

This folder is the active NüMe experience-layer implementation.

Run it from `apps/web/`.

## Auth

Clerk is the only supported authentication flow in the app. `VITE_CLERK_PUBLISHABLE_KEY` is required to run the frontend.

## Environment

Use Doppler in normal development:

```bash
cd apps/web
doppler run -- npm run dev
```

If you need a local file, copy `.env.example` to `.env.local` and set:

```bash
VITE_API_URL=http://localhost:8000
VITE_USE_MOCK_API=false
VITE_CLERK_PUBLISHABLE_KEY=pk_test_your_clerk_publishable_key
```

For Cloudflare Pages production:

```bash
VITE_API_URL=https://api.nume-demo.com
VITE_USE_MOCK_API=false
VITE_CLERK_PUBLISHABLE_KEY=<your Clerk publishable key>
```

This app uses `BrowserRouter`, so the checked-in [`_redirects`](/mnt/ssd/homelab/NüMe/apps/web/public/_redirects)
file is required for direct route loads on Cloudflare Pages.

## Current integration state

- Clerk is wired into the frontend shell, route guards, and onboarding state.
- Onboarding state is stored in Clerk user `unsafeMetadata`.
- Set `VITE_USE_MOCK_API=true` only when you intentionally want mock API data without exercising backend auth.
- The FastAPI backend now accepts Clerk session tokens and no longer exposes password login/register routes.
- First-time Clerk users are synced into the local `users` table automatically.
- For first-time user provisioning, either set `CLERK_SECRET_KEY` on the backend or add an email or username claim to the Clerk session token.
- Username-only Clerk sign-up is supported as long as the Clerk instance enables usernames and makes email optional.
- To preserve seeded roles such as admin, sign into Clerk with the same email as the existing seeded user row.

## Backend secrets

The frontend publishable key is not enough for full live mode. The backend should also receive:

```bash
CLERK_JWT_KEY=
CLERK_FRONTEND_API_URL=
CLERK_AUTHORIZED_PARTIES=https://nume-demo.com,https://www.nume-demo.com
CLERK_SECRET_KEY=
```

`CLERK_SECRET_KEY` is used only when the backend needs to fetch a Clerk user's email during first-time provisioning.

## Commands

```bash
cd apps/web
npm install
npm run dev
npm run typecheck
npm run test
npm run build
```

## Integration rule

Keep backend DTOs in `src/lib/api-contracts.ts`, UI models in `src/lib/types.ts`, and translation logic in `src/lib/api-mappers.ts`.
