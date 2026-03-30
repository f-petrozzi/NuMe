from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, List

from fastapi import FastAPI
from pydantic import BaseModel


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


def build_specialist_app(
    *,
    title: str,
    instruction: str,
    response_schema: Dict[str, Any],
    fallback_factory,
):
    app = FastAPI(title=title)
    llm = OpenAIJsonClient()

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok", "service": title}

    @app.post("/invoke")
    async def invoke(body: SpecialistRequest) -> Dict[str, Any]:
        prompt = build_json_prompt(
            instruction=instruction,
            response_schema=response_schema,
            payload=body.model_dump(),
        )
        result = llm.generate_json(prompt)
        if result.payload:
            try:
                merged_resources = sorted(
                    {
                        *(body.resources or []),
                        *[str(item).strip() for item in result.payload.get("resources", []) if str(item).strip()],
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
                fallback = fallback_factory(body=body)
                fallback["generation_mode"] = "fallback"
                fallback["generation_error"] = f"{type(exc).__name__}: {exc}"
                return fallback

        fallback = fallback_factory(body=body)
        fallback["generation_mode"] = "fallback"
        fallback["generation_error"] = result.error
        return fallback

    return app
