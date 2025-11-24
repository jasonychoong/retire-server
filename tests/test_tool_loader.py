"""Tests for the tool registry loader."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from server.tools.lib import tool_loader


def write_tool_module(tmp_path: Path, module_name: str = "demo_tool") -> None:
    module_file = tmp_path / f"{module_name}.py"
    module_file.write_text(
        "from strands import tool\n"
        "@tool\n"
        "def ping() -> str:\n"
        "    return 'pong'\n",
        encoding="utf-8",
    )


def test_load_tool_registry_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_tool_module(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    registry_file = tmp_path / "tools.yaml"
    registry_file.write_text("- demo_tool:ping\n", encoding="utf-8")
    monkeypatch.setattr(tool_loader, "TOOLS_FILE", registry_file)

    tools = tool_loader.load_tool_registry()

    assert len(tools) == 1
    assert callable(tools[0])
    assert tools[0]() == "pong"


def test_load_tool_registry_invalid_entry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    registry_file = tmp_path / "tools.yaml"
    registry_file.write_text("{bad: value}\n", encoding="utf-8")
    monkeypatch.setattr(tool_loader, "TOOLS_FILE", registry_file)

    with pytest.raises(tool_loader.ToolRegistryError):
        tool_loader.load_tool_registry()


