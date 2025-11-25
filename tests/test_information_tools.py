"""Tests for information and information_query tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from server.agents.tools import completeness_common as common
from server.agents.tools import information, information_query
from server.tools.lib.session_store import SessionStore


@pytest.fixture()
def session_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store = SessionStore(base_dir=tmp_path / ".chat")
    session = store.create_session()
    monkeypatch.setenv("RETIRE_CURRENT_SESSION_ID", session.id)
    monkeypatch.setattr(common, "SessionStore", lambda base_dir=None: store)
    return store, session.id


def test_information_writes_record(session_env: tuple[SessionStore, str]) -> None:
    store, session_id = session_env

    confirmation = information.information(
        topic="income_cash_flow",
        value="Target retirement age 60",
        subtopic="retirement_age",
        fact_type="goal_age",
        confidence=0.75,
    )

    assert "income_cash_flow" in confirmation

    records = common.read_information_records(session_id, store=store)
    assert len(records) == 1
    record = records[0]
    assert record["value"] == "Target retirement age 60"
    assert record["fact_type"] == "goal_age"
    assert record["confidence"] == 0.75


def test_information_rejects_invalid_confidence(session_env: tuple[SessionStore, str]) -> None:
    with pytest.raises(ValueError):
        information.information(topic="income_cash_flow", value="data", confidence=2.0)


def test_information_query_returns_records(session_env: tuple[SessionStore, str]) -> None:
    store, _ = session_env
    information.information(topic="income_cash_flow", value="Budget set")
    information.information(topic="tax_efficiency_rmds", value="Roth conversions ongoing")

    records = information_query.information_query()
    assert len(records) == 2
    assert records[0]["topic"] == "income_cash_flow"
    assert records[1]["topic"] == "tax_efficiency_rmds"


