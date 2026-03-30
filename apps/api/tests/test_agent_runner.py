from __future__ import annotations

from pathlib import Path

import agent_runner


def test_discover_repo_root_ignores_invalid_env_and_uses_parent_layout(monkeypatch, tmp_path: Path):
    repo_root = tmp_path / "repo"
    agents_dir = repo_root / "services" / "agents"
    api_dir = repo_root / "apps" / "api"
    agents_dir.mkdir(parents=True)
    api_dir.mkdir(parents=True)

    monkeypatch.setenv("NUME_REPO_ROOT", str(tmp_path / "missing"))
    monkeypatch.setattr(agent_runner, "__file__", str(api_dir / "agent_runner.py"))
    monkeypatch.chdir(api_dir)

    assert agent_runner._discover_repo_root() == repo_root.resolve()


def test_run_coordinator_marks_run_failed_when_bootstrap_raises(monkeypatch):
    fallback_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        agent_runner,
        "_ensure_agents_importable",
        lambda: (_ for _ in ()).throw(RuntimeError("missing services")),
    )
    monkeypatch.setattr(
        agent_runner,
        "_mark_run_failed_fallback",
        lambda **kwargs: fallback_calls.append(kwargs),
    )

    agent_runner.run_coordinator_for_run(
        user_id=7,
        run_id=42,
        auth_header="Bearer test-token",
        api_base_url="https://nume.example.com",
        scenario="live",
    )

    assert fallback_calls == [
        {
            "run_id": 42,
            "user_id": 7,
            "error": "RuntimeError: missing services",
            "scenario": "live",
        }
    ]
