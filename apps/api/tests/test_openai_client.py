from __future__ import annotations

from types import SimpleNamespace

import openai

import openai_client


OPENAI_SETTINGS_FIELDS = (
    "azure_openai_api_key",
    "azure_api_key",
    "openai_api_key",
    "azure_openai_endpoint",
    "azure_openai_base_url",
    "openai_base_url",
    "azure_openai_api_version",
    "openai_api_version",
    "azure_openai_deployment",
    "azure_openai_deployment_name",
    "azure_openai_model",
    "openai_model",
)


def _reset_openai_settings(monkeypatch) -> None:
    for field in OPENAI_SETTINGS_FIELDS:
        monkeypatch.setattr(openai_client.settings, field, "")
    monkeypatch.delenv("OPENAI_API_VERSION", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_VERSION", raising=False)


def test_resolve_openai_config_uses_azure_client_for_legacy_endpoint(monkeypatch):
    _reset_openai_settings(monkeypatch)
    monkeypatch.setattr(openai_client.settings, "azure_openai_api_key", "test-key")
    monkeypatch.setattr(
        openai_client.settings,
        "azure_openai_endpoint",
        "https://nume.cognitiveservices.azure.com/openai/deployments/gpt-4.1-mini/chat/completions?api-version=2025-01-01-preview",
    )

    config, error = openai_client.resolve_openai_config()

    assert error == ""
    assert config is not None
    assert config.use_azure_client is True
    assert config.azure_endpoint == "https://nume.cognitiveservices.azure.com"
    assert config.api_version == "2025-01-01-preview"
    assert config.model == "gpt-4.1-mini"


def test_resolve_openai_config_normalizes_v1_base_url(monkeypatch):
    _reset_openai_settings(monkeypatch)
    monkeypatch.setattr(openai_client.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(
        openai_client.settings,
        "openai_base_url",
        "https://nume.cognitiveservices.azure.com/openai/v1/",
    )
    monkeypatch.setattr(openai_client.settings, "openai_model", "gpt-4.1-mini")

    config, error = openai_client.resolve_openai_config()

    assert error == ""
    assert config is not None
    assert config.use_azure_client is False
    assert config.base_url == "https://nume.cognitiveservices.azure.com/openai/v1/"
    assert config.model == "gpt-4.1-mini"


async def test_generate_text_uses_async_azure_client_for_legacy_endpoint(monkeypatch):
    _reset_openai_settings(monkeypatch)
    monkeypatch.setattr(openai_client.settings, "azure_openai_api_key", "test-key")
    monkeypatch.setattr(
        openai_client.settings,
        "azure_openai_endpoint",
        "https://nume.cognitiveservices.azure.com/openai/deployments/gpt-4.1-mini/chat/completions?api-version=2025-01-01-preview",
    )

    calls: dict[str, object] = {}

    class DummyAsyncAzureOpenAI:
        def __init__(self, **kwargs):
            calls["client_kwargs"] = kwargs
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self._create),
            )

        async def _create(self, **kwargs):
            calls["request_kwargs"] = kwargs
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="azure response"),
                    )
                ]
            )

    class DummyAsyncOpenAI:
        def __init__(self, **_kwargs):
            raise AssertionError("Expected AsyncAzureOpenAI for a legacy Azure endpoint")

    monkeypatch.setattr(openai, "AsyncAzureOpenAI", DummyAsyncAzureOpenAI)
    monkeypatch.setattr(openai, "AsyncOpenAI", DummyAsyncOpenAI)

    text = await openai_client.generate_text("hello")

    assert text == "azure response"
    assert calls["client_kwargs"] == {
        "api_key": "test-key",
        "azure_endpoint": "https://nume.cognitiveservices.azure.com",
        "api_version": "2025-01-01-preview",
    }
    assert calls["request_kwargs"] == {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "user", "content": "hello"}],
    }


async def test_generate_text_uses_async_openai_for_v1_base_url(monkeypatch):
    _reset_openai_settings(monkeypatch)
    monkeypatch.setattr(openai_client.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(
        openai_client.settings,
        "openai_base_url",
        "https://nume.cognitiveservices.azure.com/openai/v1/",
    )
    monkeypatch.setattr(openai_client.settings, "openai_model", "gpt-4.1-mini")

    calls: dict[str, object] = {}

    class DummyAsyncOpenAI:
        def __init__(self, **kwargs):
            calls["client_kwargs"] = kwargs
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=self._create),
            )

        async def _create(self, **kwargs):
            calls["request_kwargs"] = kwargs
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="v1 response"),
                    )
                ]
            )

    class DummyAsyncAzureOpenAI:
        def __init__(self, **_kwargs):
            raise AssertionError("Expected AsyncOpenAI for an OpenAI v1 base URL")

    monkeypatch.setattr(openai, "AsyncOpenAI", DummyAsyncOpenAI)
    monkeypatch.setattr(openai, "AsyncAzureOpenAI", DummyAsyncAzureOpenAI)

    text = await openai_client.generate_text("hello")

    assert text == "v1 response"
    assert calls["client_kwargs"] == {
        "api_key": "test-key",
        "base_url": "https://nume.cognitiveservices.azure.com/openai/v1/",
    }
    assert calls["request_kwargs"] == {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "user", "content": "hello"}],
    }
