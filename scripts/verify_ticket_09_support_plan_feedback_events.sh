#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Ticket 9 verification: support-plan feedback events"
echo "repo: $REPO_ROOT"

if [[ ! -x "apps/api/.venv/bin/python" ]]; then
  echo "missing API venv at apps/api/.venv" >&2
  exit 1
fi

if [[ ! -d "apps/web/node_modules" ]]; then
  echo "missing frontend dependencies in apps/web/node_modules" >&2
  echo "run: npm ci --prefix apps/web" >&2
  exit 1
fi

export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/nume-pyc}"

echo "==> Environment"
echo "python: $(apps/api/.venv/bin/python --version 2>&1)"
echo "node: $(node --version 2>&1)"
echo "npm: $(npm --version 2>&1)"
echo "pytest autoload disabled: $PYTEST_DISABLE_PLUGIN_AUTOLOAD"
echo "pycache prefix: $PYTHONPYCACHEPREFIX"

echo "==> Backend syntax check"
apps/api/.venv/bin/python -m py_compile \
  apps/api/main.py \
  apps/api/models/personalization.py \
  apps/api/routers/support_plan.py \
  apps/api/schemas/agents.py \
  apps/api/alembic/versions/010_support_plan_feedback_events.py \
  apps/api/tests/test_support_plan.py

echo "==> Targeted backend tests"
apps/api/.venv/bin/pytest \
  apps/api/tests/test_support_plan.py \
  -q

echo "==> Frontend typecheck"
npm --prefix apps/web run typecheck

echo "==> Targeted frontend tests"
npm --prefix apps/web run test -- src/lib/api.test.ts src/test/support-plan.test.tsx

echo "==> Coverage note"
echo "This verifies support-plan feedback events persist through POST /api/support-plan/feedback,"
echo "the dashboard logs intervention-scoped acceptance and skip actions, and recommended"
echo "recipe clicks on the recipe page are tied back to the current support-plan intervention."

echo "==> Ticket 9 verification passed"
