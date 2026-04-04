from __future__ import annotations

from dataclasses import dataclass
import importlib
import logging
from pathlib import Path
import sys
from typing import Any, Callable, Dict, List, Optional

try:
    from services.agents.config import REPO_ROOT
    from services.agents.dev_stubs import (
        get_recent_signals_stub,
        get_resources_stub,
        get_user_profile_stub,
    )
except ImportError:
    from config import REPO_ROOT
    from dev_stubs import get_recent_signals_stub, get_resources_stub, get_user_profile_stub


if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger(__name__)


def _load_callable(module_name: str, attr_name: str) -> Optional[Callable[..., Any]]:
    try:
        module = importlib.import_module(module_name)
        return getattr(module, attr_name)
    except Exception:
        logger.exception("Failed to import tool callable %s.%s", module_name, attr_name)
        return None


def _require_callable(module_name: str, attr_name: str) -> Callable[..., Any]:
    func = _load_callable(module_name, attr_name)
    if func is None:
        raise RuntimeError(f"Tool import failed for {module_name}.{attr_name}")
    return func


@dataclass
class ToolProvider:
    use_stubs: bool = True
    api_base_url: str = "http://localhost:8000"
    auth_header: str = ""
    demo_as: str = ""
    internal_api_token: str = ""
    acting_user_id: int | None = None

    def get_user_profile(self, persona_type: str = "student") -> Dict[str, Any]:
        if not self.use_stubs:
            func = _require_callable("services.tools.get_user_profile_tool", "get_user_profile")
            return func(
                api_base_url=self.api_base_url,
                auth_header=self.auth_header,
                demo_as=self.demo_as,
                internal_api_token=self.internal_api_token,
                acting_user_id=self.acting_user_id,
                fallback_persona=persona_type,
            )
        return get_user_profile_stub(persona_type=persona_type)

    def get_recent_signals(self, scenario: str = "stressed_student") -> List[Dict[str, Any]]:
        if not self.use_stubs:
            func = _require_callable("services.tools.get_recent_signals_tool", "get_recent_signals")
            return func(
                api_base_url=self.api_base_url,
                auth_header=self.auth_header,
                demo_as=self.demo_as,
                internal_api_token=self.internal_api_token,
                acting_user_id=self.acting_user_id,
            )
        return get_recent_signals_stub(scenario=scenario)

    def get_personalization_context(
        self,
        *,
        run_id: int | None = None,
        scenario: str = "live",
    ) -> Dict[str, Any]:
        if not self.use_stubs:
            func = _require_callable(
                "services.tools.get_personalization_context_tool",
                "get_personalization_context",
            )
            return func(
                api_base_url=self.api_base_url,
                auth_header=self.auth_header,
                demo_as=self.demo_as,
                internal_api_token=self.internal_api_token,
                acting_user_id=self.acting_user_id,
                run_id=run_id,
                scenario=scenario,
            )

        inferred_persona = "student" if scenario == "stressed_student" else (
            "caregiver" if scenario == "exhausted_caregiver" else "older_adult"
        )
        profile = get_user_profile_stub(persona_type=inferred_persona)
        raw_signals = get_recent_signals_stub(scenario=scenario)
        signals = {item["signal_type"]: item["value"] for item in raw_signals}
        return {
            "snapshot_id": 0,
            "user_id": self.acting_user_id or 0,
            "run_id": run_id,
            "scenario": scenario,
            "persona_type": profile.get("persona_type", inferred_persona),
            "profile": profile,
            "dynamic_state": {},
            "archetype_scores": {},
            "feature_windows": {},
            "recent_checkins": [],
            "calorie_summary": {},
            "recipe_history": {},
            "intervention_history": {},
            "signals": signals,
            "normalized_event_id": None,
        }

    def get_resources(self, persona: str) -> List[Dict[str, Any]]:
        if not self.use_stubs:
            func = _require_callable("services.tools.get_resources_tool", "get_resources")
            return func(
                persona=persona,
                api_base_url=self.api_base_url,
                auth_header=self.auth_header,
                demo_as=self.demo_as,
                internal_api_token=self.internal_api_token,
                acting_user_id=self.acting_user_id,
            )
        return get_resources_stub(persona)

    def create_case(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.use_stubs:
            func = _require_callable("services.tools.create_case_tool", "create_case")
            return func(
                api_base_url=self.api_base_url,
                auth_header=self.auth_header,
                demo_as=self.demo_as,
                internal_api_token=self.internal_api_token,
                acting_user_id=self.acting_user_id,
                **payload,
            )
        return {"id": 1, **payload, "status": "open"}

    def create_intervention(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.use_stubs:
            func = _require_callable("services.tools.create_intervention_tool", "create_intervention")
            return func(
                api_base_url=self.api_base_url,
                auth_header=self.auth_header,
                demo_as=self.demo_as,
                internal_api_token=self.internal_api_token,
                acting_user_id=self.acting_user_id,
                **payload,
            )
        return {"id": 1, **payload}

    def send_notification(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.use_stubs:
            func = _require_callable("services.tools.send_notification_tool", "send_notification")
            return func(
                api_base_url=self.api_base_url,
                auth_header=self.auth_header,
                demo_as=self.demo_as,
                internal_api_token=self.internal_api_token,
                acting_user_id=self.acting_user_id,
                **payload,
            )
        return {"id": 1, **payload, "status": "queued"}

    def persist_audit(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.use_stubs:
            func = _require_callable("services.tools.persist_audit_tool", "persist_audit")
            return func(
                api_base_url=self.api_base_url,
                auth_header=self.auth_header,
                demo_as=self.demo_as,
                internal_api_token=self.internal_api_token,
                acting_user_id=self.acting_user_id,
                **payload,
            )
        return {"id": 1, **payload}

    def persist_run_message(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.use_stubs:
            func = _require_callable("services.tools.persist_run_message_tool", "persist_run_message")
            return func(
                api_base_url=self.api_base_url,
                auth_header=self.auth_header,
                demo_as=self.demo_as,
                internal_api_token=self.internal_api_token,
                acting_user_id=self.acting_user_id,
                **payload,
            )
        return {"id": payload.get("run_id", 0), **payload}

    def update_run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.use_stubs:
            func = _require_callable("services.tools.update_run_tool", "update_run")
            run_id = payload.pop("run_id")
            return func(
                run_id=run_id,
                api_base_url=self.api_base_url,
                auth_header=self.auth_header,
                demo_as=self.demo_as,
                internal_api_token=self.internal_api_token,
                acting_user_id=self.acting_user_id,
                **payload,
            )
        return {"id": payload.get("run_id", 0), **payload}
