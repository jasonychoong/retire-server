"""Tool for querying persisted retirement information facts."""

from __future__ import annotations

from typing import List

from strands import tool

from server.agents.tools import completeness_common as common


@tool
def information_query() -> List[common.InformationRecord]:
    """Fetch all persisted information records for the current session."""

    session_id = common.current_session_id()
    return common.read_information_records(session_id)



