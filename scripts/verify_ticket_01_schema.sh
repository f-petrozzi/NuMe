#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Ticket 1 verification: personalization snapshot schema + structured interventions"
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
  apps/api/models/personalization.py \
  apps/api/models/agents.py \
  apps/api/models/__init__.py \
  apps/api/routers/interventions.py \
  apps/api/schemas/agents.py \
  apps/api/alembic/versions/007_personalization_state_snapshots_and_structured_interventions.py

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
apps/api/.venv/bin/pytest apps/api/tests/test_pipeline.py -q
apps/api/.venv/bin/pytest apps/api/tests/test_internal_auth.py -q

echo "==> Coverage note"
echo "This verifies Ticket 1 schema/model/router compatibility and targeted API behavior."
echo "It does not run a live end-to-end HTTP smoke flow because Ticket 1 is an additive schema step."

echo "==> Ticket 1 verification passed"
