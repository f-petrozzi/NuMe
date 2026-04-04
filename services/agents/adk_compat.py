from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional


ADK_AVAILABLE = False
IMPORT_ERROR: Optional[Exception] = None

try:
    from google.adk.agents import BaseAgent, LlmAgent, LoopAgent, ParallelAgent, SequentialAgent
    try:
        from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
    except ImportError:
        try:
            from google.adk.agents import RemoteA2aAgent  # type: ignore
        except ImportError:
            @dataclass
            class RemoteA2aAgent:
                name: str
                agent_card: str
                description: str = ""
                invoke: Optional[Callable[[dict], dict]] = None
    ADK_AVAILABLE = True
except Exception as exc:  # pragma: no cover - exercised in local fallback
    IMPORT_ERROR = exc

    @dataclass
    class BaseAgent:
        name: str
        description: str = ""

    @dataclass
    class LlmAgent:
        name: str
        instruction: str
        tools: List[Any] = field(default_factory=list)
        model: str = "gpt-4.1-mini"

    @dataclass
    class ParallelAgent:
        name: str
        sub_agents: List[Any]

    @dataclass
    class SequentialAgent:
        name: str
        sub_agents: List[Any]

    @dataclass
    class LoopAgent:
        name: str
        sub_agent: Any
        max_iterations: int = 3

    @dataclass
    class RemoteA2aAgent:
        name: str
        agent_card: str
        description: str = ""
        invoke: Optional[Callable[[dict], dict]] = None
