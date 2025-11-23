"""Agent runtime helpers used by the CLI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Sequence

from server.agents.chat.model_registry import ModelClient
from server.tools.lib import SessionConfig


class AgentBuildError(RuntimeError):
    """Raised when an agent cannot be constructed."""


@dataclass
class SlidingWindowConversationManager:
    """Minimal sliding window manager mirroring Strands behavior for the spike."""

    window_size: int
    should_truncate_results: bool

    def prepare_messages(self, history: Sequence[dict[str, Any]]) -> List[dict[str, Any]]:
        """Return the subset of history that should be sent to the model."""

        if not history:
            return []
        if self.window_size <= 0:
            return list(history)
        trimmed = list(history[-self.window_size :])
        if not self.should_truncate_results:
            return list(history)
        return trimmed


@dataclass
class ChatAgent:
    """Lightweight agent façade until the full Strands stack is wired in."""

    model_client: ModelClient
    conversation_manager: SlidingWindowConversationManager
    system_prompt: str | None = None
    tools: Sequence[Any] = field(default_factory=tuple)

    def build_payload(self, history: Sequence[dict[str, Any]]) -> dict[str, Any]:
        """Prepare a payload that the downstream model client can consume."""

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.extend(self.conversation_manager.prepare_messages(history))
        return {
            "model": self.model_client.model_id,
            "messages": messages,
            "tools": list(self.tools),
        }


def build_conversation_manager(config: SessionConfig) -> SlidingWindowConversationManager:
    """Instantiate the sliding window manager for the effective session config."""

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
) -> ChatAgent:
    """Construct a ChatAgent wrapper for the configured model."""

    if not model_client:
        raise AgentBuildError("Model client is required to build an agent.")
    conversation_manager = build_conversation_manager(session_config)
    return ChatAgent(
        model_client=model_client,
        conversation_manager=conversation_manager,
        system_prompt=system_prompt,
        tools=tuple(tools or ()),
    )

