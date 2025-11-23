"""Tests for the chat agent runtime helpers."""

from __future__ import annotations

import pytest

from server.agents.chat.model_registry import ModelClient, ModelProvider
from server.agents.chat.runtime import (
    AgentBuildError,
    build_agent,
    build_conversation_manager,
)
from server.tools.lib import SessionConfig


def test_build_conversation_manager_applies_config() -> None:
    config = SessionConfig(model="gpt-5.1", window_size=2, should_truncate_results=True)
    manager = build_conversation_manager(config)

    history = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "next"},
    ]
    trimmed = manager.prepare_messages(history)
    assert len(trimmed) == 2
    assert trimmed[0]["content"] == "hello"


def test_build_agent_creates_payload() -> None:
    config = SessionConfig(model="gpt-5.1", window_size=10, should_truncate_results=True)
    client = ModelClient(provider=ModelProvider.OPENAI, model_id="gpt-5.1", client=object())

    agent = build_agent(
        session_config=config,
        model_client=client,
        system_prompt="You are helpful.",
        tools=("calc",),
    )

    payload = agent.build_payload([{"role": "user", "content": "hi"}])
    assert payload["model"] == "gpt-5.1"
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["role"] == "user"
    assert payload["tools"] == ["calc"]


def test_build_agent_requires_client() -> None:
    config = SessionConfig(model="gpt-5.1", window_size=5, should_truncate_results=True)
    with pytest.raises(AgentBuildError):
        build_agent(session_config=config, model_client=None, system_prompt=None)

