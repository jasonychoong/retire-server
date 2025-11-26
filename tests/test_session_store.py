"""SessionStore unit tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.tools.lib.session_store import SessionNotFoundError, SessionStore


def test_create_session_initializes_structure(tmp_path: Path) -> None:
    store = SessionStore(base_dir=tmp_path / ".chat")
    record = store.create_session()

    session_dir = tmp_path / ".chat" / "sessions" / record.id
    history_file = session_dir / "history.json"
    metadata_file = session_dir / "metadata.json"

    assert session_dir.exists()
    assert json.loads(history_file.read_text()) == []
    assert json.loads(metadata_file.read_text()) == {}

    index_data = json.loads((tmp_path / ".chat" / "sessions" / "index.json").read_text())
    assert any(entry["id"] == record.id for entry in index_data)


def test_list_mark_and_delete_session(tmp_path: Path) -> None:
    store = SessionStore(base_dir=tmp_path / ".chat")
    record_one = store.create_session()
    record_two = store.create_session()

    store.mark_current(record_two.id)
    sessions = store.list_sessions()
    assert {record.id for record in sessions} == {record_one.id, record_two.id}
    assert next(record for record in sessions if record.id == record_two.id).is_current

    store.delete_session(record_one.id)
    remaining = store.list_sessions()
    assert len(remaining) == 1 and remaining[0].id == record_two.id


def test_update_description_requires_existing_session(tmp_path: Path) -> None:
    store = SessionStore(base_dir=tmp_path / ".chat")
    record = store.create_session()

    store.update_description(record.id, "First run")
    sessions = store.list_sessions()
    assert next(r for r in sessions if r.id == record.id).description == "First run"

    with pytest.raises(SessionNotFoundError):
        store.update_description("missing", "oops")


