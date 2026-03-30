from __future__ import annotations

import os

_INCOMPATIBLE_PYDANTIC_PLUGINS = {"logfire-plugin"}
_GLOBAL_DISABLE_VALUES = {"__all__", "1", "true"}


def configure_runtime_env() -> None:
    """Disable optional global plugins that break this app's startup."""
    disabled_plugins = os.environ.get("PYDANTIC_DISABLE_PLUGINS")
    if disabled_plugins in _GLOBAL_DISABLE_VALUES:
        return

    plugins = {name.strip() for name in (disabled_plugins or "").split(",") if name.strip()}
    if _INCOMPATIBLE_PYDANTIC_PLUGINS.issubset(plugins):
        return

    plugins.update(_INCOMPATIBLE_PYDANTIC_PLUGINS)
    os.environ["PYDANTIC_DISABLE_PLUGINS"] = ",".join(sorted(plugins))
