#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Ticket 7 verification: support-plan endpoint and compatibility"
echo "repo: $REPO_ROOT"

if [[ ! -x "apps/api/.venv/bin/python" ]]; then
  echo "missing API venv at apps/api/.venv" >&2
  exit 1
fi

export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export PYTHONPYCACHEPREFIX="${PYTHONPYCACHEPREFIX:-/tmp/nume-pyc}"

echo "==> Environment"
echo "python: $(apps/api/.venv/bin/python --version 2>&1)"
echo "pytest autoload disabled: $PYTEST_DISABLE_PLUGIN_AUTOLOAD"
echo "pycache prefix: $PYTHONPYCACHEPREFIX"

echo "==> Backend syntax check"
apps/api/.venv/bin/python -m py_compile \
  apps/api/main.py \
  apps/api/support_plan.py \
  apps/api/routers/support_plan.py \
  apps/api/routers/runs.py \
  apps/api/routers/interventions.py \
  apps/api/schemas/agents.py \
  apps/api/tests/test_pipeline.py \
  apps/api/tests/test_support_plan.py

echo "==> Targeted backend tests"
apps/api/.venv/bin/pytest \
  apps/api/tests/test_pipeline.py \
  apps/api/tests/test_support_plan.py \
  -q

echo "==> Coverage note"
echo "This verifies GET /api/support-plan/current returns one structured support-plan payload,"
echo "preserves linked recipe and catalog details plus change reasons, and leaves"
echo "the legacy intervention and run-trace routes working during the transition."

echo "==> Ticket 7 verification passed"
