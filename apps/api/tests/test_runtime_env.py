from __future__ import annotations

import os

from runtime_env import configure_runtime_env


def test_configure_runtime_env_disables_logfire_plugin(monkeypatch):
    monkeypatch.delenv("PYDANTIC_DISABLE_PLUGINS", raising=False)

    configure_runtime_env()

    assert os.environ["PYDANTIC_DISABLE_PLUGINS"] == "logfire-plugin"


def test_configure_runtime_env_preserves_existing_disabled_plugins(monkeypatch):
    monkeypatch.setenv("PYDANTIC_DISABLE_PLUGINS", "custom-plugin")

    configure_runtime_env()

    assert set(os.environ["PYDANTIC_DISABLE_PLUGINS"].split(",")) == {
        "custom-plugin",
        "logfire-plugin",
    }


def test_configure_runtime_env_respects_global_plugin_disable(monkeypatch):
    monkeypatch.setenv("PYDANTIC_DISABLE_PLUGINS", "__all__")

    configure_runtime_env()

    assert os.environ["PYDANTIC_DISABLE_PLUGINS"] == "__all__"
