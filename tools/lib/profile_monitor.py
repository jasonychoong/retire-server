"""Live profile monitor CLI."""

from __future__ import annotations

import sys
import time
from collections import OrderedDict
from typing import Dict, List, Optional

from server.agents.tools.completeness_common import (
    CANONICAL_TOPICS,
    InformationRecord,
    read_information_records,
)
from server.tools.lib.monitor_utils import clear_screen, resolve_session_id
from server.tools.lib.session_store import SessionStore


POLL_INTERVAL_SECONDS = 2.0


def group_information(records: List[InformationRecord]) -> Dict[str, "OrderedDict[str, List[InformationRecord]]"]:
    """Group information records by topic -> subtopic in insertion order."""

    grouped: Dict[str, "OrderedDict[str, List[InformationRecord]]"] = {
        topic: OrderedDict() for topic in CANONICAL_TOPICS
    }
    for record in records:
        topic = record.get("topic")
        if topic not in grouped:
            continue
        subtopic = record.get("subtopic") or "(uncategorized)"
        bucket = grouped[topic].setdefault(subtopic, [])
        bucket.append(record)
    return grouped


def format_label(record: InformationRecord) -> str:
    """Format the record label using fact_type."""

    fact_type = record.get("fact_type") or "Fact"
    label = fact_type.replace("_", " ").strip().capitalize()
    return label or "Fact"


def render_grouped_records(grouped: Dict[str, "OrderedDict[str, List[InformationRecord]]"]) -> str:
    """Render the grouped structure into a printable string."""

    lines: List[str] = []
    for topic, subtopics in grouped.items():
        if not subtopics:
            continue
        lines.append(topic)
        for subtopic, records in subtopics.items():
            lines.append(f"    {subtopic}")
            for record in records:
                label = format_label(record)
                value = record.get("value", "[missing value]")
                lines.append(f"        {label}: {value}")
        lines.append("")
    return "\n".join(lines).rstrip()


def run_monitor(*, session: Optional[str] = None, poll_interval: float = POLL_INTERVAL_SECONDS) -> int:
    """Entry point used by the CLI script."""

    store = SessionStore()
    try:
        session_id = resolve_session_id(session, store)
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        print(str(exc), file=sys.stderr)
        return 1

    while True:
        records = read_information_records(session_id, store=store)
        clear_screen()
        if not records:
            print("awaiting data...")
            time.sleep(poll_interval)
            continue
        grouped = group_information(records)
        output = render_grouped_records(grouped)
        print(output or "awaiting data...")
        time.sleep(poll_interval)


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Live profile monitor.")
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


