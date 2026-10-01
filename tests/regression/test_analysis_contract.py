import pandas as pd
import pytest

from aqar_rent.analysis import summarize_listings


@pytest.mark.regression
def test_city_counts_and_chart_claims_are_stable_for_synthetic_sample() -> None:
    frame = pd.DataFrame(
        [
            {
                "city": "Dammam",
                "price": 50_000,
                "size": 100,
                "bedrooms": 2,
                "analysis_eligible": True,
            },
            {
                "city": "Dammam",
                "price": 55_000,
                "size": 150,
                "bedrooms": 3,
                "analysis_eligible": True,
            },
            {
                "city": "Riyadh",
                "price": 90_000,
                "size": 200,
                "bedrooms": 2,
                "analysis_eligible": True,
            },
            {
                "city": "Riyadh",
                "price": 110_000,
                "size": 250,
                "bedrooms": 3,
                "analysis_eligible": True,
            },
            {
                "city": "Dammam",
                "price": 52_000,
                "size": 180,
                "bedrooms": 4,
                "analysis_eligible": True,
            },
            {
                "city": "Riyadh",
                "price": 100_000,
                "size": 270,
                "bedrooms": 4,
                "analysis_eligible": True,
            },
            {
                "city": "Dammam",
                "price": 40_000,
                "size": 300,
                "bedrooms": 7,
                "analysis_eligible": True,
            },
            {
                "city": "Riyadh",
                "price": 80_000,
                "size": 350,
                "bedrooms": 7,
                "analysis_eligible": True,
            },
        ]
    )

    summary = summarize_listings(frame)

    assert summary["city_counts"][0]["city"] == "Dammam"
    assert summary["city_counts"][1]["city"] == "Riyadh"
    assert summary["chart_titles"]["rent_by_city"] == (
        "Riyadh listings have the highest median asking rent in this sample"
    )
    assert summary["chart_titles"]["rent_vs_size"] == (
        "Larger listings tend to have higher asking rents in this sample"
    )
    assert summary["bedroom_median_rents"][-1]["bedroom_label"] == "7+"
    assert "peaks at 3 bedrooms" in summary["chart_titles"]["rent_by_bedrooms"]
