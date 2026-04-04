from __future__ import annotations

from services.remote_specialists.caregiver_burnout.agent import root_agent
from services.remote_specialists.common import build_specialist_app


app = build_specialist_app(
    agent=root_agent,
    service_name="caregiver-burnout-specialist",
    default_public_base_url="http://localhost:8002",
)
