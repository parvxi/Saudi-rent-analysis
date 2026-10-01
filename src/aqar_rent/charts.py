"""Chart title helpers for data-driven, claim-first English figures."""

from aqar_rent.analysis import summarize_listings


def claim_first_titles(cleaned):
    """Return chart titles supported by the supplied cleaned sample."""
    return summarize_listings(cleaned)["chart_titles"]
