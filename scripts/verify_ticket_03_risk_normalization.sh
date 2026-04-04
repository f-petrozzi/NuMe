#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Ticket 3 verification: check-in normalization + deterministic risk subscores"
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

echo "==> Syntax check"
apps/api/.venv/bin/python -m py_compile \
  apps/api/risk_scoring.py \
  apps/api/routers/events.py \
  apps/api/schemas/events.py \
  services/agents/prompts.py \
  services/agents/schemas.py \
  services/agents/signal_interpretation/agent.py \
  services/agents/risk_stratification/agent.py \
  services/agents/coordinator/agent.py \
  services/tools/create_intervention_tool.py \
  apps/api/tests/test_pipeline.py \
  services/agents/tests/test_validation_loop.py \
  services/agents/tests/test_risk_normalization.py

echo "==> Optional migration check"
if [[ -n "${DATABASE_URL:-}" ]]; then
  (
    cd apps/api
    ../api/.venv/bin/alembic -c alembic.ini upgrade head
  )
  echo "migration check: ran alembic upgrade head"
else
  echo "migration check: skipped because DATABASE_URL is not set"
fi

echo "==> Targeted backend tests"
apps/api/.venv/bin/pytest \
  apps/api/tests/test_pipeline.py \
  services/agents/tests/test_validation_loop.py \
  services/agents/tests/test_risk_normalization.py \
  -q

echo "==> Coverage note"
echo "This verifies normalized check-in payloads, non-negative neutral/positive check-ins, deterministic risk subscores/drivers, and coordinator persistence."
echo "RemoteA2aAgent warnings are expected and not failures."

echo "==> Ticket 3 verification passed"
