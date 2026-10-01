"""Reference rent model with fixed holdout and city-level error reporting."""

import json
from pathlib import Path
from textwrap import fill
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, median_absolute_error
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from aqar_rent.analysis import eligible_listings

CATEGORICAL_FEATURES = ("city", "front")
NUMERIC_FEATURES = (
    "size",
    "bedrooms",
    "bathrooms",
    "property_age",
    "garage",
    "furnished",
    "ac",
    "pool",
    "roof",
    "frontyard",
)
FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES
TARGET_COLUMN = "price"
RANDOM_SEED = 42
TEST_FRACTION = 0.2
FEATURE_LABELS = {
    "city": "City",
    "front": "Street orientation",
    "size": "Size (m²)",
    "bedrooms": "Bedrooms",
    "bathrooms": "Bathrooms",
    "property_age": "Property age",
    "garage": "Garage",
    "furnished": "Furnished",
    "ac": "Air conditioning",
    "pool": "Pool",
    "roof": "Roof",
    "frontyard": "Front yard",
}


class ModelError(ValueError):
    """Raised when there is insufficient data for a stratified holdout."""


def select_features(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Select only approved structured model inputs and yearly rent target."""
    missing = set(FEATURE_COLUMNS + (TARGET_COLUMN,)) - set(frame.columns)
    if missing:
        raise ModelError("Cleaned table is missing required model columns")
    return frame.loc[:, FEATURE_COLUMNS].copy(), frame[TARGET_COLUMN].copy()


def split_holdout(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Create a reproducible 80/20 holdout stratified by city."""
    city_counts = frame["city"].value_counts()
    if city_counts.empty or city_counts.min() < 2:
        raise ModelError("At least two eligible listings per city are required")
    test_count = int(np.ceil(len(frame) * TEST_FRACTION))
    if test_count < city_counts.size:
        raise ModelError("Holdout must contain at least one listing per city")
    training, testing = train_test_split(
        frame,
        test_size=TEST_FRACTION,
        random_state=RANDOM_SEED,
        stratify=frame["city"],
    )
    return training.copy(), testing.copy()


def build_model_pipeline() -> Pipeline:
    """Build the modest structured-feature rent estimator."""
    preprocessing = ColumnTransformer(
        transformers=[
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore"),
                list(CATEGORICAL_FEATURES),
            ),
            ("numeric", "passthrough", list(NUMERIC_FEATURES)),
        ]
    )
    estimator = RandomForestRegressor(
        n_estimators=120,
        min_samples_leaf=3,
        random_state=RANDOM_SEED,
        n_jobs=1,
    )
    return Pipeline([("preprocessing", preprocessing), ("estimator", estimator)])


def city_median_predictions(
    training: pd.DataFrame, evaluation: pd.DataFrame
) -> np.ndarray:
    """Predict from training-city medians, with a global fallback."""
    city_medians = training.groupby("city")[TARGET_COLUMN].median()
    global_median = float(training[TARGET_COLUMN].median())
    return evaluation["city"].map(city_medians).fillna(global_median).to_numpy()


def error_metrics(actual: pd.Series, predicted: np.ndarray) -> dict[str, float]:
    """Return absolute-error measures in yearly SAR."""
    return {
        "mae_sar": float(mean_absolute_error(actual, predicted)),
        "median_absolute_error_sar": float(median_absolute_error(actual, predicted)),
    }


def held_out_permutation_importance(
    model: Pipeline, features: pd.DataFrame, target: pd.Series
) -> list[dict[str, float | str]]:
    """Measure held-out MAE increase after permuting each raw input column."""
    result = permutation_importance(
        model,
        features,
        target,
        scoring="neg_mean_absolute_error",
        n_repeats=10,
        random_state=RANDOM_SEED,
        n_jobs=1,
    )
    ranked = [
        {
            "feature": feature,
            "label": FEATURE_LABELS[feature],
            "mean_mae_increase_sar": float(mean),
            "std_mae_increase_sar": float(deviation),
        }
        for feature, mean, deviation in zip(
            FEATURE_COLUMNS, result.importances_mean, result.importances_std
        )
    ]
    return sorted(ranked, key=lambda row: row["mean_mae_increase_sar"], reverse=True)


def permutation_importance_claim(ranking: list[dict[str, Any]]) -> str:
    """Describe the highest positive permutation importance in plain English."""
    relevant = [row for row in ranking if row["mean_mae_increase_sar"] > 0][:2]
    if not relevant:
        return "No single feature improves held-out rent predictions in this sample"
    if len(relevant) == 1:
        return f"{relevant[0]['label']} matters most for asking rent in this sample"
    return (
        f"{relevant[0]['label']} and {relevant[1]['label']} matter most for "
        "asking rent in this sample"
    )


def train_and_evaluate(cleaned: pd.DataFrame) -> tuple[Pipeline, dict[str, Any]]:
    """Fit the model, compare against the baseline, and report city coverage."""
    try:
        eligible = eligible_listings(cleaned)
    except (KeyError, ValueError) as error:
        raise ModelError(str(error)) from error
    training, testing = split_holdout(eligible)
    train_features, train_target = select_features(training)
    test_features, test_target = select_features(testing)

    model = build_model_pipeline()
    model.fit(train_features, train_target)
    model_predictions = model.predict(test_features)
    baseline_predictions = city_median_predictions(training, testing)
    permutation_ranking = held_out_permutation_importance(
        model, test_features, test_target
    )

    per_city = []
    for city, city_test in testing.groupby("city", sort=True):
        mask = testing["city"].eq(city).to_numpy()
        city_actual = test_target.loc[city_test.index]
        per_city.append(
            {
                "city": str(city),
                "deduplicated_listings": int(cleaned["city"].eq(city).sum()),
                "eligible_listings": int(eligible["city"].eq(city).sum()),
                "test_listings": int(len(city_test)),
                "model": error_metrics(city_actual, model_predictions[mask]),
                "city_median_baseline": error_metrics(
                    city_actual, baseline_predictions[mask]
                ),
            }
        )

    example = {
        "city": "Riyadh",
        "front": "North",
        "size": 300,
        "bedrooms": 3,
        "bathrooms": 2,
        "property_age": 5,
        "garage": 1,
        "furnished": 0,
        "ac": 1,
        "pool": 0,
        "roof": 0,
        "frontyard": 1,
    }
    estimate = float(model.predict(pd.DataFrame([example], columns=FEATURE_COLUMNS))[0])
    metrics = {
        "target": "yearly asking rent (SAR)",
        "random_seed": RANDOM_SEED,
        "test_fraction": TEST_FRACTION,
        "train_count": int(len(training)),
        "test_count": int(len(testing)),
        "deduplicated_city_counts": {
            str(city): int(count)
            for city, count in cleaned["city"].value_counts().sort_index().items()
        },
        "eligible_city_counts": {
            str(city): int(count)
            for city, count in eligible["city"].value_counts().sort_index().items()
        },
        "features": list(FEATURE_COLUMNS),
        "permutation_importance_method": (
            "held-out permutation; negative mean absolute error scoring"
        ),
        "permutation_importance": permutation_ranking,
        "model": error_metrics(test_target, model_predictions),
        "city_median_baseline": error_metrics(test_target, baseline_predictions),
        "per_city": per_city,
        "reference_estimate": {
            "profile": example,
            "estimated_yearly_rent_sar": estimate,
        },
        "limitations": [
            "Scraped asking listings are not completed lease prices.",
            "A random holdout does not establish accuracy for future listings or "
            "unseen neighborhoods.",
            "No listing ID is available for robust listing-level grouping.",
        ],
    }
    return model, metrics


def write_model_outputs(
    model: Pipeline, metrics: dict[str, Any], output_dir: Path
) -> None:
    """Write the trained reference model, metrics, and readable report."""
    model_dir = output_dir / "model"
    report_dir = output_dir / "reports"
    figure_dir = output_dir / "figures"
    model_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_dir / "reference_model.joblib")
    (model_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2) + "\n", encoding="utf-8"
    )

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import StrMethodFormatter

    ranking = metrics["permutation_importance"]
    figure, axis = plt.subplots(figsize=(9, 6))
    axis.barh(
        [row["label"] for row in reversed(ranking)],
        [row["mean_mae_increase_sar"] for row in reversed(ranking)],
        xerr=[row["std_mae_increase_sar"] for row in reversed(ranking)],
        color="#c56b3f",
        capsize=2,
    )
    axis.set_title(fill(permutation_importance_claim(ranking), width=48), fontsize=11)
    axis.set_xlabel("Increase in mean absolute error (SAR/year)")
    axis.xaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    figure.tight_layout()
    figure.savefig(figure_dir / "permutation_importance.png", dpi=150)
    plt.close(figure)

    lines = [
        "# Reference rent model",
        "",
        "Estimate target: yearly asking rent (SAR).",
        "",
        f"The fixed-seed holdout contains {metrics['test_count']} of "
        f"{metrics['train_count'] + metrics['test_count']} eligible listings "
        f"(seed {metrics['random_seed']}, test fraction "
        f"{metrics['test_fraction']:.0%}).",
        "",
        "## Listings and held-out errors by city",
        "",
        (
            "| City | Deduplicated | Eligible | Held out | Model MAE (SAR) | "
            "Model median AE (SAR) | Baseline MAE (SAR) | Baseline median AE (SAR) |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lines.extend(
        f"| {row['city']} | {row['deduplicated_listings']} | "
        f"{row['eligible_listings']} | {row['test_listings']} | "
        f"{row['model']['mae_sar']:,.0f} | "
        f"{row['model']['median_absolute_error_sar']:,.0f} | "
        f"{row['city_median_baseline']['mae_sar']:,.0f} | "
        f"{row['city_median_baseline']['median_absolute_error_sar']:,.0f} |"
        for row in metrics["per_city"]
    )
    lines.extend(
        [
            "",
            "## Overall held-out performance",
            "",
            f"- Model MAE: {metrics['model']['mae_sar']:,.0f} SAR/year.",
            "- Model median absolute error: "
            f"{metrics['model']['median_absolute_error_sar']:,.0f} SAR/year.",
            "- City-median baseline MAE: "
            f"{metrics['city_median_baseline']['mae_sar']:,.0f} SAR/year.",
            "- City-median baseline median absolute error: "
            f"{metrics['city_median_baseline']['median_absolute_error_sar']:,.0f} "
            "SAR/year.",
            "",
            "## Held-out permutation importance",
            "",
            "Features are ranked by the mean increase in held-out MAE (SAR/year) "
            "after permuting one input column "
            "at a time; larger values indicate "
            "greater model reliance in this holdout.",
            "",
            "| Feature | Mean MAE increase (SAR/year) | Standard deviation |",
            "|---|---:|---:|",
            *[
                f"| {row['label']} | {row['mean_mae_increase_sar']:,.0f} | "
                f"{row['std_mae_increase_sar']:,.0f} |"
                for row in ranking
            ],
            "",
            "Permutation importance is descriptive, not causal. Correlated "
            "features can share or obscure importance when one column is shuffled.",
            "",
            "## Example reference estimate",
            "",
            "Profile: Riyadh, North-facing, 300 m², 3 bedrooms, 2 bathrooms, "
            "5 years old; garage and AC present, furnished/pool/roof absent, "
            "frontyard present.",
            "",
            f"Estimated yearly asking rent: "
            f"{metrics['reference_estimate']['estimated_yearly_rent_sar']:,.0f} SAR.",
            "",
            "This is a reference estimate from scraped asking listings, not a "
            "certified or fair-market valuation."
            " A random holdout does not "
            "establish performance on future listings or unseen neighborhoods.",
        ]
    )
    (report_dir / "model_summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
