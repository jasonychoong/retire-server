"""Utility helpers for loading chat tools."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Iterable, List, Optional

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - fallback handled below
    yaml = None

CHAT_DIR = Path(__file__).resolve().parents[1] / ".chat"
TOOLS_FILE = CHAT_DIR / "tools.yaml"


class ToolRegistryError(RuntimeError):
    """Raised when the tool registry cannot be loaded."""


def load_tool_registry(registry_path: Optional[Path] = None) -> List[Any]:
    """Load tool callables defined in the registry file."""

    path = registry_path or TOOLS_FILE
    if not path.exists():
        return []
    entries = _parse_registry_file(path)
    tools: List[Any] = []
    for entry in entries:
        tools.append(_resolve_tool(entry))
    return tools


def _parse_registry_file(path: Path) -> List[str]:
    if yaml is None:
        return _parse_registry_without_yaml(path)
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or []
    if not isinstance(data, list):
        raise ToolRegistryError("Tool registry must be a list of module paths.")
    entries: List[str] = []
    for item in data:
        if not isinstance(item, str) or not item.strip():
            raise ToolRegistryError("Tool registry entries must be non-empty strings.")
        entries.append(item.strip())
    return entries


def _parse_registry_without_yaml(path: Path) -> List[str]:
    entries: List[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("-"):
                line = line[1:].strip()
            if not line:
                continue
            entries.append(line)
    return entries


def _resolve_tool(entry: str) -> Any:
    module_path, attr = _split_entry(entry)
    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as exc:  # pragma: no cover - import guard
        raise ToolRegistryError(f"Unable to import module '{module_path}'") from exc
    if attr:
        try:
            tool_obj = getattr(module, attr)
        except AttributeError as exc:
            raise ToolRegistryError(f"Module '{module_path}' has no attribute '{attr}'") from exc
    else:
        tool_obj = module
    if not callable(tool_obj):
        raise ToolRegistryError(f"Tool '{entry}' is not callable.")
    return tool_obj


def _split_entry(entry: str) -> tuple[str, Optional[str]]:
    if ":" in entry:
        module_path, attr = entry.split(":", 1)
        return module_path.strip(), attr.strip() or None
    return entry, None


