#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Ticket 6 verification: activity and wellness catalogs + planner rewrite"
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
  apps/api/models/personalization.py \
  apps/api/catalog_ranking.py \
  apps/api/routers/interventions.py \
  apps/api/alembic/versions/009_activity_wellness_catalogs.py \
  services/agents/intervention_planning/agent.py \
  services/agents/coordinator/agent.py \
  services/agents/schemas.py \
  apps/api/tests/test_catalog_ranking.py \
  apps/api/tests/test_pipeline.py \
  services/agents/tests/test_intervention_planning.py \
  services/agents/tests/test_validation_loop.py

echo "==> Targeted backend and agent tests"
apps/api/.venv/bin/pytest \
  apps/api/tests/test_catalog_ranking.py \
  apps/api/tests/test_pipeline.py \
  services/agents/tests/test_intervention_planning.py \
  services/agents/tests/test_validation_loop.py \
  -q

echo "==> Coverage note"
echo "This verifies seeded activity and wellness catalogs, deterministic ranking for both,"
echo "planner retrieve-rank-compose output with why_chosen and alternatives_considered,"
echo "and coordinator/API persistence of selected activity_template_id and wellness_template_id."

echo "==> Ticket 6 verification passed"
