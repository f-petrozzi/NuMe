#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Ticket 5 verification: deterministic recipe ranking"
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
  apps/api/recipe_ranking.py \
  apps/api/routers/recipes.py \
  services/agents/intervention_planning/agent.py \
  services/agents/coordinator/agent.py \
  apps/api/tests/test_recipes.py \
  services/agents/tests/test_intervention_planning.py

echo "==> Targeted backend and agent tests"
apps/api/.venv/bin/pytest \
  apps/api/tests/test_recipes.py \
  services/agents/tests/test_intervention_planning.py \
  -q

echo "==> Coverage note"
echo "This verifies deterministic recipe ranking, snapshot-aware recommendation ordering,"
echo "allergy and low-prep fit, and intervention planner meal constraints derived from"
echo "snapshot context rather than raw signals alone."

echo "==> Ticket 5 verification passed"
