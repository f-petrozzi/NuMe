#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Ticket 8 verification: frontend support-plan cutover"
echo "repo: $REPO_ROOT"

if [[ ! -d "apps/web/node_modules" ]]; then
  echo "missing frontend dependencies in apps/web/node_modules" >&2
  echo "run: npm ci --prefix apps/web" >&2
  exit 1
fi

echo "==> Environment"
echo "node: $(node --version 2>&1)"
echo "npm: $(npm --version 2>&1)"

echo "==> Frontend typecheck"
npm --prefix apps/web run typecheck

echo "==> Targeted frontend tests"
npm --prefix apps/web run test -- src/lib/api.test.ts src/test/support-plan.test.tsx

echo "==> Coverage note"
echo "This verifies the frontend uses GET /api/support-plan/current, renders structured"
echo "risk drivers and linked recipe details on the dashboard, and reads structured"
echo "meal recommendation context on the recipe page."

echo "==> Ticket 8 verification passed"
