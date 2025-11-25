"""Shared helpers and schemas for completeness-related tools."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

from strands import tool  # noqa: F401  # re-export convenience

from server.tools.lib.session_store import SessionStore, SessionNotFoundError


CANONICAL_TOPICS = [
    "income_cash_flow",
    "healthcare_medicare",
    "housing_geography",
    "tax_efficiency_rmds",
    "longevity_inflation",
    "long_term_care",
    "lifestyle_purpose",
    "estate_planning",
]

INFORMATION_FILENAME = "information.jsonl"
COMPLETENESS_FILENAME = "completeness.jsonl"


class InformationRecord(TypedDict, total=False):
    id: str
    session_id: str
    topic: str
    subtopic: Optional[str]
    fact_type: Optional[str]
    value: str
    confidence: float
    created_at: str


class ScoreEntry(TypedDict, total=False):
    topic: str
    score: int
    reason: Optional[str]


class CompletenessSnapshot(TypedDict):
    session_id: str
    scores: List[ScoreEntry]
    created_at: str


def validate_topic(topic: str) -> str:
    if topic not in CANONICAL_TOPICS:
        raise ValueError(f"Invalid topic '{topic}'. Expected one of: {', '.join(CANONICAL_TOPICS)}")
    return topic


def current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_information_record(
    session_id: str,
    topic: str,
    value: str,
    *,
    subtopic: Optional[str] = None,
    fact_type: Optional[str] = None,
    confidence: float = 0.9,
    store: Optional[SessionStore] = None,
) -> InformationRecord:
    record: InformationRecord = {
        "session_id": session_id,
        "topic": validate_topic(topic),
        "value": value,
        "subtopic": subtopic,
        "fact_type": fact_type,
        "confidence": confidence,
        "created_at": current_timestamp(),
    }
    _append_jsonl(session_id, INFORMATION_FILENAME, record, store=store)
    return record


def append_completeness_snapshot(
    session_id: str,
    scores: List[ScoreEntry],
    *,
    store: Optional[SessionStore] = None,
) -> CompletenessSnapshot:
    validated_scores: List[ScoreEntry] = []
    for entry in scores:
        topic = validate_topic(entry["topic"])
        score = entry["score"]
        if not isinstance(score, int) or not 0 <= score <= 100:
            raise ValueError(f"Score for topic '{topic}' must be an integer between 0 and 100.")
        validated_scores.append({"topic": topic, "score": score, "reason": entry.get("reason")})

    snapshot: CompletenessSnapshot = {
        "session_id": session_id,
        "scores": validated_scores,
        "created_at": current_timestamp(),
    }
    _append_jsonl(session_id, COMPLETENESS_FILENAME, snapshot, store=store)
    return snapshot


def read_information_records(
    session_id: str,
    *,
    store: Optional[SessionStore] = None,
) -> List[InformationRecord]:
    return _read_jsonl(session_id, INFORMATION_FILENAME, store=store)


def read_completeness_snapshots(
    session_id: str,
    *,
    store: Optional[SessionStore] = None,
) -> List[CompletenessSnapshot]:
    return _read_jsonl(session_id, COMPLETENESS_FILENAME, store=store)


def _append_jsonl(
    session_id: str,
    filename: str,
    payload: Dict[str, Any],
    store: Optional[SessionStore] = None,
) -> None:
    store = store or SessionStore()
    if not store.session_exists(session_id):
        raise SessionNotFoundError(f"Session {session_id} not found")
    store.append_jsonl(session_id, filename, payload)


def _read_jsonl(session_id: str, filename: str, store: Optional[SessionStore] = None):
    store = store or SessionStore()
    if not store.session_exists(session_id):
        raise SessionNotFoundError(f"Session {session_id} not found")
    return store.read_jsonl(session_id, filename)


