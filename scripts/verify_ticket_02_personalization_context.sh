#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Ticket 2 verification: personalization context builder + coordinator integration"
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
  apps/api/personalization.py \
  apps/api/routers/personalization.py \
  apps/api/schemas/personalization.py \
  services/tools/get_personalization_context_tool.py \
  services/agents/tooling.py \
  services/agents/coordinator/agent.py

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
apps/api/.venv/bin/pytest apps/api/tests/test_personalization.py apps/api/tests/test_internal_auth.py apps/api/tests/test_pipeline.py -q

echo "==> Coordinator regression tests"
apps/api/.venv/bin/pytest services/agents/tests/test_validation_loop.py -q

echo "==> Coverage note"
echo "This verifies the shared personalization context route, internal-tool auth path, snapshot persistence, and coordinator integration."
echo "It does not run a full live HTTP smoke flow yet because Ticket 3 still changes the risk/check-in normalization path."

echo "==> Ticket 2 verification passed"
