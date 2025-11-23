"""CLI helpers for managing local chat sessions."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from server.agents.chat import (
    MODEL_REGISTRY,
    ModelRegistryError,
    build_agent,
    create_model_client,
)
from strands.types.content import Messages
from server.tools.lib import (
    ConfigError,
    SessionConfig,
    SessionNotFoundError,
    SessionStore,
    SessionStoreError,
    load_base_config,
    session_config_from_metadata,
)

HISTORY_DISPLAY_LIMIT = 10
EXIT_COMMANDS = {"exit", "/exit", "quit", ":q"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local retirement chat prototype utilities (session management foundation)."
    )
    parser.add_argument("--list-sessions", action="store_true", help="List known sessions and exit.")
    parser.add_argument("--new-session", action="store_true", help="Create a new session before running.")
    parser.add_argument("--session", type=str, help="Target an existing session by UUID.")
    parser.add_argument("--description", type=str, help="Update the description for --session.")
    parser.add_argument("--delete-session", type=str, metavar="UUID", help="Delete the specified session and exit.")
    parser.add_argument("--config-file", type=str, help="Override the default config.yaml path.")
    parser.add_argument(
        "--model",
        type=str,
        help=f"Override the model (supported: {', '.join(sorted(MODEL_REGISTRY))}).",
    )
    parser.add_argument("--window-size", type=int, help="Override the sliding window size.")
    parser.add_argument(
        "--should-truncate-results",
        type=str,
        help="Override the truncate-results flag (true/false).",
    )
    parser.add_argument("--system-prompt", type=str, help="Inline system prompt for this session.")
    parser.add_argument(
        "--system-prompt-file",
        type=str,
        help="Path to a file containing the system prompt text.",
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Run a single-turn interaction (default is interactive mode).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print verbose diagnostics to stdout in addition to standard output.",
    )
    return parser.parse_args()


def render_session_table(store: SessionStore) -> None:
    records = store.list_sessions()
    if not records:
        print("No sessions found.")
        return
    headers = ("Current", "Session ID", "Created (UTC)", "Description")
    rows = []
    for record in sorted(records, key=lambda rec: rec.created_at):
        rows.append(
            (
                "*" if record.is_current else "",
                record.id,
                record.created_at,
                record.description or "",
            )
        )
    column_widths = [
        max(len(str(value)) for value in column)
        for column in zip(headers, *(row for row in rows))
    ]
    header_line = " | ".join(header.ljust(column_widths[idx]) for idx, header in enumerate(headers))
    separator = "-+-".join("-" * column_widths[idx] for idx in range(len(headers)))
    print(header_line)
    print(separator)
    for row in rows:
        print(" | ".join(str(value).ljust(column_widths[idx]) for idx, value in enumerate(row)))


def parse_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "t", "yes", "y"}:
        return True
    if normalized in {"0", "false", "f", "no", "n"}:
        return False
    raise ValueError(f"Invalid boolean flag value: {value}")


def resolve_session(store: SessionStore, args: argparse.Namespace) -> str:
    if args.new_session:
        record = store.create_session()
        session_id = record.id
    else:
        session_id = args.session or os.environ.get("RETIRE_CURRENT_SESSION_ID")
        if not session_id:
            record = store.create_session()
            session_id = record.id
        elif not store.session_exists(session_id):
            raise SessionNotFoundError(f"Session {session_id} does not exist")
    store.mark_current(session_id)
    os.environ["RETIRE_CURRENT_SESSION_ID"] = session_id
    return session_id


def resolve_config(
    store: SessionStore, session_id: str, args: argparse.Namespace
) -> Tuple[SessionConfig, Dict[str, Any]]:
    metadata: Dict[str, Any] = {}
    if store.session_exists(session_id):
        metadata = store.read_metadata(session_id)
    base_config = session_config_from_metadata(metadata)
    if base_config is None or args.new_session:
        base_config = load_base_config(Path(args.config_file) if args.config_file else None)
    overrides: dict[str, Optional[object]] = {
        "model": args.model,
        "window_size": args.window_size,
        "should_truncate_results": parse_bool(args.should_truncate_results),
    }
    effective = base_config.apply_overrides(
        model=overrides["model"],
        window_size=overrides["window_size"],
        should_truncate_results=overrides["should_truncate_results"],
    )
    metadata["config"] = effective.to_dict()
    return effective, metadata


def resolve_system_prompt(
    store: SessionStore, session_id: str, metadata: Dict[str, Any], args: argparse.Namespace
) -> Optional[str]:
    inline_prompt = args.system_prompt
    file_prompt = args.system_prompt_file
    if inline_prompt and file_prompt:
        raise ValueError("Provide only one of --system-prompt or --system-prompt-file.")

    previous_text = metadata.get("system_prompt_text")
    previous_source = metadata.get("system_prompt_source")
    previous_file_path = metadata.get("system_prompt_file_path")

    if file_prompt:
        prompt_path = Path(file_prompt).expanduser()
        if not prompt_path.exists():
            raise FileNotFoundError(f"System prompt file not found: {prompt_path}")
        prompt_text = prompt_path.read_text(encoding="utf-8")
        source = "file"
        file_path = str(prompt_path.resolve())
    elif inline_prompt is not None:
        prompt_text = inline_prompt
        source = "inline"
        file_path = None
    else:
        # No changes requested; return previous state.
        return previous_text

    if prompt_text == previous_text and source == previous_source and file_path == previous_file_path:
        return prompt_text

    metadata["system_prompt_text"] = prompt_text
    metadata["system_prompt_source"] = source
    metadata["system_prompt_file_path"] = file_path
    metadata["system_prompt_updated_at"] = datetime.now(timezone.utc).isoformat()
    _append_system_prompt_history(store, session_id, prompt_text)
    return prompt_text


def _append_system_prompt_history(store: SessionStore, session_id: str, prompt_text: str) -> None:
    history = store.read_history(session_id)
    last_system = next((item for item in reversed(history) if item.get("role") == "system"), None)
    if last_system and last_system.get("content") == prompt_text:
        return
    history.append(
        {
            "role": "system",
            "content": prompt_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    store.write_history(session_id, history)


def load_tools() -> List[Any]:
    """Placeholder for Task 4 tool loading."""

    return []


def history_to_agent_messages(history: List[Dict[str, Any]]) -> Messages:
    """Convert stored history entries into Strands Agent message objects."""

    agent_messages: Messages = []
    for entry in history:
        role = entry.get("role")
        if role not in {"user", "assistant"}:
            continue
        content = entry.get("content")
        if not isinstance(content, str):
            continue
        agent_messages.append({"role": role, "content": [{"text": content}]})
    return agent_messages


def extract_text_from_message(message: Dict[str, Any]) -> str:
    """Concatenate text blocks from a Strands message."""

    chunks: List[str] = []
    for block in message.get("content", []):
        if isinstance(block, dict) and "text" in block:
            text = block.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks).strip()


def verbose_print(enabled: bool, message: str) -> None:
    """Print a verbose message when enabled."""

    if enabled:
        print(f"[verbose] {message}")


def print_history_overview(history: List[Dict[str, Any]]) -> None:
    """Display a short summary of the existing conversation."""

    if not history:
        print("No previous conversation history.")
        return

    print("Previous conversation:")
    for entry in history[-HISTORY_DISPLAY_LIMIT:]:
        role = entry.get("role", "system")
        label = {
            "user": "You",
            "assistant": "Assistant",
            "system": "System",
        }.get(role, role.title())
        content = entry.get("content", "")
        print(f"{label}: {content}")


def collect_single_input(prompt: str = "You> ") -> Optional[str]:
    """Collect a single line of input from stdin or the terminal."""

    if not sys.stdin.isatty():
        data = sys.stdin.read().strip()
        return data or None
    try:
        value = input(prompt)
    except EOFError:
        return None
    return value.strip() or None


def run_single_turn(
    *,
    agent: Any,
    store: SessionStore,
    session_id: str,
    history: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    verbose: bool,
) -> int:
    """Execute a single user→assistant turn."""

    user_input = collect_single_input()
    if not user_input:
        print("No input provided; exiting.", file=sys.stderr)
        return 1

    response = execute_turn(
        agent=agent,
        store=store,
        session_id=session_id,
        history=history,
        metadata=metadata,
        user_input=user_input,
        verbose=verbose,
    )
    if response is None:
        return 1
    print(f"Assistant: {response}")
    return 0


def run_interactive_loop(
    *,
    agent: Any,
    store: SessionStore,
    session_id: str,
    history: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    verbose: bool,
) -> int:
    """Enter interactive chat mode until the user exits."""

    print_history_overview(history)
    print("Enter '/exit' or press Ctrl-D to leave the session.")
    while True:
        try:
            user_input = input("You> ").strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print("\nInterrupted.")
            break

        if not user_input:
            continue
        if user_input.lower() in EXIT_COMMANDS:
            break

        response = execute_turn(
            agent=agent,
            store=store,
            session_id=session_id,
            history=history,
            metadata=metadata,
            user_input=user_input,
            verbose=verbose,
        )
        if response is not None:
            print(f"Assistant: {response}")

    return 0


def execute_turn(
    *,
    agent: Any,
    store: SessionStore,
    session_id: str,
    history: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    user_input: str,
    verbose: bool,
) -> Optional[str]:
    """Run a single agent invocation and persist history/metadata."""

    user_entry = append_history_entry(store, session_id, history, "user", user_input)

    try:
        result = agent(user_input)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"Agent execution failed: {exc}", file=sys.stderr)
        metadata.setdefault("errors", []).append(
            {"timestamp": user_entry["timestamp"], "message": str(exc)}
        )
        store.write_metadata(session_id, metadata)
        return None

    response_text = extract_text_from_message(result.message) or "[No response]"
    assistant_entry = append_history_entry(store, session_id, history, "assistant", response_text)
    record_turn_metadata(metadata, result, user_entry, assistant_entry)
    store.write_metadata(session_id, metadata)

    usage = getattr(result.metrics, "accumulated_usage", None)
    if usage:
        input_tokens, output_tokens, total_tokens = coerce_usage_counts(usage)
        verbose_print(
            verbose,
            f"tokens in={input_tokens} out={output_tokens} total={total_tokens}",
        )
    verbose_print(verbose, f"stop reason: {result.stop_reason}")
    return response_text


def record_turn_metadata(
    metadata: Dict[str, Any],
    result: Any,
    user_entry: Dict[str, Any],
    assistant_entry: Dict[str, Any],
) -> None:
    """Persist per-turn metadata for later inspection."""

    turn_log = metadata.setdefault("turns", [])
    usage = getattr(result.metrics, "accumulated_usage", None)
    usage_payload: Dict[str, Any] | None = None
    if usage:
        input_tokens, output_tokens, total_tokens = coerce_usage_counts(usage)
        usage_payload = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }

    turn_log.append(
        {
            "timestamp": assistant_entry.get("timestamp"),
            "user": user_entry.get("content"),
            "assistant": assistant_entry.get("content"),
            "stop_reason": str(getattr(result, "stop_reason", "")),
            "usage": usage_payload,
        }
    )
    metadata["last_response"] = assistant_entry.get("content")
    metadata["last_stop_reason"] = str(getattr(result, "stop_reason", ""))


def append_history_entry(
    store: SessionStore,
    session_id: str,
    history: List[Dict[str, Any]],
    role: str,
    content: str,
) -> Dict[str, Any]:
    """Append a message to the in-memory and on-disk history."""

    entry = {
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    history.append(entry)
    store.write_history(session_id, history)
    return entry


def coerce_usage_counts(usage: Any) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """Extract token usage whether result is a dataclass or dict."""

    if isinstance(usage, dict):
        return (
            usage.get("inputTokens") or usage.get("input_tokens"),
            usage.get("outputTokens") or usage.get("output_tokens"),
            usage.get("totalTokens") or usage.get("total_tokens"),
        )
    return (
        getattr(usage, "inputTokens", None),
        getattr(usage, "outputTokens", None),
        getattr(usage, "totalTokens", None),
    )


def main() -> int:
    args = parse_args()
    store = SessionStore()

    if args.list_sessions:
        render_session_table(store)
        return 0

    if args.delete_session:
        try:
            store.delete_session(args.delete_session)
        except SessionNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"Deleted session {args.delete_session}")
        return 0

    if args.description and not args.session:
        print("--description requires --session=<UUID>", file=sys.stderr)
        return 2

    if args.description:
        try:
            store.update_description(args.session, args.description)
        except SessionNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"Updated description for session {args.session}")
        return 0

    try:
        session_id = resolve_session(store, args)
    except SessionNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        config, metadata = resolve_config(store, session_id, args)
    except (ConfigError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    try:
        system_prompt = resolve_system_prompt(store, session_id, metadata, args)
    except (ValueError, OSError) as exc:
        print(f"System prompt error: {exc}", file=sys.stderr)
        return 1

    store.write_metadata(session_id, metadata)

    effective_system_prompt = system_prompt if system_prompt is not None else metadata.get("system_prompt_text")

    try:
        history = store.read_history(session_id)
    except SessionStoreError as exc:
        print(f"Unable to read session history: {exc}", file=sys.stderr)
        return 1

    agent_messages = history_to_agent_messages(history)

    try:
        model_client = create_model_client(config.model)
    except ModelRegistryError as exc:
        print(f"Model configuration error: {exc}", file=sys.stderr)
        return 1

    agent = build_agent(
        session_config=config,
        model_client=model_client,
        system_prompt=effective_system_prompt,
        tools=load_tools(),
        messages=agent_messages,
    )

    print(f"Active session: {session_id}")
    print(f"Model: {config.model}")
    print(f"Window size: {config.window_size}")
    print(f"Should truncate results: {config.should_truncate_results}")
    if effective_system_prompt:
        source = metadata.get("system_prompt_source", "unknown")
        location = metadata.get("system_prompt_file_path") or "inline text"
        print(f"System prompt ({source}): {location}")

    if args.single:
        status = run_single_turn(
            agent=agent,
            store=store,
            session_id=session_id,
            history=history,
            metadata=metadata,
            verbose=args.verbose,
        )
    else:
        status = run_interactive_loop(
            agent=agent,
            store=store,
            session_id=session_id,
            history=history,
            metadata=metadata,
            verbose=args.verbose,
        )

    print(f"Session ID: {session_id}")
    return status

