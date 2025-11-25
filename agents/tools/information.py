"""Tool for persisting structured retirement information facts."""

from __future__ import annotations

from strands import tool

from server.agents.tools import completeness_common as common


def _validate_confidence(confidence: float) -> float:
    if not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")
    return confidence


@tool
def information(
    topic: str,
    value: str,
    subtopic: str | None = None,
    fact_type: str | None = None,
    confidence: float = 0.9,
) -> str:
    """Persist a new piece of retirement-planning information for this session."""

    session_id = common.current_session_id()
    record = common.append_information_record(
        session_id=session_id,
        topic=topic,
        value=value,
        subtopic=subtopic,
        fact_type=fact_type,
        confidence=_validate_confidence(confidence),
    )
    return f"Recorded information for topic '{record['topic']}'."


