from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Mapping

try:
    from services.agents.adk_compat import ADK_AVAILABLE, LlmAgent
    from services.agents.llm_utils import DEFAULT_OPENAI_MODEL, resolve_openai_config
except ImportError:
    from adk_compat import ADK_AVAILABLE, LlmAgent
    from llm_utils import DEFAULT_OPENAI_MODEL, resolve_openai_config


ADK_RUNTIME_AVAILABLE = False

try:
    from google.adk.models.base_llm import BaseLlm
    from google.adk.models.llm_response import LlmResponse
    from google.adk.runners import InMemoryRunner
    from google.genai import types as genai_types

    ADK_RUNTIME_AVAILABLE = True
except Exception:  # pragma: no cover - exercised when google-adk is absent
    BaseLlm = Any  # type: ignore[assignment]
    LlmResponse = Any  # type: ignore[assignment]
    InMemoryRunner = Any  # type: ignore[assignment]
    genai_types = None  # type: ignore[assignment]


class AgentType(str, Enum):
    local = "local"
    a2a = "a2a"
    parallel = "parallel"
    loop = "loop"


@dataclass
class TraceRecorder:
    run_id: int
    tool_provider: Any
    messages: List[Dict[str, Any]] = field(default_factory=list)

    def log(
        self,
        *,
        agent_name: str,
        agent_type: AgentType,
        input_payload: Dict[str, Any],
        output_payload: Dict[str, Any],
        iteration: int = 0,
        duration_ms: int = 0,
    ) -> None:
        message = {
            "run_id": self.run_id,
            "agent_name": agent_name,
            "agent_type": agent_type.value,
            "input": input_payload,
            "output": output_payload,
            "iteration": iteration,
            "duration_ms": duration_ms,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.messages.append(message)
        self.tool_provider.persist_run_message(message)


def execute_parallel(callables: Dict[str, Callable[[], Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    with ThreadPoolExecutor(max_workers=len(callables)) as executor:
        futures = {name: executor.submit(func) for name, func in callables.items()}
        return {name: future.result() for name, future in futures.items()}


def adk_runtime_enabled() -> bool:
    return ADK_AVAILABLE and ADK_RUNTIME_AVAILABLE


class FailFastLlm(BaseLlm):
    """Minimal ADK model adapter used when no real model configuration is available."""

    error_message: str = ""

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r".*"]

    async def generate_content_async(
        self,
        llm_request: Any,
        stream: bool = False,
    ):
        del llm_request, stream
        raise RuntimeError(self.error_message or "No model configuration is available.")
        yield  # pragma: no cover - async generator contract


def build_adk_model(model_name: str | None = None) -> Any:
    config, error = resolve_openai_config(model_name)
    fallback_model = model_name or DEFAULT_OPENAI_MODEL

    if not config:
        return FailFastLlm(model=fallback_model, error_message=error)

    if not adk_runtime_enabled():
        return config.model

    try:
        from google.adk.models.lite_llm import LiteLlm
    except Exception as exc:  # pragma: no cover - depends on optional install
        return FailFastLlm(
            model=config.model,
            error_message=f"LiteLlm unavailable: {type(exc).__name__}: {exc}",
        )

    if config.use_azure_client:
        return LiteLlm(
            model=f"azure/{config.model}",
            api_key=config.api_key,
            api_base=config.azure_endpoint,
            api_version=config.api_version,
        )

    return LiteLlm(
        model=f"openai/{config.model}",
        api_key=config.api_key,
        api_base=config.base_url,
    )


def _combine_error_text(*parts: str) -> str:
    combined = [part.strip() for part in parts if part and part.strip()]
    return " | ".join(combined)


def _empty_model_response() -> Any:
    if not adk_runtime_enabled():
        return None

    return LlmResponse(
        content=genai_types.Content(
            role="model",
            parts=[genai_types.Part(text="")],
        )
    )


def build_stateful_llm_agent(
    *,
    name: str,
    model: Any,
    instruction_builder: Callable[[Mapping[str, Any]], str],
    state_key: str,
    parse_output: Callable[[str, Mapping[str, Any]], Dict[str, Any]],
    fallback_output: Callable[[Mapping[str, Any], str], Dict[str, Any]],
) -> Any:
    if not adk_runtime_enabled():
        return LlmAgent(name=name, instruction=f"{name} (ADK unavailable)", model=str(model))

    raw_key = f"temp:{state_key}:raw"
    parsed_key = f"temp:{state_key}:parsed"
    error_key = f"temp:{state_key}:error"

    def instruction(context: Any) -> str:
        return instruction_builder(context.state)

    def after_agent_callback(callback_context: Any) -> None:
        parsed = callback_context.state.get(parsed_key)
        error_text = str(callback_context.state.get(error_key, "") or "")
        if parsed is None:
            raw_output = str(callback_context.state.get(raw_key, "") or "").strip()
            if raw_output:
                try:
                    parsed = parse_output(raw_output, callback_context.state)
                except Exception as exc:
                    error_text = _combine_error_text(
                        error_text,
                        f"{type(exc).__name__}: {exc}",
                    )
            else:
                error_text = _combine_error_text(error_text, "Empty model response.")

        if parsed is None:
            parsed = fallback_output(callback_context.state, error_text)

        callback_context.state[state_key] = copy.deepcopy(parsed)

    def on_model_error(callback_context: Any, llm_request: Any, error: Exception) -> Any:
        del llm_request
        error_text = f"{type(error).__name__}: {error}"
        callback_context.state[error_key] = error_text
        callback_context.state[parsed_key] = copy.deepcopy(
            fallback_output(callback_context.state, error_text)
        )
        return _empty_model_response()

    return LlmAgent(
        name=name,
        model=model,
        instruction=instruction,
        include_contents="none",
        output_key=raw_key,
        after_agent_callback=after_agent_callback,
        on_model_error_callback=on_model_error,
    )


def run_in_memory_agent(
    *,
    agent: Any,
    app_name: str,
    user_id: str,
    session_id: str,
    initial_state: Dict[str, Any],
) -> tuple[Dict[str, Any], List[Any]]:
    if not adk_runtime_enabled():
        raise RuntimeError("Google ADK runtime is not available.")

    runner = InMemoryRunner(agent=agent, app_name=app_name)
    runner.session_service.create_session_sync(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
        state=copy.deepcopy(initial_state),
    )
    events = list(
        runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=genai_types.Content(
                role="user",
                parts=[
                    genai_types.Part(
                        text="Run the NüMe care coordination workflow using the current session state."
                    )
                ],
            ),
        )
    )
    session = runner.session_service.get_session_sync(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )
    return copy.deepcopy(session.state), events
