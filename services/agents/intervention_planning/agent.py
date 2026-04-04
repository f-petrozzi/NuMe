from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Mapping, Optional

API_ROOT = Path(__file__).resolve().parents[3] / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from recipe_ranking import build_recipe_ranking_context, derive_meal_constraints, summarize_recipe_preferences

try:
    from services.agents.adk_compat import LlmAgent
    from services.agents.llm_utils import (
        DEFAULT_OPENAI_MODEL,
        OpenAIJsonClient,
        extract_json_object,
    )
    from services.agents.prompts import INTERVENTION_PLANNING_PROMPT
    from services.agents.runtime import build_stateful_llm_agent
    from services.agents.schemas import (
        ActivitySuggestion,
        InterventionDraft,
        MealSuggestion,
        WellnessAction,
    )
except ImportError:
    from adk_compat import LlmAgent
    from llm_utils import DEFAULT_OPENAI_MODEL, OpenAIJsonClient, extract_json_object
    from prompts import INTERVENTION_PLANNING_PROMPT
    from runtime import build_stateful_llm_agent
    from schemas import ActivitySuggestion, InterventionDraft, MealSuggestion, WellnessAction


class InterventionPlanningAgent:
    state_key = "intervention_plan"

    def __init__(self, model: Any = DEFAULT_OPENAI_MODEL) -> None:
        self.definition = build_stateful_llm_agent(
            name="InterventionPlanning",
            model=model,
            instruction_builder=lambda state: self._build_prompt_from_state(state),
            state_key=self.state_key,
            parse_output=self._parse_response_text,
            fallback_output=lambda state, error: self._fallback_from_state(state, error),
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
        accessibility: Optional[Dict[str, Any]] = None,
        findings: Optional[List[Dict[str, Any]]] = None,
        risk_level: Optional[str] = None,
        signals: Optional[Dict[str, Any]] = None,
        dynamic_state: Optional[Dict[str, Any]] = None,
        archetype_scores: Optional[Dict[str, Any]] = None,
        feature_windows: Optional[Dict[str, Any]] = None,
        recent_checkins: Optional[List[Dict[str, Any]]] = None,
        calorie_summary: Optional[Dict[str, Any]] = None,
        recipe_history: Optional[Dict[str, Any]] = None,
        intervention_history: Optional[Dict[str, Any]] = None,
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
            accessibility=accessibility or {},
            findings=findings,
            risk_level=risk_level,
            signals=signals,
            dynamic_state=dynamic_state or {},
            archetype_scores=archetype_scores or {},
            feature_windows=feature_windows or {},
            recent_checkins=recent_checkins or [],
            calorie_summary=calorie_summary or {},
            recipe_history=recipe_history or {},
            intervention_history=intervention_history or {},
        )
        if llm_plan:
            return llm_plan

        return self.fallback_result(
            persona_type=persona_type,
            goal=goal,
            dietary_style=dietary_style,
            allergies=allergies,
            resources=resources,
            accessibility=accessibility or {},
            risk_level=risk_level,
            signals=signals,
            dynamic_state=dynamic_state or {},
            archetype_scores=archetype_scores or {},
            feature_windows=feature_windows or {},
            recent_checkins=recent_checkins or [],
            calorie_summary=calorie_summary or {},
            recipe_history=recipe_history or {},
            intervention_history=intervention_history or {},
            generation_error=self._last_generation_error,
        )

    def _build_prompt_from_state(self, state: Mapping[str, Any]) -> str:
        signal_result = state.get("signal_interpretation", {}) or {}
        risk_result = state.get("risk_assessment", {}) or {}
        resources = list(state.get("resources", []))
        return self._build_prompt(
            persona_type=str(state.get("persona_type", "older_adult")),
            goal=str(state.get("goal", "")),
            dietary_style=str(state.get("dietary_style", "")),
            allergies=list(state.get("allergies", [])),
            resources=resources,
            accessibility=dict((state.get("profile", {}) or {}).get("accessibility") or {}),
            findings=list(signal_result.get("findings", [])),
            risk_level=str(
                risk_result.get("risk_level")
                or self._derive_risk_level(dict(state.get("signals", {})))
            ),
            signals=dict(state.get("signals", {})),
            dynamic_state=dict(state.get("dynamic_state", {})),
            archetype_scores=dict(state.get("archetype_scores", {})),
            feature_windows=dict(state.get("feature_windows", {})),
            recent_checkins=list(state.get("recent_checkins", [])),
            calorie_summary=dict(state.get("calorie_summary", {})),
            recipe_history=dict(state.get("recipe_history", {})),
            intervention_history=dict(state.get("intervention_history", {})),
        )

    def _parse_response_text(
        self,
        text: str,
        state: Mapping[str, Any],
    ) -> Dict[str, object]:
        return self._coerce_plan(
            extract_json_object(text),
            resources=list(state.get("resources", [])),
            persona_type=str(state.get("persona_type", "older_adult")),
        )

    def _fallback_from_state(
        self,
        state: Mapping[str, Any],
        generation_error: str,
    ) -> Dict[str, object]:
        risk_result = state.get("risk_assessment", {}) or {}
        return self.fallback_result(
            persona_type=str(state.get("persona_type", "older_adult")),
            goal=str(state.get("goal", "")),
            dietary_style=str(state.get("dietary_style", "")),
            allergies=list(state.get("allergies", [])),
            resources=list(state.get("resources", [])),
            accessibility=dict((state.get("profile", {}) or {}).get("accessibility") or {}),
            risk_level=str(
                risk_result.get("risk_level")
                or self._derive_risk_level(dict(state.get("signals", {})))
            ),
            signals=dict(state.get("signals", {})),
            dynamic_state=dict(state.get("dynamic_state", {})),
            archetype_scores=dict(state.get("archetype_scores", {})),
            feature_windows=dict(state.get("feature_windows", {})),
            recent_checkins=list(state.get("recent_checkins", [])),
            calorie_summary=dict(state.get("calorie_summary", {})),
            recipe_history=dict(state.get("recipe_history", {})),
            intervention_history=dict(state.get("intervention_history", {})),
            generation_error=generation_error,
        )

    def fallback_result(
        self,
        *,
        persona_type: str,
        goal: str,
        dietary_style: str,
        allergies: List[str],
        resources: List[str],
        accessibility: Dict[str, Any],
        risk_level: str,
        signals: Dict[str, Any],
        dynamic_state: Dict[str, Any],
        archetype_scores: Dict[str, Any],
        feature_windows: Dict[str, Any],
        recent_checkins: List[Dict[str, Any]],
        calorie_summary: Dict[str, Any],
        recipe_history: Dict[str, Any],
        intervention_history: Dict[str, Any],
        generation_error: str = "",
    ) -> Dict[str, object]:

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
            persona_type=persona_type,
            goal=goal,
            dietary_style=dietary_style,
            allergies=allergies,
            accessibility=accessibility,
            risk_level=risk_level,
            signals=signals,
            dynamic_state=dynamic_state,
            archetype_scores=archetype_scores,
            feature_windows=feature_windows,
            recent_checkins=recent_checkins,
            calorie_summary=calorie_summary,
            recipe_history=recipe_history,
            intervention_history=intervention_history,
        )
        return InterventionDraft(
            meal_suggestion=meal,
            activity_suggestion=activity,
            wellness_action=wellness,
            generation_mode="fallback",
            generation_error=generation_error,
            resources=resources,
            notes=notes,
            meal_constraints=meal_constraints,
        ).model_dump()

    @staticmethod
    def _derive_meal_constraints(
        *,
        persona_type: str,
        goal: str,
        dietary_style: str,
        allergies: List[str],
        accessibility: Dict[str, Any],
        risk_level: str,
        signals: Dict[str, Any],
        dynamic_state: Dict[str, Any],
        archetype_scores: Dict[str, Any],
        feature_windows: Dict[str, Any],
        recent_checkins: List[Dict[str, Any]],
        calorie_summary: Dict[str, Any],
        recipe_history: Dict[str, Any],
        intervention_history: Dict[str, Any],
    ) -> List[str]:
        carried_constraints: list[str] = []
        if risk_level in {"high", "critical"}:
            carried_constraints.extend(["comforting", "low_prep"])

        context = build_recipe_ranking_context(
            profile={
                "persona_type": persona_type,
                "goal": goal,
                "dietary_style": dietary_style,
                "allergies": allergies,
                "accessibility": accessibility,
            },
            dynamic_state=dynamic_state,
            archetype_scores=archetype_scores,
            feature_windows=feature_windows,
            recent_checkins=recent_checkins,
            calorie_summary=calorie_summary,
            recipe_history=recipe_history,
            intervention_history=intervention_history,
            signals=signals,
            carried_constraints=carried_constraints,
        )
        return derive_meal_constraints(context)

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
        accessibility: Dict[str, Any],
        findings: List[Dict[str, Any]],
        risk_level: str,
        signals: Dict[str, Any],
        dynamic_state: Dict[str, Any],
        archetype_scores: Dict[str, Any],
        feature_windows: Dict[str, Any],
        recent_checkins: List[Dict[str, Any]],
        calorie_summary: Dict[str, Any],
        recipe_history: Dict[str, Any],
        intervention_history: Dict[str, Any],
    ) -> Optional[Dict[str, object]]:
        self._last_generation_error = ""

        try:
            prompt = self._build_prompt(
                persona_type=persona_type,
                goal=goal,
                dietary_style=dietary_style,
                allergies=allergies,
                resources=resources,
                accessibility=accessibility,
                findings=findings,
                risk_level=risk_level,
                signals=signals,
                dynamic_state=dynamic_state,
                archetype_scores=archetype_scores,
                feature_windows=feature_windows,
                recent_checkins=recent_checkins,
                calorie_summary=calorie_summary,
                recipe_history=recipe_history,
                intervention_history=intervention_history,
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
        accessibility: Dict[str, Any],
        findings: List[Dict[str, Any]],
        risk_level: str,
        signals: Dict[str, Any],
        dynamic_state: Dict[str, Any],
        archetype_scores: Dict[str, Any],
        feature_windows: Dict[str, Any],
        recent_checkins: List[Dict[str, Any]],
        calorie_summary: Dict[str, Any],
        recipe_history: Dict[str, Any],
        intervention_history: Dict[str, Any],
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
        meal_ranking_context = summarize_recipe_preferences(
            build_recipe_ranking_context(
                profile={
                    "persona_type": persona_type,
                    "goal": goal,
                    "dietary_style": dietary_style,
                    "allergies": allergies,
                    "accessibility": accessibility,
                },
                dynamic_state=dynamic_state,
                archetype_scores=archetype_scores,
                feature_windows=feature_windows,
                recent_checkins=recent_checkins,
                calorie_summary=calorie_summary,
                recipe_history=recipe_history,
                intervention_history=intervention_history,
                signals=signals,
                carried_constraints=["comforting", "low_prep"] if risk_level in {"high", "critical"} else [],
            )
        )
        payload = {
            "persona_type": persona_type,
            "goal": goal,
            "dietary_style": dietary_style,
            "allergies": allergies,
            "resources": resources,
            "findings": findings,
            "risk_level": risk_level,
            "signals": signals,
            "dynamic_state": dynamic_state,
            "archetype_scores": archetype_scores,
            "meal_ranking_context": meal_ranking_context,
        }
        return (
            f"{INTERVENTION_PLANNING_PROMPT}\n\n"
            "Return only valid JSON with no markdown fences.\n"
            "Keep recommendations practical, safe, and specific.\n"
            "Do not recommend medical treatment or crisis claims.\n"
            "Use meal_ranking_context as deterministic guidance for meal fit.\n"
            "Keep meal_constraints aligned with meal_ranking_context.derived_constraints.\n"
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
