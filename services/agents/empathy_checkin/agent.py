from __future__ import annotations

from typing import Any

try:
    from services.agents.adk_compat import LlmAgent
    from services.agents.llm_utils import (
        DEFAULT_OPENAI_MODEL,
        OpenAIJsonClient,
        build_json_prompt,
        extract_json_object,
    )
    from services.agents.prompts import EMPATHY_CHECKIN_PROMPT
    from services.agents.runtime import build_stateful_llm_agent
    from services.agents.schemas import EmpathyResult
except ImportError:
    from adk_compat import LlmAgent
    from llm_utils import (
        DEFAULT_OPENAI_MODEL,
        OpenAIJsonClient,
        build_json_prompt,
        extract_json_object,
    )
    from prompts import EMPATHY_CHECKIN_PROMPT
    from runtime import build_stateful_llm_agent
    from schemas import EmpathyResult


class EmpathyCheckinAgent:
    state_key = "empathy_result"

    def __init__(self, model: Any = DEFAULT_OPENAI_MODEL) -> None:
        self.definition = build_stateful_llm_agent(
            name="EmpathyCheckin",
            model=model,
            instruction_builder=lambda state: self.build_prompt(
                risk_level=str((state.get("risk_assessment", {}) or {}).get("risk_level", "low")),
                persona_type=str(state.get("persona_type", "older_adult")),
                signal_summary=str((state.get("signal_interpretation", {}) or {}).get("summary", "")),
            ),
            state_key=self.state_key,
            parse_output=lambda text, state: self.parse_response_text(text),
            fallback_output=lambda state, error: self.fallback_result(
                risk_level=str((state.get("risk_assessment", {}) or {}).get("risk_level", "low")),
                persona_type=str(state.get("persona_type", "older_adult")),
                signal_summary=str((state.get("signal_interpretation", {}) or {}).get("summary", "")),
                generation_error=error,
            ),
        )
        self._llm = OpenAIJsonClient()

    def run(self, *, risk_level: str, persona_type: str, signal_summary: str) -> dict:
        llm_result = self._generate_with_llm(
            risk_level=risk_level,
            persona_type=persona_type,
            signal_summary=signal_summary,
        )
        if llm_result and "empathy_message" in llm_result:
            return llm_result

        return self.fallback_result(
            risk_level=risk_level,
            persona_type=persona_type,
            signal_summary=signal_summary,
            generation_error=(llm_result or {}).get("generation_error", ""),
        )

    def build_prompt(self, *, risk_level: str, persona_type: str, signal_summary: str) -> str:
        return build_json_prompt(
            instruction=EMPATHY_CHECKIN_PROMPT,
            response_schema={"empathy_message": "2-4 sentence message"},
            payload={
                "risk_level": risk_level,
                "persona_type": persona_type,
                "signal_summary": signal_summary,
            },
        )

    def parse_response_text(self, text: str) -> dict:
        payload = extract_json_object(text)
        message = str(payload.get("empathy_message", "")).strip()
        if not message:
            raise ValueError("Model returned an empty empathy message.")
        return EmpathyResult(
            empathy_message=message,
            generation_mode="llm",
            generation_error="",
        ).model_dump()

    def fallback_result(
        self,
        *,
        risk_level: str,
        persona_type: str,
        signal_summary: str,
        generation_error: str = "",
    ) -> dict:
        del risk_level, signal_summary

        if persona_type == "caregiver":
            message = (
                "You are carrying a lot, and your signals reflect that. "
                "Today’s plan keeps the steps light and practical so support feels doable."
            )
        elif persona_type == "student":
            message = (
                "This stretch looks demanding. "
                "Today’s plan is meant to lower pressure with one simple meal, a short reset, and a gentle check-in."
            )
        else:
            message = (
                "Your recent signals suggest a harder-than-usual day. "
                "This plan keeps things simple, steady, and easier to follow."
            )
        return EmpathyResult(
            empathy_message=message,
            generation_mode="fallback",
            generation_error=generation_error,
        ).model_dump()

    def _generate_with_llm(
        self,
        *,
        risk_level: str,
        persona_type: str,
        signal_summary: str,
    ) -> dict | None:
        prompt = self.build_prompt(
            risk_level=risk_level,
            persona_type=persona_type,
            signal_summary=signal_summary,
        )
        result = self._llm.generate_json(prompt)
        if not result.payload:
            return {"generation_error": result.error}

        try:
            message = str(result.payload.get("empathy_message", "")).strip()
            if not message:
                raise ValueError("Model returned an empty empathy message.")
            return EmpathyResult(
                empathy_message=message,
                generation_mode="llm",
                generation_error="",
            ).model_dump()
        except Exception as exc:
            return {"generation_error": f"{type(exc).__name__}: {exc}"}
