import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from aqar_rent.schema import RETAINED_COLUMNS, SOURCE_COLUMNS

ROOT = Path(__file__).resolve().parents[2]


def make_row(details_text: str, price: str) -> list[str]:
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
            "price": price,
        }
    )
    return [values.get(column, details_text) for column in SOURCE_COLUMNS]


@pytest.mark.integration
def test_make_validate_data_uses_fixture_without_mutating_raw_csv(
    tmp_path: Path,
) -> None:
    fixture = tmp_path / "synthetic.csv"
    with fixture.open("w", encoding="utf-8", newline="") as source:
        writer = csv.writer(source)
        writer.writerow(SOURCE_COLUMNS)
        writer.writerow(make_row("synthetic private marker\ncontinued", "70000"))
        writer.writerow(make_row("another marker", "70000"))
    original_bytes = fixture.read_bytes()
    output_dir = tmp_path / "artifacts"
    environment = os.environ.copy()
    environment["AQAR_DATA_PATH"] = str(fixture)
    environment["AQAR_OUTPUT_DIR"] = str(output_dir)

    result = subprocess.run(
        ["make", "validate-data"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert fixture.read_bytes() == original_bytes
    json_report = output_dir / "reports" / "data_validation.json"
    text_report = output_dir / "reports" / "data_validation.txt"
    report = json.loads(json_report.read_text(encoding="utf-8"))
    assert report["source_record_count"] == 2
    assert report["source_column_count"] == 24
    assert report["loaded_column_count"] == 23
    assert report["duplicate_rows"] == 1
    assert "synthetic private marker" not in json_report.read_text(encoding="utf-8")
    assert "synthetic private marker" not in text_report.read_text(encoding="utf-8")


@pytest.mark.integration
def test_package_help_runs_from_installed_environment() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "aqar_rent.cli", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "validate-data" in result.stdout
