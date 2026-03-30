from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import httpx
from typing import Any, Dict, List

try:
    from services.agents.adk_compat import ParallelAgent, RemoteA2aAgent, SequentialAgent
    from services.agents.config import Settings
    from services.agents.llm_utils import OpenAIJsonClient, build_json_prompt
    from services.agents.prompts import CARE_COORDINATOR_PROMPT
    from services.agents.runtime import AgentType, TraceRecorder, execute_parallel
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
    from llm_utils import OpenAIJsonClient, build_json_prompt
    from prompts import CARE_COORDINATOR_PROMPT
    from runtime import AgentType, TraceRecorder, execute_parallel
    from schemas import FinalPlan, SpecialistResult
    from tooling import ToolProvider

    from empathy_checkin import EmpathyCheckinAgent
    from intervention_planning import InterventionPlanningAgent
    from risk_stratification import RiskStratificationAgent
    from signal_interpretation import SignalInterpretationAgent
    from validation_loop import ValidationLoopAgent


class CareCoordinatorPipeline:
    def __init__(self, settings: Settings, tool_provider: ToolProvider) -> None:
        self.settings = settings
        self.tool_provider = tool_provider
        self.signal_agent = SignalInterpretationAgent()
        self.risk_agent = RiskStratificationAgent()
        self.intervention_agent = InterventionPlanningAgent()
        self.empathy_agent = EmpathyCheckinAgent()
        self.validation_loop = ValidationLoopAgent()
        self.parallel_phase = ParallelAgent(
            name="CareCoordinatorParallelPhase",
            sub_agents=[
                self.signal_agent.definition,
                self.risk_agent.definition,
                self.intervention_agent.definition,
            ],
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

    def _specialist_for(self, persona_type: str) -> RemoteA2aAgent | None:
        if persona_type == "student":
            return RemoteA2aAgent(
                name="StudentSupportSpecialist",
                endpoint=self.settings.student_specialist_url,
                description="Student support remote specialist",
            )
        if persona_type == "caregiver":
            return RemoteA2aAgent(
                name="CaregiverBurnoutSpecialist",
                endpoint=self.settings.caregiver_specialist_url,
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
        payload = {
            "persona_type": persona_type,
            "findings": findings,
            "risk": risk,
            "draft_plan": draft_plan,
            "resources": resources,
        }
        last_exc: Exception | None = None
        for _ in range(2):
            try:
                with httpx.Client(timeout=20.0) as client:
                    response = client.post(f"{specialist_agent.endpoint.rstrip('/')}/invoke", json=payload)
                    response.raise_for_status()
                    body = response.json()
                    body.setdefault("generation_mode", "llm")
                    body.setdefault("generation_error", "")
                    return body
            except httpx.HTTPError as exc:
                last_exc = exc

        raise RuntimeError(
            f"Remote specialist call failed for {specialist_agent.name}: {last_exc}"
        )

    @staticmethod
    def _merge_plan_patch(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
        merged = deepcopy(base)
        for key, value in patch.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = CareCoordinatorPipeline._merge_plan_patch(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged

    def run(self, *, user_id: str, scenario: str, run_id: int = 1) -> Dict[str, Any]:
        recorder = TraceRecorder(run_id=run_id, tool_provider=self.tool_provider)
        run_user_id = int(user_id)
        inferred_persona = "student" if scenario == "stressed_student" else (
            "caregiver" if scenario == "exhausted_caregiver" else "older_adult"
        )
        profile = self.tool_provider.get_user_profile(persona_type=inferred_persona)
        persona_type = profile.get("persona_type", inferred_persona)
        raw_signals = self.tool_provider.get_recent_signals(scenario=scenario)
        signals = {item["signal_type"]: item["value"] for item in raw_signals}

        resources = [item["title"] for item in self.tool_provider.get_resources(persona_type)]
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
        for name, output in parallel_outputs.items():
            recorder.log(
                agent_name=name,
                agent_type=AgentType.parallel,
                input_payload={"user_id": user_id, "scenario": scenario},
                output_payload=output,
            )

        signal_result = parallel_outputs["signal_interpretation"]
        risk_result = parallel_outputs["risk_stratification"]
        draft_plan = parallel_outputs["intervention_planning"]

        specialist_agent = self._specialist_for(persona_type)
        specialist_name, specialist_agent_type, specialist_result = self._run_specialist(
            persona_type=persona_type,
            findings=signal_result["findings"],
            risk=risk_result,
            draft_plan=draft_plan,
            specialist_agent=specialist_agent,
        )
        recorder.log(
            agent_name=specialist_name,
            agent_type=specialist_agent_type,
            input_payload={"persona_type": persona_type, "risk_level": risk_result["risk_level"]},
            output_payload=specialist_result,
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

        validation_result, validation_iterations = self.validation_loop.validate(
            findings=signal_result["findings"],
            risk_level=risk_result["risk_level"],
            intervention_plan=draft_plan,
            empathy_message=empathy_result["empathy_message"],
            user_profile=profile,
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
