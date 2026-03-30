from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import sys

logger = logging.getLogger(__name__)


def _candidate_repo_roots() -> list[Path]:
    candidates: list[Path] = []

    def add_candidate(path: Path | None) -> None:
        if path is None:
            return
        resolved = path.resolve()
        if resolved not in candidates:
            candidates.append(resolved)

    env_root = os.getenv("NUME_REPO_ROOT")
    if env_root:
        add_candidate(Path(env_root))

    current = Path(__file__).resolve()
    add_candidate(current.parent)
    for parent in current.parents:
        add_candidate(parent)

    cwd = Path.cwd()
    add_candidate(cwd)
    for parent in cwd.parents:
        add_candidate(parent)

    # Common container roots across local Docker and Railway-style builds.
    add_candidate(Path("/app"))
    add_candidate(Path("/workspace"))

    return candidates


def _discover_repo_root() -> Path:
    checked: list[str] = []
    for candidate in _candidate_repo_roots():
        checked.append(str(candidate))
        if (candidate / "services" / "agents").exists():
            return candidate

    raise RuntimeError(
        "Cannot locate agents directory. "
        "Set NUME_REPO_ROOT to the repository root (the directory containing services/agents), "
        "and make sure the deployed API image includes the shared services/ directory. "
        f"Checked: {', '.join(checked)}"
    )


def _ensure_agents_importable() -> None:
    repo_root = _discover_repo_root()
    agents_dir = repo_root / "services" / "agents"
    for path in (str(agents_dir), str(repo_root)):
        if path not in sys.path:
            sys.path.insert(0, path)


async def _mark_run_failed_async(*, run_id: int, user_id: int, error: str, scenario: str) -> None:
    from database import AsyncSessionLocal
    from models.agents import AgentRun, AuditLog

    async with AsyncSessionLocal() as session:
        run = await session.get(AgentRun, run_id)
        if run is not None:
            run.status = "failed"
            run.completed_at = datetime.now(timezone.utc)

        session.add(
            AuditLog(
                user_id=user_id,
                action="agent_failed",
                entity_type="agent_run",
                entity_id=str(run_id),
                meta={"error": error, "scenario": scenario, "bootstrap_failure": True},
            )
        )
        await session.commit()


def _mark_run_failed_fallback(*, run_id: int, user_id: int, error: str, scenario: str) -> None:
    try:
        asyncio.run(
            _mark_run_failed_async(
                run_id=run_id,
                user_id=user_id,
                error=error,
                scenario=scenario,
            )
        )
    except Exception:
        logger.exception("Failed to persist fallback failure state for run_id=%s user_id=%s", run_id, user_id)


def run_coordinator_for_run(
    *,
    user_id: int,
    run_id: int,
    auth_header: str,
    api_base_url: str,
    demo_as: str = "",
    scenario: str = "live",
) -> None:
    tool_provider = None

    try:
        _ensure_agents_importable()

        from config import load_settings
        from coordinator.agent import CareCoordinatorPipeline
        from tooling import ToolProvider

        settings = load_settings()
        tool_provider = ToolProvider(
            use_stubs=False,
            api_base_url=api_base_url,
            auth_header=auth_header,
            demo_as=demo_as,
        )

        tool_provider.update_run({"run_id": run_id, "status": "running"})
        pipeline = CareCoordinatorPipeline(settings=settings, tool_provider=tool_provider)
        result = pipeline.run(user_id=str(user_id), scenario=scenario, run_id=run_id)
        tool_provider.update_run(
            {
                "run_id": run_id,
                "status": "completed",
                "risk_level": result["risk_assessment"]["risk_level"],
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    except Exception as exc:
        logger.exception("Coordinator run failed for run_id=%s user_id=%s", run_id, user_id)
        error = f"{type(exc).__name__}: {exc}"
        if tool_provider is None:
            _mark_run_failed_fallback(run_id=run_id, user_id=user_id, error=error, scenario=scenario)
            return

        try:
            tool_provider.persist_audit(
                {
                    "user_id": user_id,
                    "action": "agent_failed",
                    "entity_type": "agent_run",
                    "entity_id": str(run_id),
                    "metadata": {"error": error, "scenario": scenario},
                }
            )
        except Exception:
            logger.exception("Failed to persist audit for failed run_id=%s user_id=%s", run_id, user_id)

        try:
            tool_provider.update_run(
                {
                    "run_id": run_id,
                    "status": "failed",
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception:
            logger.exception("Failed to update failed status for run_id=%s user_id=%s", run_id, user_id)
