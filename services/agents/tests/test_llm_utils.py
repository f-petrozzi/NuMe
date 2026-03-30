from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace

import openai

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.agents import llm_utils


OPENAI_ENV_VARS = (
    "AZURE_OPENAI_API_KEY",
    "OPENAI_API_KEY",
    "AZURE_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_BASE_URL",
    "OPENAI_BASE_URL",
    "AZURE_OPENAI_API_VERSION",
    "OPENAI_API_VERSION",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_DEPLOYMENT_NAME",
    "AZURE_OPENAI_MODEL",
    "OPENAI_MODEL",
)


def _clear_openai_env(monkeypatch) -> None:
    for key in OPENAI_ENV_VARS:
        monkeypatch.delenv(key, raising=False)


def test_resolve_openai_config_uses_azure_client_for_legacy_endpoint(monkeypatch):
    _clear_openai_env(monkeypatch)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv(
        "AZURE_OPENAI_ENDPOINT",
        "https://nume.cognitiveservices.azure.com/openai/deployments/gpt-4.1-mini/chat/completions?api-version=2025-01-01-preview",
    )

    config, error = llm_utils.resolve_openai_config()

    assert error == ""
    assert config is not None
    assert config.use_azure_client is True
    assert config.azure_endpoint == "https://nume.cognitiveservices.azure.com"
    assert config.api_version == "2025-01-01-preview"
    assert config.model == "gpt-4.1-mini"


def test_resolve_openai_config_normalizes_v1_base_url(monkeypatch):
    _clear_openai_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://nume.cognitiveservices.azure.com/openai/v1/")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1-mini")

    config, error = llm_utils.resolve_openai_config()

    assert error == ""
    assert config is not None
    assert config.use_azure_client is False
    assert config.base_url == "https://nume.cognitiveservices.azure.com/openai/v1/"
    assert config.model == "gpt-4.1-mini"


def test_openai_json_client_uses_azure_client_for_legacy_endpoint(monkeypatch):
    _clear_openai_env(monkeypatch)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setenv(
        "AZURE_OPENAI_ENDPOINT",
        "https://nume.cognitiveservices.azure.com/openai/deployments/gpt-4.1-mini/chat/completions?api-version=2025-01-01-preview",
    )

    calls: dict[str, object] = {}

    class DummyAzureOpenAI:
        def __init__(self, **kwargs):
            calls["client_kwargs"] = kwargs
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self._create),
            )

        def _create(self, **kwargs):
            calls["request_kwargs"] = kwargs
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content='{"ok": true}'),
                    )
                ]
            )

    class DummyOpenAI:
        def __init__(self, **_kwargs):
            raise AssertionError("Expected AzureOpenAI for a legacy Azure endpoint")

    monkeypatch.setattr(openai, "AzureOpenAI", DummyAzureOpenAI)
    monkeypatch.setattr(openai, "OpenAI", DummyOpenAI)

    result = llm_utils.OpenAIJsonClient().generate_json("hello")

    assert result.error == ""
    assert result.payload == {"ok": True}
    assert calls["client_kwargs"] == {
        "api_key": "test-key",
        "azure_endpoint": "https://nume.cognitiveservices.azure.com",
        "api_version": "2025-01-01-preview",
    }
    assert calls["request_kwargs"] == {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "user", "content": "hello"}],
    }


def test_openai_json_client_uses_v1_client_for_v1_base_url(monkeypatch):
    _clear_openai_env(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://nume.cognitiveservices.azure.com/openai/v1/")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1-mini")

    calls: dict[str, object] = {}

    class DummyOpenAI:
        def __init__(self, **kwargs):
            calls["client_kwargs"] = kwargs
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self._create),
            )

        def _create(self, **kwargs):
            calls["request_kwargs"] = kwargs
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content='{"ok": true}'),
                    )
                ]
            )

    class DummyAzureOpenAI:
        def __init__(self, **_kwargs):
            raise AssertionError("Expected OpenAI for an OpenAI v1 base URL")

    monkeypatch.setattr(openai, "OpenAI", DummyOpenAI)
    monkeypatch.setattr(openai, "AzureOpenAI", DummyAzureOpenAI)

    result = llm_utils.OpenAIJsonClient().generate_json("hello")

    assert result.error == ""
    assert result.payload == {"ok": True}
    assert calls["client_kwargs"] == {
        "api_key": "test-key",
        "base_url": "https://nume.cognitiveservices.azure.com/openai/v1/",
    }
    assert calls["request_kwargs"] == {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "user", "content": "hello"}],
    }
