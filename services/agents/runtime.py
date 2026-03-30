from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List


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
