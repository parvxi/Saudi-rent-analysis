import pandas as pd
import pytest

from aqar_rent.cleaning import CleaningError, clean_listings
from aqar_rent.schema import RETAINED_COLUMNS


def raw_frame(rows: list[dict[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=RETAINED_COLUMNS, dtype="string")


def valid_values(**updates: str) -> dict[str, str]:
    values = {column: "1" for column in RETAINED_COLUMNS}
    values.update(
        {
            "city": " الرياض ",
            "district": " حي تجريبي ",
            "front": " 3 شوارع ",
            "size": "200",
            "property_age": "5",
            "bedrooms": "3",
            "bathrooms": "2",
            "livingrooms": "1",
            "price": "70000",
        }
    )
    values.update(updates)
    return values


@pytest.mark.unit
def test_cleaning_trims_maps_and_converts_structured_fields() -> None:
    cleaned, summary = clean_listings(raw_frame([valid_values()]))
    row = cleaned.iloc[0]

    assert row["city"] == "Riyadh"
    assert row["city_raw"] == "الرياض"
    assert row["district"] == "حي تجريبي"
    assert row["front"] == "Corner"
    assert row["size"] == 200
    assert row["garage"] == 1
    assert summary["analysis_eligible_count"] == 1


@pytest.mark.unit
def test_cleaning_deduplicates_retained_rows_and_flags_outliers() -> None:
    rows = [
        valid_values(),
        valid_values(),
        valid_values(price="9999"),
        valid_values(price="500001"),
        valid_values(size="49"),
        valid_values(size="2001"),
        valid_values(price="1000", size="1"),
    ]

    cleaned, summary = clean_listings(raw_frame(rows))

    assert len(cleaned) == 6
    assert summary["duplicate_rows_removed"] == 1
    assert summary["price_below_min_count"] == 2
    assert summary["price_above_max_count"] == 1
    assert summary["size_below_min_count"] == 2
    assert summary["size_above_max_count"] == 1
    assert summary["analysis_excluded_count"] == 5
    assert summary["analysis_eligible_count"] == 1
    assert cleaned["analysis_eligible"].sum() == 1


@pytest.mark.parametrize(
    ("updates", "expected_eligible"),
    [
        ({"price": "10000"}, True),
        ({"price": "500000"}, True),
        ({"price": "9999"}, False),
        ({"price": "500001"}, False),
        ({"size": "50"}, True),
        ({"size": "2000"}, True),
        ({"size": "49"}, False),
        ({"size": "2001"}, False),
    ],
)
@pytest.mark.unit
def test_cleaning_keeps_exact_bounds_and_excludes_values_just_outside(
    updates: dict[str, str], expected_eligible: bool
) -> None:
    cleaned, _ = clean_listings(raw_frame([valid_values(**updates)]))

    assert bool(cleaned.iloc[0]["analysis_eligible"]) is expected_eligible


@pytest.mark.unit
def test_cleaning_rejects_invalid_retained_values() -> None:
    invalid = raw_frame([valid_values(size="not-numeric")])

    with pytest.raises(CleaningError, match="Input failed validation"):
        clean_listings(invalid)
