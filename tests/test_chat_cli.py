"""Tests for chat CLI helper functions (Task 1-2 scope)."""

from __future__ import annotations

import os
from argparse import Namespace
from pathlib import Path

import pytest

from server.tools.lib import chat_cli as chat
from server.tools.lib.session_store import SessionStore


def make_args(**overrides) -> Namespace:
    defaults = dict(
        new_session=False,
        session=None,
        config_file=None,
        model=None,
        window_size=None,
        should_truncate_results=None,
        system_prompt=None,
        system_prompt_file=None,
        description=None,
        delete_session=None,
        list_sessions=False,
        single=False,
        verbose=False,
    )
    defaults.update(overrides)
    return Namespace(**defaults)


def test_resolve_session_creates_new_when_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("RETIRE_CURRENT_SESSION_ID", raising=False)
    store = SessionStore(base_dir=tmp_path / ".chat")
    args = make_args(new_session=True)

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
    args = make_args(
        new_session=True,
        config_file=str(config_path),
        model="gemini-2.5-pro",
        window_size=64,
        should_truncate_results="false",
    )

    config, metadata = chat.resolve_config(store, record.id, args)

    assert config.model == "gemini-2.5-pro"
    assert config.window_size == 64
    assert config.should_truncate_results is False
    assert metadata["config"]["model"] == "gemini-2.5-pro"


def test_resolve_system_prompt_inline_updates_metadata_and_history(tmp_path: Path) -> None:
    store = SessionStore(base_dir=tmp_path / ".chat")
    record = store.create_session()
    args = make_args(system_prompt="You are a planner.")

    metadata = {}
    prompt_text = chat.resolve_system_prompt(store, record.id, metadata, args)
    store.write_metadata(record.id, metadata)

    history = store.read_history(record.id)
    assert history[-1]["role"] == "system"
    assert prompt_text == "You are a planner."
    assert metadata["system_prompt_source"] == "inline"


def test_resolve_system_prompt_file_updates(tmp_path: Path) -> None:
    store = SessionStore(base_dir=tmp_path / ".chat")
    record = store.create_session()
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("File prompt", encoding="utf-8")
    args = make_args(system_prompt_file=str(prompt_file))

    metadata = {}
    chat.resolve_system_prompt(store, record.id, metadata, args)
    assert metadata["system_prompt_file_path"].endswith("prompt.txt")


def test_resolve_system_prompt_conflict(tmp_path: Path) -> None:
    store = SessionStore(base_dir=tmp_path / ".chat")
    record = store.create_session()
    args = make_args(system_prompt="inline", system_prompt_file="path.txt")

    metadata = {}
    with pytest.raises(ValueError):
        chat.resolve_system_prompt(store, record.id, metadata, args)


def test_history_to_agent_messages_skips_system_entries() -> None:
    history = [
        {"role": "system", "content": "prompt"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]

    messages = chat.history_to_agent_messages(history)

    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"][0]["text"] == "hello"
    assert messages[1]["role"] == "assistant"


def test_extract_text_from_message_concatenates_blocks() -> None:
    message = {
        "content": [
            {"text": "Part one"},
            {"text": "Part two"},
            {"toolUse": {}},
        ]
    }

    assert chat.extract_text_from_message(message) == "Part one\nPart two"
