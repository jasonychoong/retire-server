"""Agent runtime helpers that wrap the Strands SDK constructs."""

from __future__ import annotations

from typing import Any, Sequence

from strands.agent import Agent
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.types.content import Messages

from server.agents.chat.model_registry import ModelClient
from server.tools.lib import SessionConfig


class AgentBuildError(RuntimeError):
    """Raised when an agent cannot be constructed."""


def build_conversation_manager(config: SessionConfig) -> SlidingWindowConversationManager:
    """Instantiate the Strands sliding window manager for the effective session config."""

    return SlidingWindowConversationManager(
        window_size=config.window_size,
        should_truncate_results=config.should_truncate_results,
    )


def build_agent(
    *,
    session_config: SessionConfig,
    model_client: ModelClient,
    system_prompt: str | None,
    tools: Sequence[Any] | None = None,
    messages: Messages | None = None,
) -> Agent:
    """Construct a Strands Agent configured with the session parameters."""

    if not model_client:
        raise AgentBuildError("Model client is required to build an agent.")
    conversation_manager = build_conversation_manager(session_config)
    return Agent(
        model=model_client.client,
        system_prompt=system_prompt,
        tools=list(tools or ()),
        conversation_manager=conversation_manager,
        load_tools_from_directory=False,
        messages=messages,
    )

