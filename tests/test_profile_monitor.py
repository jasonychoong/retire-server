from server.tools.lib import profile_monitor as pm


def test_group_information_orders_by_topic_and_subtopic():
    records = [
        {"topic": "income_cash_flow", "subtopic": "ages", "value": "User 54", "fact_type": "age_fact"},
        {
            "topic": "income_cash_flow",
            "subtopic": "ages",
            "value": "Spouse 48",
            "fact_type": "age_fact",
        },
        {
            "topic": "housing_geography",
            "subtopic": "future_moves",
            "value": "Sell rental",
            "fact_type": "plan",
        },
    ]

    grouped = pm.group_information(records)

    assert "ages" in grouped["income_cash_flow"]
    assert len(grouped["income_cash_flow"]["ages"]) == 2
    assert "future_moves" in grouped["housing_geography"]


def test_format_label_defaults_and_capitalizes():
    assert pm.format_label({"fact_type": "goal_focus"}) == "Goal focus"
    assert pm.format_label({}) == "Fact"


def test_render_grouped_records_outputs_hierarchy():
    records = [
        {"topic": "income_cash_flow", "subtopic": "retirement_timing", "value": "Next year", "fact_type": "goal"},
    ]
    grouped = pm.group_information(records)
    rendered = pm.render_grouped_records(grouped)

    assert "income_cash_flow" in rendered
    assert "retirement_timing" in rendered
    assert "Goal" in rendered


