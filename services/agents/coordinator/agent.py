from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from time import sleep
from typing import Any, Dict, List
from uuid import uuid4

try:
    from google.adk.events.event import Event
except Exception:  # pragma: no cover - google-adk is optional in some environments
    Event = Any  # type: ignore[assignment]

try:
    from services.agents.adk_compat import ParallelAgent, RemoteA2aAgent, SequentialAgent
    from services.agents.config import Settings
    from services.agents.llm_utils import OpenAIJsonClient, build_json_prompt, extract_json_object
    from services.agents.prompts import CARE_COORDINATOR_PROMPT
    from services.agents.runtime import (
        AgentType,
        TraceRecorder,
        adk_runtime_enabled,
        build_adk_model,
        execute_parallel,
        run_in_memory_agent,
        run_text_agent,
    )
    from services.agents.schemas import FinalPlan, SpecialistResult
    from services.agents.tooling import ToolProvider

    from services.agents.empathy_checkin import EmpathyCheckinAgent
    from services.agents.intervention_planning import InterventionPlanningAgent
    from services.agents.risk_stratification import RiskStratificationAgent
    from services.agents.signal_interpretation import SignalInterpretationAgent
    from services.agents.validation_loop import ValidationLoopAgent
except ImportError:
    from adk_compat import ParallelAgent, RemoteA2aAgent, SequentialAgent
    from config import Settings
    from llm_utils import OpenAIJsonClient, build_json_prompt, extract_json_object
    from prompts import CARE_COORDINATOR_PROMPT
    from runtime import (
        AgentType,
        TraceRecorder,
        adk_runtime_enabled,
        build_adk_model,
        execute_parallel,
        run_in_memory_agent,
        run_text_agent,
    )
    from schemas import FinalPlan, SpecialistResult
    from tooling import ToolProvider

    from empathy_checkin import EmpathyCheckinAgent
    from intervention_planning import InterventionPlanningAgent
    from risk_stratification import RiskStratificationAgent
    from signal_interpretation import SignalInterpretationAgent
    from validation_loop import ValidationLoopAgent


class CareCoordinatorPipeline:
    _REMOTE_SPECIALIST_MAX_ATTEMPTS = 3
    _REMOTE_SPECIALIST_RETRY_DELAY_SECONDS = 0.75

    def __init__(self, settings: Settings, tool_provider: ToolProvider) -> None:
        self.settings = settings
        self.tool_provider = tool_provider
        self.use_adk_runtime = adk_runtime_enabled()
        preferred_model = settings.openai_model or settings.azure_openai_deployment or None
        self.model = build_adk_model(preferred_model)
        self.signal_agent = SignalInterpretationAgent(model=self.model)
        self.risk_agent = RiskStratificationAgent(model=self.model)
        self.intervention_agent = InterventionPlanningAgent(model=self.model)
        self.empathy_agent = EmpathyCheckinAgent(model=self.model)
        self.validation_loop = ValidationLoopAgent(model=self.model)
        parallel_kwargs = {}
        if self.use_adk_runtime:
            parallel_kwargs["after_agent_callback"] = self._after_parallel_phase
        self.parallel_phase = ParallelAgent(
            name="CareCoordinatorParallelPhase",
            sub_agents=[
                self.signal_agent.definition,
                self.risk_agent.definition,
                self.intervention_agent.definition,
            ],
            **parallel_kwargs,
        )
        self.definition = SequentialAgent(
            name="CareCoordinator",
            sub_agents=[
                self.parallel_phase,
                self.empathy_agent.definition,
                self.validation_loop.definition,
            ],
        )
        self.prompt = CARE_COORDINATOR_PROMPT
        self._llm = OpenAIJsonClient()

    @staticmethod
    def _specialist_card_url(base_url: str) -> str:
        return f"{base_url.rstrip('/')}/.well-known/agent-card.json"

    def _specialist_for(self, persona_type: str) -> RemoteA2aAgent | None:
        if persona_type == "student":
            return RemoteA2aAgent(
                name="StudentSupportSpecialist",
                agent_card=self._specialist_card_url(self.settings.student_specialist_url),
                description="Student support remote specialist",
            )
        if persona_type == "caregiver":
            return RemoteA2aAgent(
                name="CaregiverBurnoutSpecialist",
                agent_card=self._specialist_card_url(self.settings.caregiver_specialist_url),
                description="Caregiver support remote specialist",
            )
        return None

    def _run_specialist(
        self,
        *,
        persona_type: str,
        findings: List[Dict[str, Any]],
        risk: Dict[str, Any],
        draft_plan: Dict[str, Any],
        specialist_agent: RemoteA2aAgent | None,
    ) -> tuple[str, AgentType, Dict[str, Any]]:
        resources = [item["title"] for item in self.tool_provider.get_resources(persona_type)]
        if specialist_agent:
            try:
                return (
                    specialist_agent.name,
                    AgentType.a2a,
                    self._invoke_remote_specialist(
                        specialist_agent=specialist_agent,
                        persona_type=persona_type,
                        findings=findings,
                        risk=risk,
                        draft_plan=draft_plan,
                        resources=resources,
                    ),
                )
            except Exception as exc:
                fallback_name = (
                    "StudentSupportFallback"
                    if persona_type == "student"
                    else "CaregiverBurnoutFallback"
                )
                return (
                    fallback_name,
                    AgentType.local,
                    self._generate_local_specialist(
                        persona_type=persona_type,
                        findings=findings,
                        risk=risk,
                        draft_plan=draft_plan,
                        resources=resources,
                        upstream_error=f"{type(exc).__name__}: {exc}",
                    ),
                )
        return (
            "AccessibilityAdaptation",
            AgentType.local,
            self._generate_local_specialist(
                persona_type=persona_type,
                findings=findings,
                risk=risk,
                draft_plan=draft_plan,
                resources=resources,
            ),
        )

    @staticmethod
    def _specialist_prompt_bundle(persona_type: str) -> tuple[str, Dict[str, Any], Dict[str, Any]]:
        if persona_type == "student":
            return (
                (
                    "You are the Student Support Specialist for NüMe. "
                    "You receive signal findings, risk level, an intervention draft, "
                    "and available campus resources. Return structured JSON only. "
                    "Interpret the case in the context of academic overload, exam pressure, "
                    "and student recovery; strengthen the intervention with realistic, "
                    "low-pressure student-specific adjustments; include campus-specific resources "
                    "already provided when relevant; and flag burnout risk when the case suggests "
                    "sustained academic overload."
                ),
                {
                    "enriched_context": "student-specific interpretation",
                    "resources": ["resource title"],
                    "intervention_adjustments": ["specific change"],
                    "burnout_risk_flag": True,
                    "escalation_recommendation": "none | coordinator_review",
                },
                {
                    "enriched_context": "Stress pattern aligns with academic overload and low recovery.",
                    "intervention_adjustments": [
                        "Favor low-pressure study-break framing.",
                        "Include campus counseling and academic support options.",
                    ],
                    "burnout_risk_flag": None,
                    "escalation_recommendation": None,
                },
            )

        if persona_type == "caregiver":
            return (
                (
                    "You are the Caregiver Burnout Specialist for NüMe. "
                    "You receive signal findings, risk level, an intervention draft, "
                    "and available support resources. Return structured JSON only. "
                    "Interpret the case through caregiver burden and depleted recovery capacity; "
                    "adjust interventions to be micro-effort and realistic under time scarcity; "
                    "surface support-group or respite resources from the provided list when relevant; "
                    "and recommend coordinator escalation when burden is high."
                ),
                {
                    "enriched_context": "caregiver-specific interpretation",
                    "resources": ["resource title"],
                    "intervention_adjustments": ["specific change"],
                    "burnout_risk_flag": True,
                    "escalation_recommendation": "none | coordinator_review | trusted_contact_outreach",
                },
                {
                    "enriched_context": "Signals suggest caregiver burden with limited recovery capacity.",
                    "intervention_adjustments": [
                        "Favor micro-effort actions with no equipment.",
                        "Include respite and support-group resources.",
                    ],
                    "burnout_risk_flag": True,
                    "escalation_recommendation": None,
                },
            )

        return (
            (
                "You are the Accessibility Adaptation Specialist for NüMe. "
                "Return structured JSON only. Keep the plan simple, accessible, and low-friction "
                "for older adults or accessibility-focused users."
            ),
            {
                "enriched_context": "short interpretation",
                "resources": ["resource title"],
                "intervention_adjustments": ["specific change"],
                "burnout_risk_flag": False,
                "escalation_recommendation": "none | coordinator_review",
            },
            {
                "enriched_context": "Accessibility-focused adaptation kept the plan simple and easy to follow.",
                "intervention_adjustments": ["Keep plan simple and accessible."],
                "burnout_risk_flag": None,
                "escalation_recommendation": "none",
            },
        )

    @staticmethod
    def _combine_generation_error(upstream_error: str, generation_error: str) -> str:
        parts = [part.strip() for part in (upstream_error, generation_error) if part and part.strip()]
        return " | ".join(parts)

    @staticmethod
    def _is_transient_remote_specialist_error(error: Exception) -> bool:
        text = str(error).lower()
        return any(
            marker in text
            for marker in (
                "all connection attempts failed",
                "connection refused",
                "connection reset",
                "failed to resolve agentcard",
                "failed to resolve agent card",
                "network communication error",
                "remote specialist returned no text response",
                "service unavailable",
                "timed out",
            )
        )

    def _generate_local_specialist(
        self,
        *,
        persona_type: str,
        findings: List[Dict[str, Any]],
        risk: Dict[str, Any],
        draft_plan: Dict[str, Any],
        resources: List[str],
        upstream_error: str = "",
    ) -> Dict[str, Any]:
        instruction, response_schema, fallback = self._specialist_prompt_bundle(persona_type)
        fallback_resources = sorted(set(resources))
        fallback_burnout = fallback["burnout_risk_flag"]
        if fallback_burnout is None:
            fallback_burnout = risk.get("risk_level") in {"moderate", "high", "critical"}

        fallback_escalation = fallback["escalation_recommendation"]
        if fallback_escalation is None:
            fallback_escalation = (
                "coordinator_review"
                if risk.get("risk_level") in {"high", "critical"}
                else "none"
            )

        prompt = build_json_prompt(
            instruction=instruction,
            response_schema=response_schema,
            payload={
                "persona_type": persona_type,
                "findings": findings,
                "risk": risk,
                "draft_plan": draft_plan,
                "resources": resources,
            },
        )
        result = self._llm.generate_json(prompt)
        if result.payload:
            try:
                return SpecialistResult(
                    enriched_context=str(result.payload.get("enriched_context", "")).strip(),
                    resources=sorted(set(fallback_resources + result.payload.get("resources", []))),
                    intervention_adjustments=[
                        str(item).strip()
                        for item in result.payload.get("intervention_adjustments", [])
                        if str(item).strip()
                    ],
                    burnout_risk_flag=result.payload.get("burnout_risk_flag"),
                    escalation_recommendation=result.payload.get("escalation_recommendation"),
                    generation_mode="llm_fallback" if upstream_error else "llm",
                    generation_error=self._combine_generation_error(upstream_error, ""),
                ).model_dump()
            except Exception as exc:
                upstream_error = self._combine_generation_error(
                    upstream_error,
                    f"{type(exc).__name__}: {exc}",
                )

        return SpecialistResult(
            enriched_context=fallback["enriched_context"],
            resources=fallback_resources,
            intervention_adjustments=fallback["intervention_adjustments"],
            burnout_risk_flag=fallback_burnout,
            escalation_recommendation=fallback_escalation,
            generation_mode="fallback",
            generation_error=self._combine_generation_error(upstream_error, result.error),
        ).model_dump()

    def _invoke_remote_specialist(
        self,
        *,
        specialist_agent: RemoteA2aAgent,
        persona_type: str,
        findings: List[Dict[str, Any]],
        risk: Dict[str, Any],
        draft_plan: Dict[str, Any],
        resources: List[str],
    ) -> Dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, self._REMOTE_SPECIALIST_MAX_ATTEMPTS + 1):
            try:
                return self._invoke_remote_specialist_once(
                    specialist_agent=specialist_agent,
                    persona_type=persona_type,
                    findings=findings,
                    risk=risk,
                    draft_plan=draft_plan,
                    resources=resources,
                )
            except Exception as exc:
                last_error = exc
                should_retry = (
                    attempt < self._REMOTE_SPECIALIST_MAX_ATTEMPTS
                    and self._is_transient_remote_specialist_error(exc)
                )
                if not should_retry:
                    raise
                sleep(self._REMOTE_SPECIALIST_RETRY_DELAY_SECONDS * attempt)

        raise RuntimeError(
            f"Remote specialist retry budget exhausted for {specialist_agent.name}: {last_error}"
        ) from last_error

    def _invoke_remote_specialist_once(
        self,
        *,
        specialist_agent: RemoteA2aAgent,
        persona_type: str,
        findings: List[Dict[str, Any]],
        risk: Dict[str, Any],
        draft_plan: Dict[str, Any],
        resources: List[str],
    ) -> Dict[str, Any]:
        payload = {
            "persona_type": persona_type,
            "findings": findings,
            "risk": risk,
            "draft_plan": draft_plan,
            "resources": resources,
        }
        events = run_text_agent(
            agent=specialist_agent,
            app_name="NuMeRemoteSpecialistClient",
            user_id="care-coordinator",
            session_id=f"{persona_type}-{uuid4().hex}",
            message=json.dumps(payload, sort_keys=True),
        )

        response_text = ""
        response_error = ""
        for event in events:
            error_message = str(getattr(event, "error_message", "") or "").strip()
            if error_message:
                response_error = error_message

            content = getattr(event, "content", None)
            if event.author != specialist_agent.name or not content or not content.parts:
                continue

            text_parts = [str(getattr(part, "text", "") or "").strip() for part in content.parts]
            candidate = "\n".join([item for item in text_parts if item]).strip()
            if candidate:
                response_text = candidate

        if not response_text:
            raise RuntimeError(
                f"Remote specialist call failed for {specialist_agent.name}: "
                f"{response_error or 'Remote specialist returned no text response.'}"
            )

        try:
            body = extract_json_object(response_text)
            body.setdefault("generation_mode", "llm")
            body.setdefault("generation_error", "")
            return SpecialistResult(
                enriched_context=str(body.get("enriched_context", "")).strip(),
                resources=sorted(
                    {
                        str(item).strip()
                        for item in body.get("resources", [])
                        if str(item).strip()
                    }
                ),
                intervention_adjustments=[
                    str(item).strip()
                    for item in body.get("intervention_adjustments", [])
                    if str(item).strip()
                ],
                burnout_risk_flag=body.get("burnout_risk_flag"),
                escalation_recommendation=body.get("escalation_recommendation"),
                generation_mode=str(body.get("generation_mode", "llm")).strip() or "llm",
                generation_error=str(body.get("generation_error", "")).strip(),
            ).model_dump()
        except Exception as exc:
            raise RuntimeError(
                f"Remote specialist returned invalid JSON payload for "
                f"{specialist_agent.name}: {type(exc).__name__}: {exc}"
            ) from exc

    @staticmethod
    def _merge_plan_patch(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
        merged = deepcopy(base)
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = CareCoordinatorPipeline._merge_plan_patch(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged

    def _after_parallel_phase(self, callback_context: Any) -> None:
        state = callback_context.state
        persona_type = str(state.get("persona_type", "older_adult"))
        signal_result = deepcopy(state.get("signal_interpretation", {}))
        risk_result = deepcopy(state.get("risk_assessment", {}))
        draft_plan = deepcopy(state.get("intervention_plan", {}))
        state["intervention_planning_trace"] = deepcopy(draft_plan)

        specialist_name, specialist_agent_type, specialist_result = self._run_specialist(
            persona_type=persona_type,
            findings=signal_result.get("findings", []),
            risk=risk_result,
            draft_plan=draft_plan,
            specialist_agent=self._specialist_for(persona_type),
        )

        if specialist_result["resources"]:
            draft_plan["resources"] = sorted(
                set(draft_plan.get("resources", []) + specialist_result["resources"])
            )
        if specialist_result["intervention_adjustments"]:
            draft_plan["notes"] = (
                draft_plan.get("notes", "")
                + " "
                + " ".join(specialist_result["intervention_adjustments"])
            ).strip()

        state["intervention_plan"] = draft_plan
        state["specialist_name"] = specialist_name
        state["specialist_agent_type"] = specialist_agent_type.value
        state["specialist_result"] = specialist_result

    def _load_run_context(self, *, user_id: str, scenario: str) -> Dict[str, Any]:
        inferred_persona = "student" if scenario == "stressed_student" else (
            "caregiver" if scenario == "exhausted_caregiver" else "older_adult"
        )
        profile = self.tool_provider.get_user_profile(persona_type=inferred_persona)
        persona_type = profile.get("persona_type", inferred_persona)
        raw_signals = self.tool_provider.get_recent_signals(scenario=scenario)
        signals = {item["signal_type"]: item["value"] for item in raw_signals}
        resources = [item["title"] for item in self.tool_provider.get_resources(persona_type)]
        return {
            "run_user_id": int(user_id),
            "profile": profile,
            "persona_type": persona_type,
            "signals": signals,
            "resources": resources,
            "scenario": scenario,
        }

    def _build_initial_state(self, context: Dict[str, Any]) -> Dict[str, Any]:
        profile = context["profile"]
        return {
            "persona_type": context["persona_type"],
            "profile": deepcopy(profile),
            "goal": profile["goal"],
            "dietary_style": profile["dietary_style"],
            "allergies": list(profile["allergies"]),
            "signals": deepcopy(context["signals"]),
            "resources": list(context["resources"]),
            "validation_iterations": [],
            "validation_plan_changed": False,
        }

    def _finalize_run(
        self,
        *,
        user_id: str,
        run_id: int,
        context: Dict[str, Any],
        signal_result: Dict[str, Any],
        risk_result: Dict[str, Any],
        parallel_intervention_output: Dict[str, Any],
        draft_plan: Dict[str, Any],
        specialist_name: str,
        specialist_agent_type: AgentType,
        specialist_result: Dict[str, Any],
        empathy_result: Dict[str, Any],
        validation_result: Dict[str, Any],
        validation_iterations: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        recorder = TraceRecorder(run_id=run_id, tool_provider=self.tool_provider)
        profile = context["profile"]
        persona_type = context["persona_type"]
        signals = context["signals"]
        scenario = context["scenario"]
        run_user_id = context["run_user_id"]

        parallel_outputs = {
            "signal_interpretation": signal_result,
            "risk_stratification": risk_result,
            "intervention_planning": parallel_intervention_output,
        }
        for name, output in parallel_outputs.items():
            recorder.log(
                agent_name=name,
                agent_type=AgentType.parallel,
                input_payload={"user_id": user_id, "scenario": scenario},
                output_payload=output,
            )
        recorder.log(
            agent_name=specialist_name,
            agent_type=specialist_agent_type,
            input_payload={"persona_type": persona_type, "risk_level": risk_result["risk_level"]},
            output_payload=specialist_result,
        )
        recorder.log(
            agent_name="EmpathyCheckin",
            agent_type=AgentType.local,
            input_payload={
                "persona_type": persona_type,
                "risk_level": risk_result["risk_level"],
                "summary": signal_result["summary"],
            },
            output_payload=empathy_result,
        )
        for entry in validation_iterations:
            recorder.log(
                agent_name="ValidationLoop",
                agent_type=AgentType.loop,
                input_payload=entry["input"],
                output_payload=entry["output"],
                iteration=entry["iteration"],
            )
        if validation_result.get("revised_plan") is not None:
            draft_plan = self._merge_plan_patch(draft_plan, validation_result["revised_plan"])

        final_plan = FinalPlan(
            meal_suggestion=draft_plan["meal_suggestion"]["description"],
            activity_suggestion=draft_plan["activity_suggestion"]["description"],
            wellness_action=draft_plan["wellness_action"]["description"],
            empathy_message=empathy_result["empathy_message"],
            risk_level=risk_result["risk_level"],
            generation_mode=draft_plan.get("generation_mode", "fallback"),
            generation_error=draft_plan.get("generation_error", ""),
            resources=draft_plan.get("resources", []),
            notes=draft_plan.get("notes", ""),
        ).model_dump()

        intervention_payload = {
            "user_id": run_user_id,
            "run_id": run_id,
            "meal_suggestion": final_plan["meal_suggestion"],
            "activity_suggestion": final_plan["activity_suggestion"],
            "wellness_action": final_plan["wellness_action"],
            "empathy_message": final_plan["empathy_message"],
            "meal_constraints": draft_plan.get("meal_constraints", []),
        }
        intervention_record = self.tool_provider.create_intervention(intervention_payload)
        case_record = None
        if risk_result["risk_level"] in {"moderate", "high", "critical"}:
            case_record = self.tool_provider.create_case(
                {
                    "user_id": run_user_id,
                    "run_id": run_id,
                    "risk_level": risk_result["risk_level"],
                }
            )
        notification_record = self.tool_provider.send_notification(
            {
                "user_id": run_user_id,
                "type": "intervention_ready",
                "content": empathy_result["empathy_message"],
            }
        )
        audit_record = self.tool_provider.persist_audit(
            {
                "action": "agent_completed",
                "entity_type": "agent_run",
                "entity_id": str(run_id),
                "metadata": {
                    "risk_level": risk_result["risk_level"],
                    "scenario": scenario,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                },
            }
        )
        return {
            "run_id": run_id,
            "user_id": user_id,
            "persona_type": persona_type,
            "profile": profile,
            "signals": signals,
            "signal_interpretation": signal_result,
            "risk_assessment": risk_result,
            "specialist_result": specialist_result,
            "validation": validation_result,
            "final_plan": final_plan,
            "case_record": case_record,
            "intervention_record": intervention_record,
            "notification_record": notification_record,
            "audit_record": audit_record,
            "trace_messages": recorder.messages,
            "adk_prompt": self.prompt,
        }

    def _run_adk(self, *, user_id: str, scenario: str, run_id: int) -> Dict[str, Any]:
        context = self._load_run_context(user_id=user_id, scenario=scenario)
        session_state, _events = run_in_memory_agent(
            agent=self.definition,
            app_name="NuMeCareCoordinator",
            user_id=user_id,
            session_id=f"run-{run_id}",
            initial_state=self._build_initial_state(context),
        )
        del _events
        return self._finalize_run(
            user_id=user_id,
            run_id=run_id,
            context=context,
            signal_result=deepcopy(session_state["signal_interpretation"]),
            risk_result=deepcopy(session_state["risk_assessment"]),
            parallel_intervention_output=deepcopy(
                session_state.get("intervention_planning_trace", session_state["intervention_plan"])
            ),
            draft_plan=deepcopy(session_state["intervention_plan"]),
            specialist_name=str(session_state["specialist_name"]),
            specialist_agent_type=AgentType(str(session_state["specialist_agent_type"])),
            specialist_result=deepcopy(session_state["specialist_result"]),
            empathy_result=deepcopy(session_state["empathy_result"]),
            validation_result=deepcopy(session_state["validation_result"]),
            validation_iterations=deepcopy(session_state.get("validation_iterations", [])),
        )

    def _run_legacy(self, *, user_id: str, scenario: str, run_id: int = 1) -> Dict[str, Any]:
        context = self._load_run_context(user_id=user_id, scenario=scenario)
        profile = context["profile"]
        persona_type = context["persona_type"]
        signals = context["signals"]
        resources = context["resources"]
        parallel_outputs = execute_parallel(
            {
                "signal_interpretation": lambda: self.signal_agent.run(signals=signals),
                "risk_stratification": lambda: self.risk_agent.run(
                    persona_type=persona_type,
                    signals=signals,
                ),
                "intervention_planning": lambda: self.intervention_agent.run(
                    persona_type=persona_type,
                    goal=profile["goal"],
                    dietary_style=profile["dietary_style"],
                    allergies=profile["allergies"],
                    resources=resources,
                    signals=signals,
                ),
            }
        )
        signal_result = parallel_outputs["signal_interpretation"]
        risk_result = parallel_outputs["risk_stratification"]
        draft_plan = parallel_outputs["intervention_planning"]
        parallel_intervention_output = deepcopy(draft_plan)
        specialist_name, specialist_agent_type, specialist_result = self._run_specialist(
            persona_type=persona_type,
            findings=signal_result["findings"],
            risk=risk_result,
            draft_plan=draft_plan,
            specialist_agent=self._specialist_for(persona_type),
        )
        if specialist_result["resources"]:
            draft_plan["resources"] = sorted(
                set(draft_plan.get("resources", []) + specialist_result["resources"])
            )
        if specialist_result["intervention_adjustments"]:
            draft_plan["notes"] = (
                draft_plan.get("notes", "")
                + " "
                + " ".join(specialist_result["intervention_adjustments"])
            ).strip()
        empathy_result = self.empathy_agent.run(
            risk_level=risk_result["risk_level"],
            persona_type=persona_type,
            signal_summary=signal_result["summary"],
        )
        validation_result, validation_iterations = self.validation_loop.validate(
            findings=signal_result["findings"],
            risk_level=risk_result["risk_level"],
            intervention_plan=draft_plan,
            empathy_message=empathy_result["empathy_message"],
            user_profile=profile,
        )
        return self._finalize_run(
            user_id=user_id,
            run_id=run_id,
            context=context,
            signal_result=signal_result,
            risk_result=risk_result,
            parallel_intervention_output=parallel_intervention_output,
            draft_plan=draft_plan,
            specialist_name=specialist_name,
            specialist_agent_type=specialist_agent_type,
            specialist_result=specialist_result,
            empathy_result=empathy_result,
            validation_result=validation_result,
            validation_iterations=validation_iterations,
        )

    def run(self, *, user_id: str, scenario: str, run_id: int = 1) -> Dict[str, Any]:
        if self.use_adk_runtime:
            return self._run_adk(user_id=user_id, scenario=scenario, run_id=run_id)
        return self._run_legacy(user_id=user_id, scenario=scenario, run_id=run_id)
