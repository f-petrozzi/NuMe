from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any, Callable, Dict, List
from urllib.parse import urlparse

from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.genai import types as genai_types
from pydantic import BaseModel, ConfigDict, ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from typing_extensions import override


REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO_ROOT / "services" / "agents"
for path in (str(REPO_ROOT), str(AGENTS_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from llm_utils import OpenAIJsonClient, build_json_prompt
from schemas import SpecialistResult


class SpecialistRequest(BaseModel):
    persona_type: str
    findings: List[Dict[str, Any]]
    risk: Dict[str, Any]
    draft_plan: Dict[str, Any]
    resources: List[str]


class StructuredSpecialistAgent(BaseAgent):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    instruction: str
    response_schema: Dict[str, Any]
    fallback_factory: Callable[..., Dict[str, Any]]

    def execute(self, body: SpecialistRequest) -> Dict[str, Any]:
        prompt = build_json_prompt(
            instruction=self.instruction,
            response_schema=self.response_schema,
            payload=body.model_dump(),
        )
        result = OpenAIJsonClient().generate_json(prompt)
        if result.payload:
            try:
                merged_resources = sorted(
                    {
                        *(body.resources or []),
                        *[
                            str(item).strip()
                            for item in result.payload.get("resources", [])
                            if str(item).strip()
                        ],
                    }
                )
                return SpecialistResult(
                    enriched_context=str(result.payload.get("enriched_context", "")).strip(),
                    resources=merged_resources,
                    intervention_adjustments=[
                        str(item).strip()
                        for item in result.payload.get("intervention_adjustments", [])
                        if str(item).strip()
                    ],
                    burnout_risk_flag=result.payload.get("burnout_risk_flag"),
                    escalation_recommendation=result.payload.get("escalation_recommendation"),
                    generation_mode="llm",
                    generation_error="",
                ).model_dump()
            except Exception as exc:
                fallback = self.fallback_factory(body=body)
                fallback["generation_mode"] = "fallback"
                fallback["generation_error"] = f"{type(exc).__name__}: {exc}"
                return fallback

        fallback = self.fallback_factory(body=body)
        fallback["generation_mode"] = "fallback"
        fallback["generation_error"] = result.error
        return fallback

    @override
    async def _run_async_impl(
        self,
        ctx: InvocationContext,
    ):
        try:
            body = _extract_specialist_request(ctx)
            response_payload = self.execute(body)
        except Exception as exc:
            response_payload = SpecialistResult(
                enriched_context="",
                resources=[],
                intervention_adjustments=[],
                burnout_risk_flag=None,
                escalation_recommendation=None,
                generation_mode="fallback",
                generation_error=f"{type(exc).__name__}: {exc}",
            ).model_dump()

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=genai_types.Content(
                role="model",
                parts=[genai_types.Part(text=json.dumps(response_payload, sort_keys=True))],
            ),
        )


def _extract_specialist_request(ctx: InvocationContext) -> SpecialistRequest:
    raw_text = ""
    if ctx.user_content and ctx.user_content.parts:
        raw_text = "\n".join(
            [
                str(getattr(part, "text", "") or "").strip()
                for part in ctx.user_content.parts
                if str(getattr(part, "text", "") or "").strip()
            ]
        ).strip()

    if not raw_text:
        for event in reversed(ctx.session.events):
            if event.author != "user" or not event.content or not event.content.parts:
                continue
            raw_text = "\n".join(
                [
                    str(getattr(part, "text", "") or "").strip()
                    for part in event.content.parts
                    if str(getattr(part, "text", "") or "").strip()
                ]
            ).strip()
            if raw_text:
                break

    if not raw_text:
        raise ValueError("Specialist request is empty.")

    return SpecialistRequest.model_validate_json(raw_text)


def build_specialist_app(
    *,
    agent: StructuredSpecialistAgent,
    service_name: str,
    default_public_base_url: str,
):
    public_base_url = os.getenv("A2A_PUBLIC_BASE_URL", default_public_base_url).strip().rstrip("/")
    parsed = urlparse(public_base_url)
    protocol = parsed.scheme or "http"
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if protocol == "https" else 80)

    app = to_a2a(
        agent=agent,
        host=host,
        port=port,
        protocol=protocol,
    )

    async def health(_request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "service": service_name,
                "agent": agent.name,
            }
        )

    async def invoke(request: Request) -> JSONResponse:
        try:
            body = SpecialistRequest.model_validate(await request.json())
        except ValidationError as exc:
            return JSONResponse({"detail": exc.errors(include_url=False)}, status_code=422)
        return JSONResponse(agent.execute(body))

    app.add_route("/health", health, methods=["GET"])
    app.add_route("/invoke", invoke, methods=["POST"])
    return app
