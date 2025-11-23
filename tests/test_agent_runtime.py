"""Tests for the chat agent runtime helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

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

    assert manager.window_size == 2
    assert manager.should_truncate_results is True


def test_build_agent_constructs_strands_agent() -> None:
    config = SessionConfig(model="gpt-5.1", window_size=10, should_truncate_results=True)
    client = ModelClient(provider=ModelProvider.OPENAI, model_id="gpt-5.1", client=object())

    sentinel_manager = object()
    with patch("server.agents.chat.runtime.build_conversation_manager", return_value=sentinel_manager) as bcm_mock, patch(
        "server.agents.chat.runtime.Agent"
    ) as agent_cls:
        agent_instance = MagicMock()
        agent_cls.return_value = agent_instance

        agent = build_agent(
            session_config=config,
            model_client=client,
            system_prompt="You are helpful.",
            tools=("calc",),
        )

    assert agent is agent_instance
    bcm_mock.assert_called_once_with(config)
    agent_cls.assert_called_once_with(
        model=client.client,
        system_prompt="You are helpful.",
        tools=["calc"],
        conversation_manager=sentinel_manager,
        load_tools_from_directory=False,
    )


def test_build_agent_requires_client() -> None:
    config = SessionConfig(model="gpt-5.1", window_size=5, should_truncate_results=True)
    with pytest.raises(AgentBuildError):
        build_agent(session_config=config, model_client=None, system_prompt=None)

