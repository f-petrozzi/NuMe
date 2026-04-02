#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

API_URL="${API_URL:-http://127.0.0.1:8000}"
INTERNAL_API_TOKEN="${INTERNAL_API_TOKEN:-dev-internal-token}"
SMOKE_USER_EMAIL="${SMOKE_USER_EMAIL:-local-smoke@example.com}"
INSTALL_DEPS="${INSTALL_DEPS:-0}"
RESTART_STACK="${RESTART_STACK:-0}"
BUILD_IMAGES="${BUILD_IMAGES:-0}"
export API_URL INTERNAL_API_TOKEN

wait_for_url() {
  local url="$1"
  local label="$2"
  local attempts="${3:-60}"
  local delay="${4:-2}"

  for ((i = 1; i <= attempts; i++)); do
    if curl -fsS "$url" >/dev/null; then
      echo "ready: $label"
      return 0
    fi
    sleep "$delay"
  done

  echo "timed out waiting for $label at $url" >&2
  return 1
}

wait_for_specialist_health() {
  local service_url="$1"
  local label="$2"

  docker compose exec -T api python - "$service_url" "$label" <<'PY'
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

url = sys.argv[1]
label = sys.argv[2]

for _ in range(60):
    try:
        with urlopen(url, timeout=5) as response:
            print(f"ready: {label} -> {response.read().decode()}")
            raise SystemExit(0)
    except URLError:
        time.sleep(2)

raise SystemExit(f"timed out waiting for {label} at {url}")
PY
}

echo "==> Activate existing API venv"
source apps/api/.venv/bin/activate

if [[ "$INSTALL_DEPS" == "1" ]]; then
  echo "==> Install/update API deps"
  pip install -r apps/api/requirements.txt
else
  echo "==> Skip API dependency install (set INSTALL_DEPS=1 to enable)"
fi

echo "==> Test env"
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

echo "==> Ensure compose network exists"
docker network inspect homelab_network >/dev/null 2>&1 || docker network create homelab_network

if [[ "$RESTART_STACK" == "1" ]]; then
  echo "==> Restart stack"
  docker compose down
  if [[ "$BUILD_IMAGES" == "1" ]]; then
    docker compose up -d --build db api specialist-student specialist-caregiver
  else
    docker compose up -d db api specialist-student specialist-caregiver
  fi
else
  echo "==> Skip docker restart (set RESTART_STACK=1 to enable)"
fi

echo "==> Wait for API"
wait_for_url "$API_URL/health" "api health"
wait_for_url "$API_URL/readyz" "api readiness"

echo "==> Apply migrations"
docker compose exec -T api alembic upgrade head

echo "==> Verify API container has ADK deps"
docker compose exec -T api python - <<'PY'
import importlib.util
print("google.adk:", bool(importlib.util.find_spec("google.adk")))
print("litellm:", bool(importlib.util.find_spec("litellm")))
PY

echo "==> Wait for specialist health"
wait_for_specialist_health "http://specialist-student:8001/health" "student specialist"
wait_for_specialist_health "http://specialist-caregiver:8002/health" "caregiver specialist"

echo "==> Ensure smoke-test user exists"
SMOKE_USER_ID="$(
  docker compose exec -T api python - "$SMOKE_USER_EMAIL" <<'PY' | tail -n 1
import asyncio
import sys
from datetime import datetime, timezone
from sqlalchemy import select
from database import AsyncSessionLocal
from models.user import User

email = sys.argv[1]

async def main():
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(User).where(User.email == email))
        user = existing.scalar_one_or_none()
        if user is None:
            user = User(email=email, role="member", created_at=datetime.now(timezone.utc))
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"created smoke user {user.id} {user.email}")
        else:
            print(f"reusing smoke user {user.id} {user.email}")
        print(user.id)

asyncio.run(main())
PY
)"
export SMOKE_USER_ID
echo "SMOKE_USER_ID=$SMOKE_USER_ID"

echo "==> Health checks"
curl -fsS "$API_URL/health"
echo
curl -fsS "$API_URL/readyz"
echo
curl -fsS \
  -H "X-Internal-Api-Key: $INTERNAL_API_TOKEN" \
  -H "X-Internal-User-Id: $SMOKE_USER_ID" \
  "$API_URL/api/auth/me"
echo

echo "==> Run targeted backend tests"
pytest services/agents/tests apps/api/tests/test_agent_runner.py apps/api/tests/test_pipeline.py apps/api/tests/test_internal_auth.py -q

echo "==> Scenario smoke test"
python - <<'PY'
import json
import os
import time
import urllib.request

base = os.environ.get("API_URL", "http://127.0.0.1:8000")
headers = {
    "Content-Type": "application/json",
    "X-Internal-Api-Key": os.environ["INTERNAL_API_TOKEN"],
    "X-Internal-User-Id": os.environ["SMOKE_USER_ID"],
}
req = urllib.request.Request(
    f"{base}/api/scenarios/stressed_student/run",
    data=b"{}",
    headers=headers,
    method="POST",
)
with urllib.request.urlopen(req) as resp:
    payload = json.loads(resp.read().decode())
print("scenario start:", payload)
run_id = payload.get("run_id", payload.get("id"))
if run_id is None:
    raise SystemExit(f"scenario response missing run id: {payload}")

for _ in range(30):
    with urllib.request.urlopen(urllib.request.Request(f"{base}/api/runs/{run_id}", headers=headers)) as resp:
        trace = json.loads(resp.read().decode())
    run = trace["run"]
    print("scenario run:", run["status"], "risk:", run.get("risk_level"), "messages:", len(trace.get("messages", [])))
    if run["status"] in {"completed", "failed"}:
        print(json.dumps(trace, indent=2))
        if run["status"] != "completed":
            raise SystemExit("scenario run failed")
        break
    time.sleep(1)
else:
    raise SystemExit("scenario run timed out")
PY

echo "==> Check-in smoke test"
python - <<'PY'
import json
import os
import time
import urllib.request

base = os.environ.get("API_URL", "http://127.0.0.1:8000")
headers = {
    "Content-Type": "application/json",
    "X-Internal-Api-Key": os.environ["INTERNAL_API_TOKEN"],
    "X-Internal-User-Id": os.environ["SMOKE_USER_ID"],
}
body = json.dumps({
    "mood": 6,
    "sleep_hours": 6.5,
    "stress": 70,
    "note": "Feeling a bit off today",
}).encode()

req = urllib.request.Request(
    f"{base}/api/events/checkin",
    data=body,
    headers=headers,
    method="POST",
)
with urllib.request.urlopen(req) as resp:
    payload = json.loads(resp.read().decode())
print("checkin start:", payload)
run_id = payload.get("run_id", payload.get("id"))
if run_id is None:
    raise SystemExit(f"checkin response missing run id: {payload}")

for _ in range(30):
    with urllib.request.urlopen(urllib.request.Request(f"{base}/api/runs/{run_id}", headers=headers)) as resp:
        trace = json.loads(resp.read().decode())
    run = trace["run"]
    print("checkin run:", run["status"], "risk:", run.get("risk_level"), "messages:", len(trace.get("messages", [])))
    if run["status"] in {"completed", "failed"}:
        print(json.dumps(trace, indent=2))
        if run["status"] != "completed":
            raise SystemExit("checkin run failed")
        break
    time.sleep(1)
else:
    raise SystemExit("checkin run timed out")
PY

echo "==> Verify DB writes"
docker compose exec -T api python - <<'PY'
import asyncio
from sqlalchemy import text
from database import AsyncSessionLocal

QUERIES = [
    ("agent_runs", "select id, user_id, status, risk_level, started_at, completed_at from agent_runs order by id desc limit 5"),
    ("agent_messages", "select run_id, agent_name, agent_type, iteration from agent_messages order by id desc limit 15"),
    ("interventions", "select id, run_id, user_id, created_at from interventions order by id desc limit 5"),
    ("cases", "select id, run_id, user_id, risk_level, status from cases order by id desc limit 5"),
]

async def main():
    async with AsyncSessionLocal() as session:
        for label, sql in QUERIES:
            print(f"-- {label} --")
            rows = (await session.execute(text(sql))).all()
            for row in rows:
                print(dict(row._mapping))
            if not rows:
                print("(no rows)")

asyncio.run(main())
PY

echo "==> Smoke test complete"
