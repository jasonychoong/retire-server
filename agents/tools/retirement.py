"""Simple retirement-planning helper tools."""

from __future__ import annotations

from strands import tool


@tool
def retirement_readiness(age: int, savings: float, monthly_spend: float, target_years: int = 25) -> str:
    """Estimate a quick retirement readiness score.

    Args:
        age: Current age of the client (years).
        savings: Total liquid retirement savings (USD).
        monthly_spend: Current monthly spending (USD).
        target_years: Number of retirement years to fund (defaults to 25).

    Returns:
        A short qualitative assessment with a suggested next step.
    """

    annual_spend = monthly_spend * 12
    required_fund = annual_spend * target_years
    funding_ratio = savings / required_fund if required_fund else 0

    if funding_ratio >= 1.1:
        status = "on_track"
        recommendation = (
            "You appear to have enough savings to cover the target horizon. "
            "Stress-test the plan with market variability and healthcare costs."
        )
    elif funding_ratio >= 0.75:
        status = "needs_adjustment"
        recommendation = (
            "You're within striking distance. Consider increasing savings, "
            "delaying retirement a few years, or trimming monthly spend."
        )
    else:
        status = "shortfall"
        recommendation = (
            "Current savings are well below the target. Revisit contributions, "
            "lifestyle assumptions, or explore part-time retirement income."
        )

    return (
        f"Status: {status} — Funding ratio {funding_ratio:.0%}. "
        f"Estimated requirement ${required_fund:,.0f}. {recommendation}"
    )



