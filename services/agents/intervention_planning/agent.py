from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence

API_ROOT = Path(__file__).resolve().parents[3] / "apps" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from catalog_ranking import (
    DEFAULT_ACTIVITY_TEMPLATES,
    DEFAULT_WELLNESS_TEMPLATES,
    RankedCatalogItem,
    build_catalog_ranking_context,
    rank_activity_templates,
    rank_wellness_templates,
)
from recipe_ranking import build_recipe_ranking_context, derive_meal_constraints, rank_recipes, summarize_recipe_preferences

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


@dataclass(frozen=True)
class _RecipeTemplateCandidate:
    id: int
    title: str
    description: str
    tags: Sequence[str]
    ingredients: Sequence[Any]
    prep_effort: str | None
    prep_minutes: int | None
    cook_minutes: int | None
    calories: int | None
    protein_grams: float | None


_FALLBACK_RECIPE_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "title": "Nut-Free Chickpea Toast",
        "description": "A simple savory option with protein and low prep for stressful days.",
        "tags": ["high_protein", "low_prep", "avoid_nuts", "light"],
        "ingredients": [{"name": "Chickpeas"}],
        "prep_effort": "low",
        "prep_minutes": 10,
        "cook_minutes": 5,
        "calories": 310,
        "protein_grams": 13.0,
    },
    {
        "title": "Comforting Lentil Rice Cup",
        "description": "A warm, gentle meal built for high-stress days when energy is low.",
        "tags": ["comforting", "low_prep", "light", "vegetarian"],
        "ingredients": [{"name": "Lentils"}],
        "prep_effort": "low",
        "prep_minutes": 5,
        "cook_minutes": 12,
        "calories": 360,
        "protein_grams": 15.0,
    },
    {
        "title": "Hydration Citrus Oats",
        "description": "Soft oats with fruit and chia for recovery after poor sleep or elevated stress.",
        "tags": ["hydration_support", "high_protein", "light", "breakfast"],
        "ingredients": [{"name": "Oats"}],
        "prep_effort": "low",
        "prep_minutes": 5,
        "cook_minutes": 10,
        "calories": 340,
        "protein_grams": 14.0,
    },
    {
        "title": "Spinach Yogurt Bowl",
        "description": "A quick, high-protein bowl with magnesium-rich greens and almost no prep.",
        "tags": ["high_protein", "low_prep", "comforting", "hydration_support"],
        "ingredients": [{"name": "Greek yogurt"}],
        "prep_effort": "low",
        "prep_minutes": 8,
        "cook_minutes": 0,
        "calories": 320,
        "protein_grams": 24.0,
    },
)


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
        planner_artifacts = self._build_planner_artifacts(
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
        llm_plan = self._generate_with_llm(
            prompt_payload=planner_artifacts["prompt_payload"],
            base_plan=planner_artifacts["draft_plan"],
            resources=resources,
            persona_type=persona_type,
        )
        if llm_plan:
            return llm_plan

        return self.fallback_result(
            base_plan=planner_artifacts["draft_plan"],
            generation_error=self._last_generation_error,
        )

    def _build_prompt_from_state(self, state: Mapping[str, Any]) -> str:
        planner_artifacts = self._planner_artifacts_from_state(state)
        return self._build_prompt(prompt_payload=planner_artifacts["prompt_payload"])

    def _parse_response_text(
        self,
        text: str,
        state: Mapping[str, Any],
    ) -> Dict[str, object]:
        planner_artifacts = self._planner_artifacts_from_state(state)
        return self._coerce_plan(
            extract_json_object(text),
            base_plan=planner_artifacts["draft_plan"],
            resources=list(state.get("resources", [])),
            persona_type=str(state.get("persona_type", "older_adult")),
        )

    def _fallback_from_state(
        self,
        state: Mapping[str, Any],
        generation_error: str,
    ) -> Dict[str, object]:
        planner_artifacts = self._planner_artifacts_from_state(state)
        return self.fallback_result(
            base_plan=planner_artifacts["draft_plan"],
            generation_error=generation_error,
        )

    def fallback_result(
        self,
        *,
        base_plan: Dict[str, Any],
        generation_error: str = "",
    ) -> Dict[str, object]:
        plan = deepcopy(base_plan)
        plan["generation_mode"] = "fallback"
        plan["generation_error"] = generation_error
        return plan

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
        prompt_payload: Dict[str, Any],
        base_plan: Dict[str, Any],
        resources: List[str],
        persona_type: str,
    ) -> Optional[Dict[str, object]]:
        self._last_generation_error = ""

        try:
            prompt = self._build_prompt(prompt_payload=prompt_payload)
            result = self._llm.generate_json(prompt)
            if not result.payload:
                self._last_generation_error = result.error
                return None
            return self._coerce_plan(
                result.payload,
                base_plan=base_plan,
                resources=resources,
                persona_type=persona_type,
            )
        except Exception as exc:
            self._last_generation_error = f"{type(exc).__name__}: {exc}"
            return None

    def _build_prompt(self, *, prompt_payload: Dict[str, Any]) -> str:
        response_schema = {
            "meal_suggestion": {
                "title": "keep the selected meal title unchanged",
                "description": "1-2 sentence meal suggestion",
                "rationale": "why this meal fits the condition",
            },
            "activity_suggestion": {
                "title": "keep the selected activity title unchanged",
                "description": "1-2 sentence activity suggestion",
                "duration_minutes": 10,
                "intensity": "very_low | low | moderate",
                "rationale": "why this activity fits the condition",
            },
            "wellness_action": {
                "title": "keep the selected wellness title unchanged",
                "description": "1-2 sentence wellness action",
                "rationale": "why this action fits the condition",
            },
            "why_chosen": {
                "meal": ["reason"],
                "activity": ["reason"],
                "wellness": ["reason"],
            },
            "alternatives_considered": [
                {"kind": "meal | activity | wellness", "title": "backup option", "rank": 2}
            ],
            "meal_constraints": ["tag1", "tag2"],
            "resources": ["resource title"],
            "notes": "brief planning notes",
        }
        return (
            f"{INTERVENTION_PLANNING_PROMPT}\n\n"
            "Return only valid JSON with no markdown fences.\n"
            "Use selected_support_plan as the fixed retrieve-rank-compose result.\n"
            "Do not change selected titles, selected template IDs, or activity duration/intensity.\n"
            "Use ranked candidate lists only as support for explanation and alternatives.\n"
            "Keep meal_constraints aligned with meal_ranking_context.derived_constraints.\n"
            f"Response schema:\n{json.dumps(response_schema, indent=2)}\n\n"
            f"Input:\n{json.dumps(prompt_payload, indent=2)}"
        )

    def _planner_artifacts_from_state(self, state: Mapping[str, Any]) -> Dict[str, Any]:
        signal_result = state.get("signal_interpretation", {}) or {}
        risk_result = state.get("risk_assessment", {}) or {}
        resources = list(state.get("resources", []))
        return self._build_planner_artifacts(
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

    def _build_planner_artifacts(
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
    ) -> Dict[str, Any]:
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
        meal_context = build_recipe_ranking_context(
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
            carried_constraints=meal_constraints,
        )
        ranked_meals = rank_recipes(list(_load_recipe_candidates()), meal_context, limit=3)
        if not ranked_meals:
            raise RuntimeError("Recipe candidate retrieval returned no results.")

        catalog_context = build_catalog_ranking_context(
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
            intervention_history=intervention_history,
            signals=signals,
            risk_level=risk_level,
        )
        ranked_activities = rank_activity_templates(DEFAULT_ACTIVITY_TEMPLATES, catalog_context, limit=3)
        ranked_wellness = rank_wellness_templates(DEFAULT_WELLNESS_TEMPLATES, catalog_context, limit=3)
        if not ranked_activities or not ranked_wellness:
            raise RuntimeError("Activity or wellness candidate retrieval returned no results.")

        selected_meal = ranked_meals[0]
        selected_activity = ranked_activities[0]
        selected_wellness = ranked_wellness[0]
        why_chosen = {
            "meal": self._meal_choice_reasons(
                ranked_item=selected_meal,
                meal_constraints=meal_constraints,
                goal=goal,
                allergies=allergies,
                dynamic_state=dynamic_state,
            ),
            "activity": self._activity_choice_reasons(
                ranked_item=selected_activity,
                goal=goal,
                risk_level=risk_level,
                dynamic_state=dynamic_state,
                accessibility=accessibility,
            ),
            "wellness": self._wellness_choice_reasons(
                ranked_item=selected_wellness,
                goal=goal,
                dynamic_state=dynamic_state,
                recent_checkins=recent_checkins,
                accessibility=accessibility,
            ),
        }
        alternatives_considered = self._build_alternatives(
            ranked_meals=ranked_meals,
            ranked_activities=ranked_activities,
            ranked_wellness=ranked_wellness,
        )
        why_changed = self._why_changed_from_previous(
            intervention_history=intervention_history,
            selected_meal_title=selected_meal.recipe.title,
            selected_activity_title=self._template_text(selected_activity.template, "title"),
            selected_wellness_title=self._template_text(selected_wellness.template, "title"),
            dynamic_state=dynamic_state,
        )
        notes = (
            "Retrieve-rank-compose selected one meal, one activity, and one wellness option "
            f"for a {risk_level} risk day."
        )

        draft_plan = InterventionDraft(
            meal_suggestion=MealSuggestion(
                title=selected_meal.recipe.title,
                description=selected_meal.recipe.description,
                rationale=" ".join(why_chosen["meal"][:2]),
            ),
            activity_suggestion=ActivitySuggestion(
                title=self._template_text(selected_activity.template, "title"),
                description=self._template_text(selected_activity.template, "description"),
                duration_minutes=self._template_int(selected_activity.template, "duration_minutes", 10),
                intensity=self._template_text(selected_activity.template, "intensity") or "low",
                rationale=" ".join(why_chosen["activity"][:2]),
            ),
            wellness_action=WellnessAction(
                title=self._template_text(selected_wellness.template, "title"),
                description=self._template_text(selected_wellness.template, "description"),
                rationale=" ".join(why_chosen["wellness"][:2]),
            ),
            recipe_id=None,
            activity_template_id=self._template_int(selected_activity.template, "id", 0),
            wellness_template_id=self._template_int(selected_wellness.template, "id", 0),
            generation_mode="fallback",
            generation_error="",
            resources=sorted({str(item).strip() for item in resources if str(item).strip()}),
            notes=notes,
            meal_constraints=meal_constraints,
            why_chosen=why_chosen,
            alternatives_considered=alternatives_considered,
            why_changed_from_previous=why_changed,
        ).model_dump()

        prompt_payload = {
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
            "meal_ranking_context": summarize_recipe_preferences(meal_context),
            "selected_support_plan": {
                "meal": {
                    "title": draft_plan["meal_suggestion"]["title"],
                    "description": draft_plan["meal_suggestion"]["description"],
                    "why_chosen": why_chosen["meal"],
                    "alternatives_considered": [item for item in alternatives_considered if item["kind"] == "meal"],
                },
                "activity": {
                    "template_id": draft_plan["activity_template_id"],
                    "title": draft_plan["activity_suggestion"]["title"],
                    "description": draft_plan["activity_suggestion"]["description"],
                    "duration_minutes": draft_plan["activity_suggestion"]["duration_minutes"],
                    "intensity": draft_plan["activity_suggestion"]["intensity"],
                    "why_chosen": why_chosen["activity"],
                    "alternatives_considered": [item for item in alternatives_considered if item["kind"] == "activity"],
                },
                "wellness": {
                    "template_id": draft_plan["wellness_template_id"],
                    "title": draft_plan["wellness_action"]["title"],
                    "description": draft_plan["wellness_action"]["description"],
                    "why_chosen": why_chosen["wellness"],
                    "alternatives_considered": [item for item in alternatives_considered if item["kind"] == "wellness"],
                },
                "why_changed_from_previous": why_changed,
            },
            "ranked_meal_candidates": [self._serialize_ranked_meal(item) for item in ranked_meals],
            "ranked_activity_candidates": [self._serialize_ranked_catalog_item(item, kind="activity") for item in ranked_activities],
            "ranked_wellness_candidates": [self._serialize_ranked_catalog_item(item, kind="wellness") for item in ranked_wellness],
        }
        return {"draft_plan": draft_plan, "prompt_payload": prompt_payload}

    @staticmethod
    def _meal_choice_reasons(
        *,
        ranked_item: Any,
        meal_constraints: Sequence[str],
        goal: str,
        allergies: Sequence[str],
        dynamic_state: Mapping[str, Any],
    ) -> List[str]:
        reasons: list[str] = []
        matched_tags = {str(tag).strip().lower() for tag in ranked_item.matched_tags}
        candidate = ranked_item.recipe
        if "low_prep" in matched_tags or str(getattr(candidate, "prep_effort", "")).lower() == "low":
            reasons.append("Fits current prep capacity with low effort.")
        if "high_protein" in matched_tags or _safe_float(getattr(candidate, "protein_grams", 0.0)) >= 18.0:
            reasons.append("Improves protein coverage without adding complexity.")
        if "comforting" in matched_tags and _safe_float(dynamic_state.get("stress_load"), 0.0) >= 0.55:
            reasons.append("Leans comforting for a higher-stress day.")
        if "hydration_support" in matched_tags and _safe_float(dynamic_state.get("sleep_debt"), 0.0) >= 0.35:
            reasons.append("Supports recovery after lighter sleep.")
        if any(str(constraint).startswith("avoid_") for constraint in meal_constraints) and allergies:
            reasons.append("Stays aligned with the current allergy constraints.")
        if goal == "better_sleep" and "light" in matched_tags:
            reasons.append("Keeps the meal lighter so it does not add friction later in the day.")
        if not reasons:
            reasons.append("Ranks best against today's deterministic meal-fit constraints.")
        return reasons[:3]

    @staticmethod
    def _activity_choice_reasons(
        *,
        ranked_item: RankedCatalogItem,
        goal: str,
        risk_level: str,
        dynamic_state: Mapping[str, Any],
        accessibility: Mapping[str, Any],
    ) -> List[str]:
        reasons: list[str] = []
        template = ranked_item.template
        if risk_level in {"moderate", "high", "critical"}:
            reasons.append("Keeps intensity manageable for the current strain level.")
        if _safe_float(dynamic_state.get("activity_capacity"), 0.5) <= 0.45:
            reasons.append("Matches today's lower activity capacity.")
        if bool(accessibility.get("low_energy_mode", False)) and "low_energy_friendly" in _template_tags(template, "accessibility_tags"):
            reasons.append("Works well with low-energy mode and minimal setup.")
        if goal in _template_metadata_tags(template, "goal_tags"):
            reasons.append(f"Supports your {goal.replace('_', ' ')} goal without adding pressure.")
        if not reasons:
            reasons.append("Ranks best for today's recovery, duration, and accessibility fit.")
        return reasons[:3]

    @staticmethod
    def _wellness_choice_reasons(
        *,
        ranked_item: RankedCatalogItem,
        goal: str,
        dynamic_state: Mapping[str, Any],
        recent_checkins: Sequence[Mapping[str, Any]],
        accessibility: Mapping[str, Any],
    ) -> List[str]:
        reasons: list[str] = []
        template = ranked_item.template
        category = _normalize_tag(InterventionPlanningAgent._template_text(template, "category"))
        stress_load = _safe_float(dynamic_state.get("stress_load"), 0.0)
        sleep_debt = _safe_float(dynamic_state.get("sleep_debt"), 0.0)
        if category in {"grounding", "breathing"} and stress_load >= 0.55:
            reasons.append("Directly addresses elevated stress load.")
        if category == "sleep" and (sleep_debt >= 0.35 or goal == "better_sleep"):
            reasons.append("Supports sleep recovery later today.")
        if category in {"planning", "routine"} and _safe_float(dynamic_state.get("routine_stability"), 0.5) <= 0.45:
            reasons.append("Helps rebuild routine with a low-friction step.")
        if bool(accessibility.get("low_energy_mode", False)) and "low_energy_friendly" in _template_tags(template, "accessibility_tags"):
            reasons.append("Fits a low-energy day without extra setup.")
        if recent_checkins and _safe_float(recent_checkins[0].get("note_sentiment"), 0.0) < -0.15 and category == "reflection":
            reasons.append("Creates a small outlet for the current mental load.")
        if not reasons:
            reasons.append("Ranks best for today's stress, sleep, and time-fit signals.")
        return reasons[:3]

    @staticmethod
    def _build_alternatives(
        *,
        ranked_meals: Sequence[Any],
        ranked_activities: Sequence[RankedCatalogItem],
        ranked_wellness: Sequence[RankedCatalogItem],
    ) -> List[Dict[str, Any]]:
        alternatives: list[dict[str, Any]] = []
        for rank, item in enumerate(ranked_meals[1:3], start=2):
            alternatives.append(
                {
                    "kind": "meal",
                    "title": item.recipe.title,
                    "rank": rank,
                    "score": round(item.score, 3),
                }
            )
        for rank, item in enumerate(ranked_activities[1:3], start=2):
            alternatives.append(
                {
                    "kind": "activity",
                    "template_id": InterventionPlanningAgent._template_int(item.template, "id", 0),
                    "title": InterventionPlanningAgent._template_text(item.template, "title"),
                    "rank": rank,
                    "score": round(item.score, 3),
                }
            )
        for rank, item in enumerate(ranked_wellness[1:3], start=2):
            alternatives.append(
                {
                    "kind": "wellness",
                    "template_id": InterventionPlanningAgent._template_int(item.template, "id", 0),
                    "title": InterventionPlanningAgent._template_text(item.template, "title"),
                    "rank": rank,
                    "score": round(item.score, 3),
                }
            )
        return alternatives

    @staticmethod
    def _why_changed_from_previous(
        *,
        intervention_history: Mapping[str, Any],
        selected_meal_title: str,
        selected_activity_title: str,
        selected_wellness_title: str,
        dynamic_state: Mapping[str, Any],
    ) -> List[str]:
        latest = dict(intervention_history.get("latest") or {})
        if not latest:
            return []

        reasons: list[str] = []
        latest_meal = str(latest.get("meal_suggestion", "")).lower()
        latest_activity = str(latest.get("activity_suggestion", "")).lower()
        latest_wellness = str(latest.get("wellness_action", "")).lower()
        if selected_meal_title.lower() not in latest_meal:
            if _safe_float(dynamic_state.get("prep_capacity"), 0.5) <= 0.45:
                reasons.append("Meal choice shifted toward a lower-prep fit than the previous plan.")
            else:
                reasons.append("Meal choice changed to better match today's ranked meal fit.")
        if selected_activity_title.lower() not in latest_activity:
            reasons.append("Activity changed to better match today's capacity and recovery signals.")
        if selected_wellness_title.lower() not in latest_wellness:
            reasons.append("Wellness action changed to better match today's stress and routine needs.")
        return reasons[:3]

    @staticmethod
    def _serialize_ranked_meal(ranked_item: Any) -> Dict[str, Any]:
        return {
            "title": ranked_item.recipe.title,
            "description": ranked_item.recipe.description,
            "score": round(ranked_item.score, 3),
            "matched_tags": list(ranked_item.matched_tags),
        }

    @staticmethod
    def _serialize_ranked_catalog_item(ranked_item: RankedCatalogItem, *, kind: str) -> Dict[str, Any]:
        payload = {
            "title": InterventionPlanningAgent._template_text(ranked_item.template, "title"),
            "description": InterventionPlanningAgent._template_text(ranked_item.template, "description"),
            "score": round(ranked_item.score, 3),
            "components": {
                key: round(float(value), 3)
                for key, value in ranked_item.components.items()
            },
            "rank_kind": kind,
        }
        template_id = InterventionPlanningAgent._template_int(ranked_item.template, "id", 0)
        if template_id:
            payload["template_id"] = template_id
        duration = InterventionPlanningAgent._template_int(ranked_item.template, "duration_minutes", 0)
        if duration:
            payload["duration_minutes"] = duration
        intensity = InterventionPlanningAgent._template_text(ranked_item.template, "intensity")
        if intensity:
            payload["intensity"] = intensity
        category = InterventionPlanningAgent._template_text(ranked_item.template, "category")
        if category:
            payload["category"] = category
        return payload

    @staticmethod
    def _coerce_plan(
        payload: Dict[str, Any],
        *,
        base_plan: Dict[str, Any],
        resources: List[str],
        persona_type: str,
    ) -> Dict[str, object]:
        meal_payload = payload.get("meal_suggestion", {}) if isinstance(payload.get("meal_suggestion"), dict) else {}
        activity_payload = payload.get("activity_suggestion", {}) if isinstance(payload.get("activity_suggestion"), dict) else {}
        wellness_payload = payload.get("wellness_action", {}) if isinstance(payload.get("wellness_action"), dict) else {}

        model_resources = payload.get("resources") or []
        merged_resources = sorted(
            {
                str(item).strip()
                for item in [*resources, *(base_plan.get("resources") or []), *model_resources]
                if str(item).strip()
            }
        )
        notes = str(payload.get("notes", "")).strip() or str(base_plan.get("notes", "")).strip() or f"Plan tuned for {persona_type}."
        meal_constraints = sorted(
            {
                *[str(item).strip().lower() for item in (base_plan.get("meal_constraints") or []) if str(item).strip()],
                *[str(item).strip().lower() for item in (payload.get("meal_constraints") or []) if str(item).strip()],
            }
        )
        why_chosen = _merge_reason_map(
            dict(base_plan.get("why_chosen") or {}),
            payload.get("why_chosen"),
        )

        return InterventionDraft(
            meal_suggestion=MealSuggestion(
                title=str(base_plan["meal_suggestion"]["title"]).strip(),
                description=str(meal_payload.get("description", "")).strip() or str(base_plan["meal_suggestion"]["description"]).strip(),
                rationale=str(meal_payload.get("rationale", "")).strip() or str(base_plan["meal_suggestion"]["rationale"]).strip(),
            ),
            activity_suggestion=ActivitySuggestion(
                title=str(base_plan["activity_suggestion"]["title"]).strip(),
                description=str(activity_payload.get("description", "")).strip() or str(base_plan["activity_suggestion"]["description"]).strip(),
                duration_minutes=max(5, min(int(base_plan["activity_suggestion"]["duration_minutes"]), 60)),
                intensity=str(base_plan["activity_suggestion"]["intensity"]).strip() or "low",
                rationale=str(activity_payload.get("rationale", "")).strip() or str(base_plan["activity_suggestion"]["rationale"]).strip(),
            ),
            wellness_action=WellnessAction(
                title=str(base_plan["wellness_action"]["title"]).strip(),
                description=str(wellness_payload.get("description", "")).strip() or str(base_plan["wellness_action"]["description"]).strip(),
                rationale=str(wellness_payload.get("rationale", "")).strip() or str(base_plan["wellness_action"]["rationale"]).strip(),
            ),
            recipe_id=base_plan.get("recipe_id"),
            activity_template_id=base_plan.get("activity_template_id"),
            wellness_template_id=base_plan.get("wellness_template_id"),
            generation_mode="llm",
            generation_error="",
            resources=merged_resources,
            notes=notes,
            meal_constraints=meal_constraints,
            why_chosen=why_chosen,
            alternatives_considered=list(base_plan.get("alternatives_considered") or []),
            why_changed_from_previous=list(base_plan.get("why_changed_from_previous") or []),
        ).model_dump()

    @staticmethod
    def _template_text(template: Mapping[str, Any], field_name: str) -> str:
        return str(template.get(field_name, "")).strip()

    @staticmethod
    def _template_int(template: Mapping[str, Any], field_name: str, default: int) -> int:
        try:
            value = int(template.get(field_name, default))
        except (TypeError, ValueError):
            return default
        return value


@lru_cache(maxsize=1)
def _load_recipe_candidates() -> tuple[_RecipeTemplateCandidate, ...]:
    try:
        from routers.recipes import DEFAULT_TEMPLATE_RECIPES  # type: ignore

        templates = tuple(DEFAULT_TEMPLATE_RECIPES)
    except Exception:
        templates = _FALLBACK_RECIPE_TEMPLATES

    return tuple(
        _RecipeTemplateCandidate(
            id=index + 1,
            title=str(template.get("title", "Supportive Meal")).strip(),
            description=str(template.get("description", "")).strip(),
            tags=tuple(template.get("tags") or ()),
            ingredients=tuple(template.get("ingredients") or ()),
            prep_effort=template.get("prep_effort"),
            prep_minutes=template.get("prep_minutes"),
            cook_minutes=template.get("cook_minutes"),
            calories=template.get("calories"),
            protein_grams=template.get("protein_grams"),
        )
        for index, template in enumerate(templates)
    )


def _template_tags(template: Mapping[str, Any], field_name: str) -> set[str]:
    return {
        _normalize_tag(item)
        for item in template.get(field_name, []) or []
        if _normalize_tag(item)
    }


def _template_metadata_tags(template: Mapping[str, Any], field_name: str) -> set[str]:
    metadata = dict(template.get("metadata") or {})
    return {
        _normalize_tag(item)
        for item in metadata.get(field_name, []) or []
        if _normalize_tag(item)
    }


def _merge_reason_map(base: Dict[str, Any], candidate: Any) -> Dict[str, List[str]]:
    merged: dict[str, list[str]] = {}
    candidate_map = candidate if isinstance(candidate, dict) else {}
    for key in sorted({*base.keys(), *candidate_map.keys()}):
        candidate_values = candidate_map.get(key) if isinstance(candidate_map.get(key), list) else []
        merged[key] = _normalize_reason_list(
            [
                *list(base.get(key) or []),
                *list(candidate_values),
            ]
        )
    return merged


def _normalize_reason_list(values: Sequence[Any]) -> List[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized[:4]


def _normalize_tag(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
