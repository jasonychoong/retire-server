"""Shared helpers for CLI monitor utilities."""

from __future__ import annotations

import json
import select
import sys
from pathlib import Path
from typing import Dict, Optional

from server.tools.lib.session_store import SessionNotFoundError, SessionStore


CHAT_DIR = Path(__file__).resolve().parents[1] / ".chat"
USER_PROMPTS_PATH = CHAT_DIR / "user-prompts" / "explore-topic.json"


def clear_screen() -> None:
    """Clear the terminal screen using ANSI escape codes."""

    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


def resolve_session_id(session_arg: Optional[str], store: SessionStore) -> str:
    """Resolve the session ID to monitor based on CLI arguments or current session."""

    if session_arg:
        if not store.session_exists(session_arg):
            raise SessionNotFoundError(f"Session {session_arg} not found.")
        return session_arg

    current = store.get_current_session()
    if not current:
        raise SessionNotFoundError("No session is marked as current. Use --session to specify one explicitly.")
    return current.id


def read_input_with_timeout(prompt: str, timeout: float) -> Optional[str]:
    """Prompt the user and wait up to timeout seconds for a line of input."""

    sys.stdout.write(prompt)
    sys.stdout.flush()
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if not ready:
        sys.stdout.write("\n")
        sys.stdout.flush()
        return None
    line = sys.stdin.readline()
    if not line:
        return None
    return line.strip()


def load_topic_prompts(path: Path = USER_PROMPTS_PATH) -> Dict[str, str]:
    """Load topic recommendation prompts from disk."""

    if not path.exists():
        raise FileNotFoundError(f"Topic prompt file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Topic prompt file must contain an object mapping. Found: {type(data)}")
    return {str(key): str(value) for key, value in data.items()}


