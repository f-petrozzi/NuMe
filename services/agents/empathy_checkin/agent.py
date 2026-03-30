from __future__ import annotations

try:
    from services.agents.adk_compat import LlmAgent
    from services.agents.llm_utils import OpenAIJsonClient, build_json_prompt
    from services.agents.prompts import EMPATHY_CHECKIN_PROMPT
    from services.agents.schemas import EmpathyResult
except ImportError:
    from adk_compat import LlmAgent
    from llm_utils import OpenAIJsonClient, build_json_prompt
    from prompts import EMPATHY_CHECKIN_PROMPT
    from schemas import EmpathyResult


class EmpathyCheckinAgent:
    def __init__(self) -> None:
        self.definition = LlmAgent(
            name="EmpathyCheckin",
            instruction=EMPATHY_CHECKIN_PROMPT,
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
            generation_error=(llm_result or {}).get("generation_error", ""),
        ).model_dump()

    def _generate_with_llm(
        self,
        *,
        risk_level: str,
        persona_type: str,
        signal_summary: str,
    ) -> dict | None:
        prompt = build_json_prompt(
            instruction=EMPATHY_CHECKIN_PROMPT,
            response_schema={"empathy_message": "2-4 sentence message"},
            payload={
                "risk_level": risk_level,
                "persona_type": persona_type,
                "signal_summary": signal_summary,
            },
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
