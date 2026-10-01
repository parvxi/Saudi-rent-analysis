import pandas as pd
import pytest

from aqar_rent.modeling import (
    FEATURE_COLUMNS,
    city_median_predictions,
    error_metrics,
    permutation_importance_claim,
    select_features,
    split_holdout,
)


def model_rows(count_per_city: int = 5) -> pd.DataFrame:
    rows = []
    for city, base in (("Riyadh", 90_000), ("Jeddah", 70_000)):
        for index in range(count_per_city):
            rows.append(
                {
                    "city": city,
                    "front": "North",
                    "size": 100 + index * 10,
                    "bedrooms": 2 + index % 2,
                    "bathrooms": 2,
                    "property_age": index,
                    "garage": 1,
                    "furnished": 0,
                    "ac": 1,
                    "pool": 0,
                    "roof": 0,
                    "frontyard": 1,
                    "district": "not a model feature",
                    "price": base + index * 1_000,
                    "analysis_eligible": True,
                }
            )
    return pd.DataFrame(rows)


@pytest.mark.unit
def test_feature_selection_excludes_district_and_text() -> None:
    features, target = select_features(model_rows())

    assert tuple(features.columns) == FEATURE_COLUMNS
    assert "district" not in features.columns
    assert "details" not in features.columns
    assert target.name == "price"


@pytest.mark.unit
def test_holdout_split_is_fixed_seed_and_city_stratified() -> None:
    frame = model_rows()
    train_a, test_a = split_holdout(frame)
    train_b, test_b = split_holdout(frame)

    assert train_a.index.tolist() == train_b.index.tolist()
    assert test_a.index.tolist() == test_b.index.tolist()
    assert test_a["city"].value_counts().to_dict() == {"Riyadh": 1, "Jeddah": 1}


@pytest.mark.unit
def test_city_median_baseline_and_error_metrics() -> None:
    training = model_rows()
    evaluation = pd.DataFrame(
        {"city": ["Riyadh", "Unknown"], "price": [95_000, 30_000]}
    )

    predictions = city_median_predictions(training, evaluation)
    errors = error_metrics(pd.Series([90_000, 30_000]), predictions)

    assert predictions.tolist() == [92_000.0, 82_000.0]
    assert errors["mae_sar"] == 27_000.0
    assert errors["median_absolute_error_sar"] == 27_000.0


@pytest.mark.unit
def test_permutation_claim_uses_human_labels_and_english_wording() -> None:
    ranking = [
        {"label": "Size (m²)", "mean_mae_increase_sar": 20.0},
        {"label": "Air conditioning", "mean_mae_increase_sar": 10.0},
        {"label": "Property age", "mean_mae_increase_sar": 5.0},
    ]

    assert permutation_importance_claim(ranking) == (
        "Size (m²) and Air conditioning matter most for asking rent in this sample"
    )
