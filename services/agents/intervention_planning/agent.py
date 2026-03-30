from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

try:
    from services.agents.adk_compat import LlmAgent
    from services.agents.llm_utils import OpenAIJsonClient
    from services.agents.prompts import INTERVENTION_PLANNING_PROMPT
    from services.agents.schemas import (
        ActivitySuggestion,
        InterventionDraft,
        MealSuggestion,
        WellnessAction,
    )
except ImportError:
    from adk_compat import LlmAgent
    from llm_utils import OpenAIJsonClient
    from prompts import INTERVENTION_PLANNING_PROMPT
    from schemas import ActivitySuggestion, InterventionDraft, MealSuggestion, WellnessAction


class InterventionPlanningAgent:
    def __init__(self) -> None:
        self.definition = LlmAgent(
            name="InterventionPlanning",
            instruction=INTERVENTION_PLANNING_PROMPT,
        )
        self._llm = OpenAIJsonClient()
        self._last_generation_error = ""

    def run(
        self,
        *,
        persona_type: str,
        goal: str,
        dietary_style: str,
        allergies: List[str],
        resources: List[str],
        findings: Optional[List[Dict[str, Any]]] = None,
        risk_level: Optional[str] = None,
        signals: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, object]:
        findings = findings or []
        signals = signals or {}
        risk_level = risk_level or self._derive_risk_level(signals)
        llm_plan = self._generate_with_llm(
            persona_type=persona_type,
            goal=goal,
            dietary_style=dietary_style,
            allergies=allergies,
            resources=resources,
            findings=findings,
            risk_level=risk_level,
            signals=signals,
        )
        if llm_plan:
            return llm_plan

        low_intensity = risk_level in {"moderate", "high", "critical"}
        meal_title = "Steady Energy Bowl" if dietary_style != "none" else "Simple Nourishing Meal"
        meal = MealSuggestion(
            title=meal_title,
            description="A balanced, quick-prep meal with protein, carbs, and hydration support.",
            rationale=f"Supports {goal} without adding planning overhead and respects {dietary_style}.",
        )
        activity = ActivitySuggestion(
            title="Reset Walk" if persona_type == "student" else "Gentle Reset",
            description="A brief movement break focused on recovery rather than performance.",
            duration_minutes=10 if low_intensity else 20,
            intensity="low" if low_intensity else "moderate",
            rationale="High strain signals call for a short, manageable activity instead of an intense workout.",
        )
        wellness = WellnessAction(
            title="Two-Minute Check-In",
            description="Pause for a short breathing or grounding exercise and reassess later today.",
            rationale="Adds a low-friction regulation step that fits a high-stress day.",
        )
        notes = (
            f"Plan tuned for {persona_type}; allergies considered: "
            f"{', '.join(allergies) if allergies else 'none'}."
        )
        meal_constraints = self._derive_meal_constraints(
            dietary_style=dietary_style,
            allergies=allergies,
            risk_level=risk_level,
            signals=signals,
        )
        return InterventionDraft(
            meal_suggestion=meal,
            activity_suggestion=activity,
            wellness_action=wellness,
            generation_mode="fallback",
            generation_error=self._last_generation_error,
            resources=resources,
            notes=notes,
            meal_constraints=meal_constraints,
        ).model_dump()

    @staticmethod
    def _derive_meal_constraints(
        *,
        dietary_style: str,
        allergies: List[str],
        risk_level: str,
        signals: Dict[str, Any],
    ) -> List[str]:
        constraints: list[str] = []
        if dietary_style and dietary_style not in {"none", ""}:
            constraints.append(dietary_style)
        for allergy in allergies:
            constraints.append(f"avoid_{allergy.lower().replace(' ', '_')}")
        stress = float(signals.get("stress_level", 0) or 0)
        sleep_h = float(signals.get("sleep_hours", 7) or 7)
        steps = int(signals.get("steps", 0) or 0)
        if risk_level in {"high", "critical"} or stress >= 7:
            constraints.append("comforting")
            constraints.append("low_prep")
        if sleep_h < 6:
            constraints.append("hydration_support")
            constraints.append("high_protein")
        if steps > 10000:
            constraints.append("high_calorie")
        elif steps < 3000 and steps > 0:
            constraints.append("light")
        return sorted(set(constraints))

    @staticmethod
    def _derive_risk_level(signals: Dict[str, Any]) -> str:
        stress_level = float(signals.get("stress_level", 3) or 3)
        sleep_hours = float(signals.get("sleep_hours", 7) or 7)
        if stress_level >= 8 and sleep_hours < 5.5:
            return "high"
        if stress_level >= 6 or sleep_hours < 6:
            return "moderate"
        return "low"

    def _generate_with_llm(
        self,
        *,
        persona_type: str,
        goal: str,
        dietary_style: str,
        allergies: List[str],
        resources: List[str],
        findings: List[Dict[str, Any]],
        risk_level: str,
        signals: Dict[str, Any],
    ) -> Optional[Dict[str, object]]:
        self._last_generation_error = ""

        try:
            prompt = self._build_prompt(
                persona_type=persona_type,
                goal=goal,
                dietary_style=dietary_style,
                allergies=allergies,
                resources=resources,
                findings=findings,
                risk_level=risk_level,
                signals=signals,
            )
            result = self._llm.generate_json(prompt)
            if not result.payload:
                self._last_generation_error = result.error
                return None
            return self._coerce_plan(
                result.payload,
                resources=resources,
                persona_type=persona_type,
            )
        except Exception as exc:
            self._last_generation_error = f"{type(exc).__name__}: {exc}"
            return None

    def _build_prompt(
        self,
        *,
        persona_type: str,
        goal: str,
        dietary_style: str,
        allergies: List[str],
        resources: List[str],
        findings: List[Dict[str, Any]],
        risk_level: str,
        signals: Dict[str, Any],
    ) -> str:
        response_schema = {
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
            "meal_constraints": ["tag1", "tag2"],
            "resources": ["resource title"],
            "notes": "brief planning notes",
        }
        payload = {
            "persona_type": persona_type,
            "goal": goal,
            "dietary_style": dietary_style,
            "allergies": allergies,
            "resources": resources,
            "findings": findings,
            "risk_level": risk_level,
            "signals": signals,
        }
        return (
            f"{INTERVENTION_PLANNING_PROMPT}\n\n"
            "Return only valid JSON with no markdown fences.\n"
            "Keep recommendations practical, safe, and specific.\n"
            "Do not recommend medical treatment or crisis claims.\n"
            f"Response schema:\n{json.dumps(response_schema, indent=2)}\n\n"
            f"Input:\n{json.dumps(payload, indent=2)}"
        )

    @staticmethod
    def _coerce_plan(
        payload: Dict[str, Any],
        *,
        resources: List[str],
        persona_type: str,
    ) -> Dict[str, object]:
        meal_payload = payload.get("meal_suggestion", {})
        activity_payload = payload.get("activity_suggestion", {})
        wellness_payload = payload.get("wellness_action", {})
        intensity = str(activity_payload.get("intensity", "low")).lower()
        if intensity not in {"very_low", "low", "moderate"}:
            intensity = "low"

        model_resources = payload.get("resources") or []
        merged_resources = sorted(
            {
                str(item).strip()
                for item in [*resources, *model_resources]
                if str(item).strip()
            }
        )
        notes = str(payload.get("notes", "")).strip() or f"Plan tuned for {persona_type}."
        meal_constraints = sorted(
            {str(c).strip().lower() for c in (payload.get("meal_constraints") or []) if str(c).strip()}
        )

        return InterventionDraft(
            meal_suggestion=MealSuggestion(
                title=str(meal_payload.get("title", "Supportive Meal")).strip(),
                description=str(meal_payload.get("description", "")).strip(),
                rationale=str(meal_payload.get("rationale", "")).strip(),
            ),
            activity_suggestion=ActivitySuggestion(
                title=str(activity_payload.get("title", "Gentle Reset")).strip(),
                description=str(activity_payload.get("description", "")).strip(),
                duration_minutes=max(5, min(int(activity_payload.get("duration_minutes", 10)), 60)),
                intensity=intensity,
                rationale=str(activity_payload.get("rationale", "")).strip(),
            ),
            wellness_action=WellnessAction(
                title=str(wellness_payload.get("title", "Check-In")).strip(),
                description=str(wellness_payload.get("description", "")).strip(),
                rationale=str(wellness_payload.get("rationale", "")).strip(),
            ),
            generation_mode="llm",
            generation_error="",
            resources=merged_resources,
            notes=notes,
            meal_constraints=meal_constraints,
        ).model_dump()
