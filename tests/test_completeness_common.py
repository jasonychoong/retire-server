"""Tests for completeness_common helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.agents.tools import completeness_common as common
from server.tools.lib.session_store import SessionStore, SessionNotFoundError


def test_validate_topic_accepts_known_values() -> None:
    for topic in common.CANONICAL_TOPICS:
        assert common.validate_topic(topic) == topic


def test_validate_topic_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        common.validate_topic("unknown_topic")


def test_append_and_read_information_records(tmp_path: Path) -> None:
    store = SessionStore(base_dir=tmp_path / ".chat")
    session = store.create_session()

    record = common.append_information_record(
        session.id,
        topic="income_cash_flow",
        value="Retire at 55",
        subtopic="retirement_age",
        fact_type="goal_age",
        confidence=0.8,
        store=store,
    )

    assert record["topic"] == "income_cash_flow"
    assert record["value"] == "Retire at 55"
    assert isinstance(record["created_at"], str)

    contents = common.read_information_records(session.id, store=store)
    assert contents == [record]


def test_append_and_read_completeness_snapshots(tmp_path: Path) -> None:
    store = SessionStore(base_dir=tmp_path / ".chat")
    session = store.create_session()

    snapshot = common.append_completeness_snapshot(
        session.id,
        scores=[{"topic": "income_cash_flow", "score": 80, "reason": "Collected budget"}],
        store=store,
    )
    assert snapshot["scores"][0]["score"] == 80

    snapshots = common.read_completeness_snapshots(session.id, store=store)
    assert snapshots == [snapshot]


def test_completeness_snapshot_validates_score_range(tmp_path: Path) -> None:
    store = SessionStore(base_dir=tmp_path / ".chat")
    session = store.create_session()

    with pytest.raises(ValueError):
        common.append_completeness_snapshot(
            session.id,
            scores=[{"topic": "income_cash_flow", "score": 150}],
            store=store,
        )


def test_helpers_require_existing_session(tmp_path: Path) -> None:
    store = SessionStore(base_dir=tmp_path / ".chat")

    with pytest.raises(SessionNotFoundError):
        common.read_information_records("missing", store=store)


