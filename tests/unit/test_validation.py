import csv
from pathlib import Path

import pandas as pd
import pytest

from aqar_rent.io import DataLoadError, load_listings
from aqar_rent.schema import RETAINED_COLUMNS, SOURCE_COLUMNS
from aqar_rent.validation import validate_listings, write_validation_report


def write_fixture(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fixture:
        writer = csv.writer(fixture)
        writer.writerow(SOURCE_COLUMNS)
        writer.writerows(rows)


def valid_row(**updates: str) -> list[str]:
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
    return [values.get(column, "private fixture text") for column in SOURCE_COLUMNS]


@pytest.mark.unit
def test_loader_omits_free_text_and_parses_quoted_newlines(tmp_path: Path) -> None:
    source_path = tmp_path / "synthetic.csv"
    row = valid_row()
    row[-1] = "synthetic marker\nsecond line"
    write_fixture(source_path, [row])

    frame = load_listings(source_path)

    assert tuple(frame.columns) == RETAINED_COLUMNS
    assert "details" not in frame.columns
    assert len(frame) == 1


@pytest.mark.unit
def test_loader_rejects_wrong_header_and_record_width(tmp_path: Path) -> None:
    wrong_header_path = tmp_path / "wrong-header.csv"
    wrong_header_path.write_text("wrong,header\n1,2\n", encoding="utf-8")
    with pytest.raises(DataLoadError, match="header"):
        load_listings(wrong_header_path)

    wrong_width_path = tmp_path / "wrong-width.csv"
    with wrong_width_path.open("w", encoding="utf-8", newline="") as source:
        writer = csv.writer(source)
        writer.writerow(SOURCE_COLUMNS)
        writer.writerow(["one", "field"])
    with pytest.raises(DataLoadError, match="record 2"):
        load_listings(wrong_width_path)


@pytest.mark.unit
def test_loader_rejects_empty_csv(tmp_path: Path) -> None:
    source_path = tmp_path / "empty.csv"
    source_path.write_text("", encoding="utf-8")

    with pytest.raises(DataLoadError, match="CSV is empty"):
        load_listings(source_path)


@pytest.mark.unit
def test_loader_reports_missing_input_without_reading_dataset(tmp_path: Path) -> None:
    with pytest.raises(DataLoadError, match="Could not read input CSV"):
        load_listings(tmp_path / "missing.csv")


@pytest.mark.unit
def test_validation_reports_numeric_binary_city_and_duplicate_findings() -> None:
    valid = {column: "1" for column in RETAINED_COLUMNS}
    valid.update(
        {
            "city": " الرياض ",
            "front": "شمال",
            "size": "200",
            "property_age": "5",
            "bedrooms": "3",
            "bathrooms": "2",
            "livingrooms": "1",
            "price": "70000",
        }
    )
    bad = dict(valid, size="not-a-number", garage="3", city="unknown")
    frame = pd.DataFrame([valid, bad, valid], columns=RETAINED_COLUMNS, dtype="string")

    report = validate_listings(frame)

    assert report["valid"] is False
    assert report["source_record_count"] == 3
    assert report["duplicate_rows"] == 1
    assert report["checks"]["numeric_parse_errors"]["size"] == 1
    assert report["checks"]["binary_domain_errors"]["garage"] == 1
    assert report["checks"]["unknown_city_values"] == 1


@pytest.mark.unit
def test_validation_rejects_unknown_front_values() -> None:
    row = {column: "1" for column in RETAINED_COLUMNS}
    row.update({"city": "الرياض", "front": "واجهة مجهولة"})

    report = validate_listings(
        pd.DataFrame([row], columns=RETAINED_COLUMNS, dtype="string")
    )

    assert report["valid"] is False
    assert report["checks"]["unknown_front_values"] == 1
    assert "unknown_front_values: 1" in report["errors"]


@pytest.mark.unit
def test_validation_counts_null_and_non_finite_numeric_values() -> None:
    row = {column: "1" for column in RETAINED_COLUMNS}
    row.update(
        {
            "city": "الرياض",
            "front": "شمال",
            "district": "",
            "size": "inf",
            "property_age": "NaN",
            "bedrooms": "3",
            "bathrooms": "2",
            "livingrooms": "1",
            "price": "70000",
        }
    )

    report = validate_listings(
        pd.DataFrame([row], columns=RETAINED_COLUMNS, dtype="string")
    )

    assert report["checks"]["structured_nulls"]["district"] == 1
    assert report["checks"]["numeric_non_finite"]["size"] == 1
    assert report["checks"]["numeric_parse_errors"]["property_age"] == 1


@pytest.mark.unit
def test_report_writers_do_not_include_fixture_free_text(tmp_path: Path) -> None:
    source_path = tmp_path / "synthetic.csv"
    row = valid_row()
    sentinel = "private-fixture-sentinel"
    row[-1] = sentinel
    write_fixture(source_path, [row])

    frame = load_listings(source_path)
    report = validate_listings(frame)
    write_validation_report(report, tmp_path)
    output = tmp_path / "reports"
    json_report = (output / "data_validation.json").read_text(encoding="utf-8")
    text_report = (output / "data_validation.txt").read_text(encoding="utf-8")
    assert "details" not in frame.columns
    assert sentinel not in json_report
    assert sentinel not in text_report
