"""Tests for chat CLI helper functions (Task 1 scope)."""

from __future__ import annotations

import os
from argparse import Namespace
from pathlib import Path

import pytest

from server.tools import chat_cli as chat
from server.tools.lib.session_store import SessionStore


def test_resolve_session_creates_new_when_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("RETIRE_CURRENT_SESSION_ID", raising=False)
    store = SessionStore(base_dir=tmp_path / ".chat")
    args = Namespace(new_session=True, session=None)

    session_id = chat.resolve_session(store, args)

    assert store.session_exists(session_id)
    assert os.environ["RETIRE_CURRENT_SESSION_ID"] == session_id


def test_resolve_config_applies_overrides(tmp_path: Path) -> None:
    store = SessionStore(base_dir=tmp_path / ".chat")
    record = store.create_session()
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "model: gpt-5.1-mini\nwindow_size: 20\nshould_truncate_results: true\n",
        encoding="utf-8",
    )
    args = Namespace(
        new_session=True,
        config_file=str(config_path),
        model="gemini-2.5",
        window_size=64,
        should_truncate_results="false",
    )

    config = chat.resolve_config(store, record.id, args)

    assert config.model == "gemini-2.5"
    assert config.window_size == 64
    assert config.should_truncate_results is False

