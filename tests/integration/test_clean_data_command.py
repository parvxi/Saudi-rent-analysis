import csv
import json
import os
import subprocess
from pathlib import Path

import pytest

from aqar_rent.schema import RETAINED_COLUMNS, SOURCE_COLUMNS

ROOT = Path(__file__).resolve().parents[2]


def fixture_row(city: str, front: str, price: str, size: str) -> list[str]:
    values = {column: "1" for column in RETAINED_COLUMNS}
    values.update(
        {
            "city": city,
            "district": " حي تجريبي ",
            "front": front,
            "size": size,
            "property_age": "5",
            "bedrooms": "3",
            "bathrooms": "2",
            "livingrooms": "1",
            "price": price,
        }
    )
    return [values.get(column, "synthetic details marker") for column in SOURCE_COLUMNS]


@pytest.mark.integration
def test_make_clean_data_is_repeatable_and_preserves_raw_input(tmp_path: Path) -> None:
    fixture = tmp_path / "synthetic.csv"
    with fixture.open("w", encoding="utf-8", newline="") as source:
        writer = csv.writer(source)
        writer.writerow(SOURCE_COLUMNS)
        writer.writerow(fixture_row("الرياض", "3 شوارع", "70000", "200"))
        writer.writerow(fixture_row("الرياض", "3 شوارع", "70000", "200"))
        writer.writerow(fixture_row("جدة", "شرق", "600000", "300"))
    original_bytes = fixture.read_bytes()
    output_dir = tmp_path / "artifacts"
    environment = os.environ.copy()
    environment["AQAR_DATA_PATH"] = str(fixture)
    environment["AQAR_OUTPUT_DIR"] = str(output_dir)

    outputs = []
    for _ in range(2):
        result = subprocess.run(
            ["make", "clean-data"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        outputs.append(
            (
                (output_dir / "cleaned" / "listings.csv").read_bytes(),
                (output_dir / "reports" / "cleaning_summary.txt").read_bytes(),
            )
        )

    cleaned_text = outputs[0][0].decode("utf-8")
    summary_json = json.loads(
        (output_dir / "reports" / "cleaning_summary.json").read_text(encoding="utf-8")
    )
    assert fixture.read_bytes() == original_bytes
    assert outputs[0] == outputs[1]
    assert "details" not in cleaned_text
    assert "synthetic details marker" not in cleaned_text
    assert "Riyadh" in cleaned_text
    assert "Corner" in cleaned_text
    assert summary_json["duplicate_rows_removed"] == 1
    assert summary_json["price_above_max_count"] == 1
    assert summary_json["analysis_excluded_count"] == 1
