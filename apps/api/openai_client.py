from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional
from urllib.parse import parse_qs, urlparse, urlunparse

from settings import settings


DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str
    model: str
    base_url: str = ""
    azure_endpoint: str = ""
    api_version: str = ""
    use_azure_client: bool = False


@dataclass(frozen=True)
class ParsedEndpoint:
    resource_url: str
    deployment: str
    api_version: str
    has_v1_path: bool
    has_legacy_azure_path: bool


def _first_non_empty(*values: str) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return ""


def _parse_endpoint(candidate: str) -> ParsedEndpoint:
    candidate = candidate.strip()
    if not candidate:
        return ParsedEndpoint(
            resource_url="",
            deployment="",
            api_version="",
            has_v1_path=False,
            has_legacy_azure_path=False,
        )

    parsed = urlparse(candidate)
    query = parse_qs(parsed.query)
    path = parsed.path.rstrip("/")

    deployment = ""
    legacy_prefix = "/openai/deployments/"
    if legacy_prefix in path:
        suffix = path.split(legacy_prefix, 1)[1]
        deployment = suffix.split("/", 1)[0]

    if "/openai/v1" in path:
        resource_path = path.split("/openai/v1", 1)[0]
        has_v1_path = True
        has_legacy_azure_path = False
    elif "/openai" in path:
        resource_path = path.split("/openai", 1)[0]
        has_v1_path = False
        has_legacy_azure_path = True
    else:
        resource_path = path
        has_v1_path = False
        has_legacy_azure_path = False

    resource_url = urlunparse(parsed._replace(path=resource_path, query="", fragment="")).rstrip("/")
    api_version = ""
    for key in ("api-version", "api_version"):
        values = query.get(key)
        if values:
            api_version = values[0].strip()
            break

    return ParsedEndpoint(
        resource_url=resource_url,
        deployment=deployment,
        api_version=api_version,
        has_v1_path=has_v1_path,
        has_legacy_azure_path=has_legacy_azure_path,
    )


def _normalize_v1_base_url(candidate: str) -> str:
    parsed = _parse_endpoint(candidate)
    if not parsed.resource_url:
        return ""
    return f"{parsed.resource_url}/openai/v1/"


def resolve_openai_config(model_name: Optional[str] = None) -> tuple[Optional[OpenAIConfig], str]:
    api_key = _first_non_empty(
        settings.azure_openai_api_key,
        settings.openai_api_key,
        settings.azure_api_key,
    )
    if not api_key:
        return None, "AZURE_OPENAI_API_KEY or OPENAI_API_KEY is not set."

    base_url_candidate = _first_non_empty(
        settings.openai_base_url,
        settings.azure_openai_base_url,
    )
    endpoint_candidate = settings.azure_openai_endpoint.strip()

    parsed_base_url = _parse_endpoint(base_url_candidate)
    parsed_endpoint = _parse_endpoint(endpoint_candidate)

    resolved_model = model_name or _first_non_empty(
        settings.azure_openai_deployment,
        settings.azure_openai_deployment_name,
        parsed_base_url.deployment,
        parsed_endpoint.deployment,
        settings.azure_openai_model,
        settings.openai_model,
        DEFAULT_OPENAI_MODEL,
    )

    use_azure_client = bool(
        endpoint_candidate
        and not parsed_endpoint.has_v1_path
    ) or (
        base_url_candidate
        and (parsed_base_url.has_legacy_azure_path or parsed_base_url.api_version)
    )

    if use_azure_client:
        azure_endpoint = parsed_endpoint.resource_url or parsed_base_url.resource_url
        if not azure_endpoint:
            return None, "AZURE_OPENAI_ENDPOINT or OPENAI_BASE_URL is not set."

        api_version = _first_non_empty(
            settings.azure_openai_api_version,
            settings.openai_api_version,
            os.environ.get("AZURE_OPENAI_API_VERSION", ""),
            os.environ.get("OPENAI_API_VERSION", ""),
            parsed_endpoint.api_version,
            parsed_base_url.api_version,
        )
        if not api_version:
            return None, "OPENAI_API_VERSION or AZURE_OPENAI_API_VERSION is not set for Azure OpenAI."

        return OpenAIConfig(
            api_key=api_key,
            model=resolved_model,
            azure_endpoint=azure_endpoint,
            api_version=api_version,
            use_azure_client=True,
        ), ""

    base_url = _normalize_v1_base_url(base_url_candidate or endpoint_candidate)
    if not base_url:
        return None, "OPENAI_BASE_URL or AZURE_OPENAI_ENDPOINT is not set."

    return OpenAIConfig(
        api_key=api_key,
        model=resolved_model,
        base_url=base_url,
    ), ""


def extract_response_text(response) -> str:
    content = response.choices[0].message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            text = getattr(item, "text", "")
            if text:
                parts.append(str(text))
                continue
            if isinstance(item, dict) and item.get("type") == "text":
                value = item.get("text", "")
                if isinstance(value, dict):
                    value = value.get("value", "")
                if value:
                    parts.append(str(value))
        return "\n".join(parts)
    raise ValueError("No text content found in model response.")


async def generate_text(prompt: str, *, model_name: Optional[str] = None) -> str:
    config, error = resolve_openai_config(model_name=model_name)
    if not config:
        raise RuntimeError(error)

    try:
        from openai import AsyncAzureOpenAI, AsyncOpenAI
    except ModuleNotFoundError as exc:
        if exc.name != "openai":
            raise
        raise RuntimeError(
            "The 'openai' package is not installed. Install API dependencies with "
            "`pip install -r apps/api/requirements.txt`."
        ) from exc

    if config.use_azure_client:
        client = AsyncAzureOpenAI(
            api_key=config.api_key,
            azure_endpoint=config.azure_endpoint,
            api_version=config.api_version,
        )
    else:
        client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )
    response = await client.chat.completions.create(
        model=config.model,
        messages=[{"role": "user", "content": prompt}],
    )
    return extract_response_text(response)
