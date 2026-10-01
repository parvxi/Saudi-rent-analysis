"""Deterministic cleaning and audit outputs for retained listing fields."""

import json
from pathlib import Path
from typing import Any

import pandas as pd

from aqar_rent.schema import BINARY_COLUMNS, NUMERIC_COLUMNS
from aqar_rent.validation import validate_listings

CITY_LABELS = {
    "الخبر": "Al Khobar",
    "الدمام": "Dammam",
    "الرياض": "Riyadh",
    "جدة": "Jeddah",
}
FRONT_LABELS = {
    "جنوب": "South",
    "جنوب شرقي": "Southeast",
    "جنوب غربي": "Southwest",
    "شرق": "East",
    "شمال": "North",
    "شمال شرقي": "Northeast",
    "شمال غربي": "Northwest",
    "غرب": "West",
    "3 شوارع": "Corner",
    "4 شوارع": "Corner",
}
PRICE_MIN = 10_000
PRICE_MAX = 500_000
SIZE_MIN = 50
SIZE_MAX = 2_000


class CleaningError(ValueError):
    """Raised when input fails the established retained-column validation."""


def clean_listings(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Clean validated data and return audit flags and aggregate counts."""
    validation = validate_listings(frame)
    if not validation["valid"]:
        raise CleaningError(
            "Input failed validation: " + "; ".join(validation["errors"])
        )

    duplicate_rows_removed = int(frame.duplicated(keep="first").sum())
    cleaned = frame.drop_duplicates(keep="first").copy()
    cleaned.insert(1, "city_raw", cleaned["city"])

    for column in cleaned.columns:
        cleaned[column] = cleaned[column].str.strip()
    cleaned["city"] = cleaned["city"].map(CITY_LABELS)
    cleaned["front"] = cleaned["front"].map(
        lambda value: FRONT_LABELS.get(value, value)
    )

    for column in NUMERIC_COLUMNS:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="raise")
    for column in BINARY_COLUMNS:
        cleaned[column] = cleaned[column].astype("int64")

    cleaned["price_below_min"] = cleaned["price"] < PRICE_MIN
    cleaned["price_above_max"] = cleaned["price"] > PRICE_MAX
    cleaned["size_below_min"] = cleaned["size"] < SIZE_MIN
    cleaned["size_above_max"] = cleaned["size"] > SIZE_MAX
    excluded = (
        cleaned["price_below_min"]
        | cleaned["price_above_max"]
        | cleaned["size_below_min"]
        | cleaned["size_above_max"]
    )
    cleaned["analysis_eligible"] = ~excluded

    summary = {
        "raw_record_count": len(frame),
        "duplicate_rows_removed": duplicate_rows_removed,
        "deduplicated_record_count": len(cleaned),
        "price_below_min_count": int(cleaned["price_below_min"].sum()),
        "price_above_max_count": int(cleaned["price_above_max"].sum()),
        "size_below_min_count": int(cleaned["size_below_min"].sum()),
        "size_above_max_count": int(cleaned["size_above_max"].sum()),
        "analysis_excluded_count": int(excluded.sum()),
        "analysis_eligible_count": int((~excluded).sum()),
    }
    return cleaned, summary


def write_cleaning_outputs(
    cleaned: pd.DataFrame, summary: dict[str, Any], output_dir: Path
) -> None:
    """Write the cleaned table and a concise, value-free audit summary."""
    cleaned_dir = output_dir / "cleaned"
    reports_dir = output_dir / "reports"
    cleaned_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    cleaned.to_csv(cleaned_dir / "listings.csv", index=False, encoding="utf-8")

    lines = [
        "Cleaning summary",
        f"Raw records: {summary['raw_record_count']}",
        f"Exact duplicate retained rows removed: {summary['duplicate_rows_removed']}",
        f"Rows after deduplication: {summary['deduplicated_record_count']}",
        f"Price below 10,000 SAR: {summary['price_below_min_count']}",
        f"Price above 500,000 SAR: {summary['price_above_max_count']}",
        f"Size below 50 m2: {summary['size_below_min_count']}",
        f"Size above 2,000 m2: {summary['size_above_max_count']}",
        "Excluded from analysis/modeling (any bound): "
        f"{summary['analysis_excluded_count']}",
        f"Eligible records: {summary['analysis_eligible_count']}",
    ]
    (reports_dir / "cleaning_summary.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    (reports_dir / "cleaning_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
