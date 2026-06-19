from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


_PACKAGE_DIR = Path(__file__).parent


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载模块: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def register() -> dict[str, Any]:
    tools: list[dict[str, Any]] = []
    handlers: dict[str, Any] = {}
    safety: dict[str, bool] = {}

    for module_path in sorted(_PACKAGE_DIR.glob("*.py")):
        if module_path.name == "__init__.py" or module_path.name.startswith("_"):
            continue

        module_name = f"tools.automation.{module_path.stem}"
        try:
            module = _load_module(module_path, module_name)
        except Exception:
            continue

        if not hasattr(module, "register"):
            continue

        try:
            plugin = module.register()
        except Exception:
            continue

        if not isinstance(plugin, dict):
            continue

        module_tools = plugin.get("tools", [])
        module_handlers = plugin.get("handlers", {})
        module_safety = plugin.get("safety", {})

        if isinstance(module_tools, list):
            tools.extend([item for item in module_tools if isinstance(item, dict)])
        if isinstance(module_handlers, dict):
            handlers.update({k: v for k, v in module_handlers.items() if callable(v)})
        if isinstance(module_safety, dict):
            safety.update({k: bool(v) for k, v in module_safety.items()})

    return {"tools": tools, "handlers": handlers, "safety": safety}
