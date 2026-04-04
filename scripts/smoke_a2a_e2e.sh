#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

API_URL="${API_URL:-http://127.0.0.1:8000}"
INTERNAL_API_TOKEN="${INTERNAL_API_TOKEN:-dev-internal-token}"
SMOKE_USER_EMAIL="${SMOKE_USER_EMAIL:-local-smoke@example.com}"
export API_URL INTERNAL_API_TOKEN SMOKE_USER_EMAIL

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

require_container_module() {
  local service="$1"
  local module="$2"
  local label="$3"

  if ! docker compose exec -T "$service" python -c "import ${module}" >/dev/null 2>&1; then
    echo "$label is missing Python module '$module' in the running container." >&2
    echo "Rebuild or recreate the service before rerunning this smoke test." >&2
    echo "Suggested fix: docker compose up -d --build --force-recreate api specialist-student specialist-caregiver" >&2
    return 1
  fi
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

raise SystemExit(
    f"timed out waiting for {label} at {url}. "
    "If you recently changed specialist dependencies, recreate the specialist containers first."
)
PY
}

echo "==> Activate existing API venv"
source apps/api/.venv/bin/activate

echo "==> Wait for API"
wait_for_url "$API_URL/health" "api health"
wait_for_url "$API_URL/readyz" "api readiness"

echo "==> Verify A2A dependencies in running containers"
require_container_module "api" "a2a" "api"

echo "==> Wait for specialist health"
wait_for_specialist_health "http://specialist-student:8001/health" "student specialist"
wait_for_specialist_health "http://specialist-caregiver:8002/health" "caregiver specialist"

echo "==> Verify specialist agent cards from the API container network"
docker compose exec -T api python - <<'PY'
import json
import time
from urllib.error import URLError
from urllib.request import urlopen

targets = {
    "student": "http://specialist-student:8001/.well-known/agent-card.json",
    "caregiver": "http://specialist-caregiver:8002/.well-known/agent-card.json",
}

for label, url in targets.items():
    payload = None
    for _ in range(30):
        try:
            with urlopen(url, timeout=5) as response:
                payload = json.loads(response.read().decode())
            break
        except URLError:
            time.sleep(1)
    if payload is None:
        raise SystemExit(
            f"timed out fetching {label} agent card at {url}. "
            "If you recently changed specialist dependencies, recreate the specialist containers first."
        )
    print(label, payload["name"], payload["url"])
    assert payload["name"]
    assert payload["url"]
PY

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
        print(user.id)

asyncio.run(main())
PY
)"
export SMOKE_USER_ID
echo "SMOKE_USER_ID=$SMOKE_USER_ID"

echo "==> Run A2A scenario checks"
python - <<'PY'
import json
import os
import time
import urllib.request

base = os.environ["API_URL"]
headers = {
    "Content-Type": "application/json",
    "X-Internal-Api-Key": os.environ["INTERNAL_API_TOKEN"],
    "X-Internal-User-Id": os.environ["SMOKE_USER_ID"],
}

scenarios = {
    "stressed_student": "StudentSupportSpecialist",
    "exhausted_caregiver": "CaregiverBurnoutSpecialist",
}

for scenario_id, specialist_name in scenarios.items():
    print(f"scenario={scenario_id} expected_specialist={specialist_name}")
    req = urllib.request.Request(
        f"{base}/api/scenarios/{scenario_id}/run",
        data=b"{}",
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        payload = json.loads(resp.read().decode())
    run_id = payload.get("run_id", payload.get("id"))
    if run_id is None:
        raise SystemExit(f"missing run id for {scenario_id}: {payload}")

    trace = None
    for _ in range(45):
        with urllib.request.urlopen(
            urllib.request.Request(f"{base}/api/runs/{run_id}", headers=headers)
        ) as resp:
            trace = json.loads(resp.read().decode())
        if trace["run"]["status"] in {"completed", "failed"}:
            break
        time.sleep(1)

    if trace is None:
        raise SystemExit(f"no trace for {scenario_id}")
    if trace["run"]["status"] != "completed":
        raise SystemExit(f"{scenario_id} failed: {trace['run']}")

    messages = trace.get("messages", [])
    a2a_messages = [m for m in messages if m.get("agent_type") == "a2a"]
    if not a2a_messages:
        raise SystemExit(f"{scenario_id} completed without any a2a trace messages")

    names = {m.get("agent_name") for m in a2a_messages}
    if specialist_name not in names:
        raise SystemExit(
            f"{scenario_id} completed but missing expected specialist {specialist_name}; got {sorted(names)}"
        )

    latest = next(m for m in reversed(a2a_messages) if m.get("agent_name") == specialist_name)
    output = latest.get("output", {})
    print(
        json.dumps(
            {
                "run_id": run_id,
                "status": trace["run"]["status"],
                "risk_level": trace["run"].get("risk_level"),
                "specialist": specialist_name,
                "agent_type": latest.get("agent_type"),
                "generation_mode": output.get("generation_mode"),
                "resource_count": len(output.get("resources", [])),
            },
            indent=2,
        )
    )
PY

echo "==> A2A end-to-end smoke test complete"
