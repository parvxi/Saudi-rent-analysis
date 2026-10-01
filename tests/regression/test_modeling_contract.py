import pandas as pd
import pytest

from aqar_rent.modeling import FEATURE_COLUMNS, train_and_evaluate


@pytest.mark.regression
def test_model_metrics_and_city_reporting_are_stable_for_synthetic_sample() -> None:
    rows = []
    cities = ("Al Khobar", "Dammam", "Jeddah", "Riyadh")
    for city_index, city in enumerate(cities):
        base = 50_000 + city_index * 10_000
        for index in range(8):
            rows.append(
                {
                    "city": city,
                    "front": "North" if index % 2 else "Corner",
                    "size": 100 + index * 15,
                    "bedrooms": 2 + index % 3,
                    "bathrooms": 1 + index % 2,
                    "property_age": index,
                    "garage": index % 2,
                    "furnished": 0,
                    "ac": 1,
                    "pool": 0,
                    "roof": 0,
                    "frontyard": 1,
                    "price": base + index * 2_000 + city_index * 100,
                    "analysis_eligible": True,
                }
            )
    cleaned = pd.DataFrame(rows)

    _, metrics = train_and_evaluate(cleaned)

    assert metrics["train_count"] == 25
    assert metrics["test_count"] == 7
    assert metrics["eligible_city_counts"] == {
        "Al Khobar": 8,
        "Dammam": 8,
        "Jeddah": 8,
        "Riyadh": 8,
    }
    assert len(metrics["per_city"]) == 4
    assert all(row["test_listings"] >= 1 for row in metrics["per_city"])
    assert all("mae_sar" in row["model"] for row in metrics["per_city"])
    assert all(
        "median_absolute_error_sar" in row["model"] for row in metrics["per_city"]
    )
    assert metrics["features"] == list(FEATURE_COLUMNS)
    assert metrics["permutation_importance_method"].startswith("held-out permutation")
    importance = metrics["permutation_importance"]
    assert {row["feature"] for row in importance} == set(FEATURE_COLUMNS)
    assert {row["label"] for row in importance} >= {
        "Size (m²)",
        "Air conditioning",
        "Property age",
    }
    assert [row["mean_mae_increase_sar"] for row in importance] == sorted(
        (row["mean_mae_increase_sar"] for row in importance), reverse=True
    )
    assert 0 <= metrics["model"]["mae_sar"] <= 45_000
    assert 0 <= metrics["city_median_baseline"]["mae_sar"] <= 45_000
    assert 0 < metrics["reference_estimate"]["estimated_yearly_rent_sar"] < 200_000
