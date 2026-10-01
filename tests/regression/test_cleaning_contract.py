import pandas as pd
import pytest

from aqar_rent.cleaning import clean_listings
from aqar_rent.schema import RETAINED_COLUMNS


def make_row(**updates: str) -> dict[str, str]:
    values = {column: "1" for column in RETAINED_COLUMNS}
    values.update(
        {
            "city": "الرياض",
            "district": "حي تجريبي",
            "front": "شمال",
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


@pytest.mark.regression
def test_cleaned_column_and_confirmed_exclusion_contract() -> None:
    source = pd.DataFrame(
        [
            make_row(),
            make_row(),
            make_row(price="9999"),
            make_row(price="500001"),
            make_row(size="49"),
            make_row(size="2001"),
            make_row(price="1000", size="1"),
        ],
        columns=RETAINED_COLUMNS,
        dtype="string",
    )

    cleaned, summary = clean_listings(source)

    expected_columns = (
        "city",
        "city_raw",
        *RETAINED_COLUMNS[1:],
        "price_below_min",
        "price_above_max",
        "size_below_min",
        "size_above_max",
        "analysis_eligible",
    )
    assert tuple(cleaned.columns) == expected_columns
    assert "details" not in cleaned.columns
    assert summary == {
        "raw_record_count": 7,
        "duplicate_rows_removed": 1,
        "deduplicated_record_count": 6,
        "price_below_min_count": 2,
        "price_above_max_count": 1,
        "size_below_min_count": 2,
        "size_above_max_count": 1,
        "analysis_excluded_count": 5,
        "analysis_eligible_count": 1,
    }
