from __future__ import annotations

from services.remote_specialists.common import build_specialist_app
from services.remote_specialists.student_support.agent import root_agent


app = build_specialist_app(
    agent=root_agent,
    service_name="student-support-specialist",
    default_public_base_url="http://localhost:8001",
)
