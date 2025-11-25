"""Local session persistence utilities for the chat CLI."""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


CHAT_DIR = Path(__file__).resolve().parents[1] / ".chat"
SESSIONS_DIRNAME = "sessions"
HISTORY_FILENAME = "history.json"
METADATA_FILENAME = "metadata.json"
INDEX_FILENAME = "index.json"


class SessionStoreError(RuntimeError):
    """Base error for session store failures."""


class SessionNotFoundError(SessionStoreError):
    """Raised when a requested session cannot be located on disk."""


@dataclass
class SessionRecord:
    """Lightweight representation of a session entry."""

    id: str
    created_at: str
    description: Optional[str] = None
    is_current: bool = False

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "SessionRecord":
        return cls(
            id=payload["id"],
            created_at=payload["created_at"],
            description=payload.get("description"),
            is_current=payload.get("is_current", False),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SessionStore:
    """Manages session directories and indexes on the local filesystem."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or CHAT_DIR
        self.sessions_dir = self.base_dir / SESSIONS_DIRNAME
        self.index_file = self.sessions_dir / INDEX_FILENAME
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        if not self.index_file.exists():
            self._write_index([])

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def list_sessions(self) -> List[SessionRecord]:
        return self._read_index()

    def create_session(self, description: Optional[str] = None) -> SessionRecord:
        session_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        record = SessionRecord(
            id=session_id,
            created_at=created_at,
            description=description,
            is_current=False,
        )
        session_dir = self._session_dir(session_id)
        session_dir.mkdir(parents=True, exist_ok=False)
        self.write_history(session_id, [])
        self.write_metadata(session_id, {})
        sessions = self._read_index()
        sessions.append(record)
        self._write_index(sessions)
        return record

    def session_exists(self, session_id: str) -> bool:
        return self._session_dir(session_id).exists()

    def mark_current(self, session_id: str) -> None:
        updated = False
        sessions = self._read_index()
        for record in sessions:
            record.is_current = record.id == session_id
            if record.is_current:
                updated = True
        if not updated:
            raise SessionNotFoundError(f"Session {session_id} not found")
        self._write_index(sessions)

    def get_current_session(self) -> Optional[SessionRecord]:
        """Return the session marked as current, if any."""

        for record in self._read_index():
            if record.is_current:
                return record
        return None

    def update_description(self, session_id: str, description: str) -> None:
        changed = False
        sessions = self._read_index()
        for record in sessions:
            if record.id == session_id:
                record.description = description
                changed = True
                break
        if not changed:
            raise SessionNotFoundError(f"Session {session_id} not found")
        self._write_index(sessions)

    def delete_session(self, session_id: str) -> None:
        session_dir = self._session_dir(session_id)
        if not session_dir.exists():
            raise SessionNotFoundError(f"Session {session_id} not found")
        shutil.rmtree(session_dir)
        sessions = [record for record in self._read_index() if record.id != session_id]
        self._write_index(sessions)

    def read_history(self, session_id: str) -> List[Dict[str, Any]]:
        return self._read_json_file(self._history_file(session_id))

    def write_history(self, session_id: str, history: List[Dict[str, Any]]) -> None:
        self._write_json_file(self._history_file(session_id), history)

    def read_metadata(self, session_id: str) -> Dict[str, Any]:
        return self._read_json_file(self._metadata_file(session_id))

    def write_metadata(self, session_id: str, data: Dict[str, Any]) -> None:
        self._write_json_file(self._metadata_file(session_id), data)

    def session_directory(self, session_id: str) -> Path:
        """Return the root directory for the given session."""

        return self._session_dir(session_id)

    def append_jsonl(self, session_id: str, filename: str, payload: Dict[str, Any]) -> None:
        """Append a JSON-serializable payload to a *.jsonl file under the session."""

        target_file = self._session_dir(session_id) / filename
        target_file.parent.mkdir(parents=True, exist_ok=True)
        with target_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload))
            handle.write("\n")

    def read_jsonl(self, session_id: str, filename: str) -> List[Dict[str, Any]]:
        """Read a jsonl file under the session, returning a list of parsed dicts."""

        target_file = self._session_dir(session_id) / filename
        if not target_file.exists():
            return []
        records: List[Dict[str, Any]] = []
        with target_file.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                records.append(json.loads(line))
        return records

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _session_dir(self, session_id: str) -> Path:
        return self.sessions_dir / session_id

    def _history_file(self, session_id: str) -> Path:
        return self._session_dir(session_id) / HISTORY_FILENAME

    def _metadata_file(self, session_id: str) -> Path:
        return self._session_dir(session_id) / METADATA_FILENAME

    def _read_index(self) -> List[SessionRecord]:
        data = self._read_json_file(self.index_file)
        if isinstance(data, dict) and "sessions" in data:
            # Support early format experiments.
            data = data["sessions"]
        return [SessionRecord.from_dict(item) for item in data]

    def _write_index(self, records: List[SessionRecord]) -> None:
        payload = [record.to_dict() for record in records]
        self._write_json_file(self.index_file, payload)

    def _read_json_file(self, path: Path) -> Any:
        if not path.exists():
            raise SessionStoreError(f"Expected file missing: {path}")
        with path.open("r", encoding="utf-8") as handle:
            if path.stat().st_size == 0:
                return [] if path.name == HISTORY_FILENAME else {}
            return json.load(handle)

    def _write_json_file(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")

