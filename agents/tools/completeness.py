"""Tool for persisting completeness score snapshots."""

from __future__ import annotations

from typing import Any

from strands import tool

from server.agents.tools import completeness_common as common


@tool
def completeness(scores: list[dict[str, Any]]) -> str:
    """Persist a completeness snapshot for one or more topics."""

    if not isinstance(scores, list) or not scores:
        raise ValueError("scores must be a non-empty list of topic score objects")

    normalized: list[dict[str, Any]] = []
    for entry in scores:
        if not isinstance(entry, dict):
            raise ValueError("Each score entry must be a dict with 'topic' and 'score'")
        topic = entry.get("topic")
        score = entry.get("score")
        reason = entry.get("reason")
        if topic is None or score is None:
            raise ValueError("Each score entry must include 'topic' and 'score'")
        normalized.append({"topic": str(topic), "score": int(score), "reason": reason})

    session_id = common.current_session_id()
    common.append_completeness_snapshot(session_id, normalized)
    topics = ", ".join(entry["topic"] for entry in normalized)
    return f"Completeness snapshot stored for topics: {topics}"


