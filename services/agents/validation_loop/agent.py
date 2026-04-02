from __future__ import annotations

import copy
import json
from typing import Any, Dict, List, Mapping, Tuple

try:
    from google.adk.events.event import Event
    from google.adk.events.event_actions import EventActions

    from services.agents.adk_compat import BaseAgent, LlmAgent, LoopAgent
    from services.agents.llm_utils import DEFAULT_OPENAI_MODEL, OpenAIJsonClient, extract_json_object
    from services.agents.prompts import VALIDATION_LOOP_PROMPT
    from services.agents.runtime import build_stateful_llm_agent
    from services.agents.schemas import ValidationResult
except ImportError:
    from adk_compat import BaseAgent, LlmAgent, LoopAgent
    from llm_utils import DEFAULT_OPENAI_MODEL, OpenAIJsonClient, extract_json_object
    from prompts import VALIDATION_LOOP_PROMPT
    from runtime import build_stateful_llm_agent
    from schemas import ValidationResult

    class EventActions:  # pragma: no cover - local fallback only
        def __init__(self, state_delta: Dict[str, Any] | None = None, escalate: bool | None = None):
            self.state_delta = state_delta or {}
            self.escalate = escalate

    class Event:  # pragma: no cover - local fallback only
        def __init__(
            self,
            *,
            invocation_id: str,
            author: str,
            branch: str | None = None,
            actions: EventActions | None = None,
        ) -> None:
            self.invocation_id = invocation_id
            self.author = author
            self.branch = branch
            self.actions = actions or EventActions()


class ValidationLoopStateAgent(BaseAgent):
    helper: Any = None

    async def _run_async_impl(self, ctx: Any):
        current_plan = copy.deepcopy(ctx.session.state.get("intervention_plan", {}))
        validation_result = copy.deepcopy(ctx.session.state.get("validation_step_result", {}))
        iterations = copy.deepcopy(ctx.session.state.get("validation_iterations", []))
        plan_changed = bool(ctx.session.state.get("validation_plan_changed", False))

        if validation_result.get("revised_plan") is not None:
            current_plan = self.helper._merge_plan(current_plan, validation_result["revised_plan"])
            validation_result = {
                **validation_result,
                "revised_plan": copy.deepcopy(current_plan),
            }
            plan_changed = True
        elif plan_changed and (validation_result.get("approved") or validation_result.get("halt")):
            validation_result = {
                **validation_result,
                "revised_plan": copy.deepcopy(current_plan),
            }

        iteration_number = len(iterations) + 1
        iteration_entry = {
            "iteration": iteration_number,
            "input": {
                "findings": copy.deepcopy(
                    (ctx.session.state.get("signal_interpretation", {}) or {}).get("findings", [])
                ),
                "risk_level": (ctx.session.state.get("risk_assessment", {}) or {}).get("risk_level", "low"),
                "intervention_plan": copy.deepcopy(current_plan),
                "empathy_message": (ctx.session.state.get("empathy_result", {}) or {}).get(
                    "empathy_message",
                    "",
                ),
            },
            "output": copy.deepcopy(validation_result),
        }
        iterations.append(iteration_entry)

        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            actions=EventActions(
                state_delta={
                    "intervention_plan": current_plan,
                    "validation_result": validation_result,
                    "validation_iterations": iterations,
                    "validation_plan_changed": plan_changed,
                },
                escalate=bool(validation_result.get("approved") or validation_result.get("halt")),
            ),
        )

    async def _run_live_impl(self, ctx: Any):
        del ctx
        raise NotImplementedError("Live validation loop is not supported.")
        yield


class ValidationLoopAgent:
    def __init__(self, model: Any = DEFAULT_OPENAI_MODEL) -> None:
        self.validator = build_stateful_llm_agent(
            name="ValidationAgent",
            model=model,
            instruction_builder=lambda state: self.build_prompt(
                findings=list((state.get("signal_interpretation", {}) or {}).get("findings", [])),
                risk_level=str((state.get("risk_assessment", {}) or {}).get("risk_level", "low")),
                intervention_plan=copy.deepcopy(state.get("intervention_plan", {})),
                empathy_message=str((state.get("empathy_result", {}) or {}).get("empathy_message", "")),
                user_profile=dict(state.get("profile", {})),
                low_energy_mode=bool(
                    ((state.get("profile", {}) or {}).get("accessibility") or {}).get(
                        "low_energy_mode",
                        False,
                    )
                ),
            ),
            state_key="validation_step_result",
            parse_output=lambda text, state: self.parse_response_text(text),
            fallback_output=lambda state, error: self._fallback_from_state(state, error),
        )
        self.apply_agent = ValidationLoopStateAgent(
            name="ValidationLoopStateUpdate",
            description="Applies validation revisions to the current intervention plan.",
        )
        self.apply_agent.helper = self
        self.definition = LoopAgent(
            name="ValidationLoop",
            sub_agents=[self.validator, self.apply_agent],
            max_iterations=3,
        )
        self._llm = OpenAIJsonClient()

    def validate(
        self,
        *,
        findings: List[Dict[str, Any]],
        risk_level: str,
        intervention_plan: Dict[str, Any],
        empathy_message: str,
        user_profile: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        current_plan = copy.deepcopy(intervention_plan)
        iterations: List[Dict[str, Any]] = []
        low_energy_mode = (user_profile.get("accessibility") or {}).get("low_energy_mode", False)
        plan_changed = False

        for iteration in range(1, 4):
            llm_result = self._generate_with_llm(
                findings=findings,
                risk_level=risk_level,
                intervention_plan=current_plan,
                empathy_message=empathy_message,
                user_profile=user_profile,
                low_energy_mode=low_energy_mode,
            )
            if llm_result and "approved" in llm_result:
                result = llm_result
            else:
                result = self._fallback_validate(
                    current_plan=current_plan,
                    risk_level=risk_level,
                    low_energy_mode=low_energy_mode,
                    iteration=iteration,
                    generation_error=(llm_result or {}).get("generation_error", ""),
                )

            if result.get("revised_plan") is not None:
                current_plan = self._merge_plan(current_plan, result["revised_plan"])
                result = {
                    **result,
                    "revised_plan": copy.deepcopy(current_plan),
                }
                plan_changed = True
            elif plan_changed and (result["approved"] or result["halt"]):
                result = {
                    **result,
                    "revised_plan": copy.deepcopy(current_plan),
                }

            iterations.append(
                {
                    "iteration": iteration,
                    "input": {
                        "findings": findings,
                        "risk_level": risk_level,
                        "intervention_plan": current_plan,
                        "empathy_message": empathy_message,
                    },
                    "output": result,
                }
            )
            if result["approved"] or result["halt"]:
                return result, iterations

        return result, iterations

    @staticmethod
    def _merge_plan(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
        merged = copy.deepcopy(base)
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = ValidationLoopAgent._merge_plan(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        return merged

    def build_prompt(
        self,
        *,
        findings: List[Dict[str, Any]],
        risk_level: str,
        intervention_plan: Dict[str, Any],
        empathy_message: str,
        user_profile: Dict[str, Any],
        low_energy_mode: bool,
    ) -> str:
        return (
            f"{VALIDATION_LOOP_PROMPT}\n\n"
            "Return only valid JSON with no markdown fences.\n"
            "Response schema:\n"
            f"{json.dumps(self._response_schema(), indent=2)}\n\n"
            "Input:\n"
            f"{json.dumps({'findings': findings, 'risk_level': risk_level, 'intervention_plan': intervention_plan, 'empathy_message': empathy_message, 'user_profile': user_profile, 'low_energy_mode': low_energy_mode}, indent=2)}"
            "\n\nIf you provide revised_plan, include the full plan object. Do not return only changed fields."
        )

    @staticmethod
    def _response_schema() -> Dict[str, Any]:
        return {
            "approved": True,
            "issues": [
                {
                    "type": "contradiction | accessibility_mismatch | policy_violation | low_confidence | missing_evidence",
                    "description": "issue description",
                    "suggested_fix": "how to fix",
                }
            ],
            "revised_plan": {
                "meal_suggestion": {
                    "title": "short title",
                    "description": "1-2 sentence meal suggestion",
                    "rationale": "why this meal fits the condition",
                },
                "activity_suggestion": {
                    "title": "short title",
                    "description": "1-2 sentence activity suggestion",
                    "duration_minutes": 10,
                    "intensity": "very_low | low | moderate",
                    "rationale": "why this activity fits the condition",
                },
                "wellness_action": {
                    "title": "short title",
                    "description": "1-2 sentence wellness action",
                    "rationale": "why this action fits the condition",
                },
                "resources": ["resource title"],
                "notes": "brief planning notes",
                "meal_constraints": ["tag1", "tag2"],
            },
            "halt": False,
        }

    def parse_response_text(self, text: str) -> Dict[str, Any]:
        return self._parse_payload(extract_json_object(text))

    def _parse_payload(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        issues = [
            {
                "type": str(issue.get("type", "")).strip(),
                "description": str(issue.get("description", "")).strip(),
                "suggested_fix": str(issue.get("suggested_fix", "")).strip(),
            }
            for issue in payload.get("issues", [])
            if str(issue.get("type", "")).strip()
        ]
        revised_plan = payload.get("revised_plan")
        if revised_plan is not None and not isinstance(revised_plan, dict):
            raise ValueError("revised_plan must be an object or null.")

        return ValidationResult(
            approved=bool(payload.get("approved", False)),
            issues=issues,
            revised_plan=revised_plan,
            halt=bool(payload.get("halt", False)),
            generation_mode="llm",
            generation_error="",
        ).model_dump()

    def _fallback_from_state(
        self,
        state: Mapping[str, Any],
        generation_error: str,
    ) -> Dict[str, Any]:
        return self._fallback_validate(
            current_plan=copy.deepcopy(state.get("intervention_plan", {})),
            risk_level=str((state.get("risk_assessment", {}) or {}).get("risk_level", "low")),
            low_energy_mode=bool(
                ((state.get("profile", {}) or {}).get("accessibility") or {}).get(
                    "low_energy_mode",
                    False,
                )
            ),
            iteration=len(list(state.get("validation_iterations", []))) + 1,
            generation_error=generation_error,
        )

    def _generate_with_llm(
        self,
        *,
        findings: List[Dict[str, Any]],
        risk_level: str,
        intervention_plan: Dict[str, Any],
        empathy_message: str,
        user_profile: Dict[str, Any],
        low_energy_mode: bool,
    ) -> Dict[str, Any] | None:
        prompt = self.build_prompt(
            findings=findings,
            risk_level=risk_level,
            intervention_plan=intervention_plan,
            empathy_message=empathy_message,
            user_profile=user_profile,
            low_energy_mode=low_energy_mode,
        )
        result = self._llm.generate_json(prompt)
        if not result.payload:
            return {"generation_error": result.error}

        try:
            return self._parse_payload(result.payload)
        except Exception as exc:
            return {"generation_error": f"{type(exc).__name__}: {exc}"}

    def _fallback_validate(
        self,
        *,
        current_plan: Dict[str, Any],
        risk_level: str,
        low_energy_mode: bool,
        iteration: int,
        generation_error: str,
    ) -> Dict[str, Any]:
        issues = []
        activity = current_plan["activity_suggestion"]
        if risk_level in {"high", "critical"} and activity["intensity"] not in {"very_low", "low"}:
            issues.append(
                {
                    "type": "contradiction",
                    "description": "Activity intensity is too high for the current strain level.",
                    "suggested_fix": "Lower the activity intensity and shorten the duration.",
                }
            )
        if low_energy_mode and activity["duration_minutes"] > 15:
            issues.append(
                {
                    "type": "accessibility_mismatch",
                    "description": "Plan exceeds low-energy preference.",
                    "suggested_fix": "Reduce duration to 10-15 minutes and simplify instructions.",
                }
            )

        approved = not issues
        halt = bool(iteration == 3 and issues)
        revised_plan = None
        if issues and not halt:
            current_plan["activity_suggestion"]["intensity"] = "low"
            current_plan["activity_suggestion"]["duration_minutes"] = min(
                current_plan["activity_suggestion"]["duration_minutes"], 10
            )
            current_plan["notes"] = (
                current_plan.get("notes", "") + " Validation reduced effort for safety."
            ).strip()
            revised_plan = copy.deepcopy(current_plan)

        return ValidationResult(
            approved=approved,
            issues=issues,
            revised_plan=revised_plan,
            halt=halt,
            generation_mode="fallback",
            generation_error=generation_error,
        ).model_dump()
