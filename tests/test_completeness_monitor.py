from server.agents.tools.completeness_common import CANONICAL_TOPICS
from server.tools.lib import completeness_monitor as cm


def test_compute_latest_scores_picks_last_entries():
    snapshots = [
        {"scores": [{"topic": "income_cash_flow", "score": 30}]},
        {
            "scores": [
                {"topic": "income_cash_flow", "score": 70},
                {"topic": "housing_geography", "score": 50},
            ]
        },
    ]

    latest = cm.compute_latest_scores(snapshots)

    assert latest["income_cash_flow"]["score"] == 70
    assert latest["housing_geography"]["score"] == 50
    assert latest["tax_efficiency_rmds"] is None


def test_format_arrow_rounds_and_scales():
    assert cm.format_arrow(0) == "|"
    assert cm.format_arrow(5) == "|>"
    assert cm.format_arrow(12) == "|=>"


def test_format_topic_line_handles_missing_scores():
    line_with_score = cm.format_topic_line(1, CANONICAL_TOPICS[0], 85)
    assert "85" in line_with_score
    assert "=>" in line_with_score

    line_missing = cm.format_topic_line(2, CANONICAL_TOPICS[1], None)
    assert line_missing.endswith("| 0")


