"""Live completeness monitor CLI."""

from __future__ import annotations

import sys
import time
from typing import Dict, List, Optional, Tuple

from server.agents.tools.completeness_common import CANONICAL_TOPICS, ScoreEntry
from server.tools.lib.monitor_utils import (
    clear_screen,
    load_topic_prompts,
    read_input_with_timeout,
    resolve_session_id,
)
from server.tools.lib.session_store import SessionStore


POLL_INTERVAL_SECONDS = 2.0
ARROW_SCALE = 5  # one character per five points


def compute_latest_scores(snapshots: List[Dict[str, any]]) -> Dict[str, Optional[ScoreEntry]]:
    """Return the most recent score per canonical topic."""

    latest: Dict[str, Optional[ScoreEntry]] = {topic: None for topic in CANONICAL_TOPICS}
    for snapshot in snapshots:
        for entry in snapshot.get("scores", []):
            topic = entry.get("topic")
            score = entry.get("score")
            if topic in latest and isinstance(score, int):
                latest[topic] = {"topic": topic, "score": score, "reason": entry.get("reason")}
    return latest


def format_arrow(score: int) -> str:
    """Return a text arrow scaled to the score."""

    if score <= 0:
        return "|"
    segments = max(0, int(round(score / ARROW_SCALE)))
    if segments == 0:
        return "|"
    if segments == 1:
        return "|>"
    return "|" + ("=" * (segments - 1)) + ">"


def format_topic_line(index: int, topic: str, score: Optional[int]) -> str:
    """Render a single topic row."""

    label = f"{index}. {topic}".ljust(24)
    if score is None:
        return f"{label} | 0"
    arrow = format_arrow(score)
    if score == 0:
        return f"{label} {arrow} 0"
    return f"{label} {arrow} {score}"


def maybe_show_prompt(topic_index: int, prompts: Dict[str, str]) -> None:
    """Print the recommended prompt for a topic."""

    topic = CANONICAL_TOPICS[topic_index]
    prompt_text = prompts.get(topic)
    if not prompt_text:
        print(f"No recommended prompt found for topic '{topic}'.")
        return
    print()
    print(f"Recommended prompt for {topic}:")
    print(prompt_text)
    print()
    input("Copy the prompt above, then press Enter to continue monitoring...")


def run_monitor(*, session: Optional[str] = None, poll_interval: float = POLL_INTERVAL_SECONDS) -> int:
    """Entry point used by the CLI script."""

    store = SessionStore()
    try:
        session_id = resolve_session_id(session, store)
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        print(str(exc), file=sys.stderr)
        return 1

    try:
        prompts = load_topic_prompts()
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        print(f"Failed to load topic prompts: {exc}", file=sys.stderr)
        return 1

    from server.agents.tools.completeness_common import read_completeness_snapshots

    while True:
        snapshots = read_completeness_snapshots(session_id, store=store)
        clear_screen()
        if not snapshots:
            print("awaiting data...")
            time.sleep(poll_interval)
            continue

        latest = compute_latest_scores(snapshots)
        for idx, topic in enumerate(CANONICAL_TOPICS, start=1):
            entry = latest.get(topic)
            score = entry["score"] if entry else None
            print(format_topic_line(idx, topic, score))

        selection = read_input_with_timeout(
            "Help me explore a specific topic (enter number 1-8)> ",
            poll_interval,
        )
        if not selection:
            continue

        if selection.lower() in {"q", "quit", "exit"}:
            print("Exiting.")
            return 0
        if not selection.isdigit():
            print("Please enter a number between 1 and 8, or Ctrl-C to quit.")
            time.sleep(1)
            continue
        index = int(selection)
        if not 1 <= index <= len(CANONICAL_TOPICS):
            print("Please enter a number between 1 and 8.")
            time.sleep(1)
            continue
        maybe_show_prompt(index - 1, prompts)


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Live completeness monitor.")
    parser.add_argument("--session", help="Session ID to monitor. Defaults to current session.", default=None)
    parser.add_argument(
        "--interval",
        type=float,
        default=POLL_INTERVAL_SECONDS,
        help="Polling interval in seconds (default: %(default)s).",
    )
    args = parser.parse_args(argv)

    try:
        return run_monitor(session=args.session, poll_interval=args.interval)
    except KeyboardInterrupt:
        print("\nExiting.")
        return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


