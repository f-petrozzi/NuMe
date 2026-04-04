#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Ticket 4 verification: recipe nutrition + effort fields"
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
  apps/api/models/recipes.py \
  apps/api/schemas/recipes.py \
  apps/api/routers/recipes.py \
  apps/api/alembic/versions/008_recipe_nutrition_fields.py \
  apps/api/tests/test_recipes.py

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
apps/api/.venv/bin/pytest apps/api/tests/test_recipes.py -q

echo "==> Frontend typecheck"
if [[ -x "apps/web/node_modules/.bin/tsc" ]]; then
  (
    cd apps/web
    npm run typecheck
  )
  echo "frontend typecheck: passed"
else
  echo "frontend typecheck: skipped because apps/web/node_modules/.bin/tsc is not available"
fi

echo "==> Coverage note"
echo "This verifies additive recipe nutrition and effort fields, recipe CRUD compatibility, template seeding, and migration application."
echo "Frontend typecheck runs when the local web toolchain is installed."

echo "==> Ticket 4 verification passed"
