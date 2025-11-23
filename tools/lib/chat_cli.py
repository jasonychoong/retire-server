"""CLI helpers for managing local chat sessions."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from server.tools.lib import (
    ConfigError,
    SessionConfig,
    SessionNotFoundError,
    SessionStore,
    load_base_config,
    session_config_from_metadata,
)


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
    parser.add_argument("--model", type=str, help="Override the model for this invocation.")
    parser.add_argument("--window-size", type=int, help="Override the sliding window size.")
    parser.add_argument(
        "--should-truncate-results",
        type=str,
        help="Override the truncate-results flag (true/false).",
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


def resolve_config(store: SessionStore, session_id: str, args: argparse.Namespace) -> SessionConfig:
    metadata = {}
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
    store.write_metadata(session_id, metadata)
    return effective


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
        config = resolve_config(store, session_id, args)
    except (ConfigError, ValueError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1

    print(f"Active session: {session_id}")
    print(f"Model: {config.model}")
    print(f"Window size: {config.window_size}")
    print(f"Should truncate results: {config.should_truncate_results}")
    print("Chat functionality will be added in Task 3 – this command currently handles setup only.")
    return 0

