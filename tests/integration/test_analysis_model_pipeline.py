import csv
import json
import os
import subprocess
from pathlib import Path

import pytest

from aqar_rent.schema import RETAINED_COLUMNS, SOURCE_COLUMNS

ROOT = Path(__file__).resolve().parents[2]
CITIES = (
    ("الخبر", 50_000),
    ("الدمام", 60_000),
    ("جدة", 70_000),
    ("الرياض", 90_000),
)
FRONTS = ("شمال", "شرق", "3 شوارع", "غرب")


def synthetic_row(city: str, base_price: int, index: int) -> list[str]:
    values = {column: "1" for column in RETAINED_COLUMNS}
    values.update(
        {
            "city": city,
            "district": "منطقة اختبار",
            "front": FRONTS[index % len(FRONTS)],
            "size": str(100 + (index % 10) * 20),
            "property_age": str(index % 15),
            "bedrooms": str(2 + index % 3),
            "bathrooms": str(1 + index % 2),
            "livingrooms": "1",
            "garage": str(index % 2),
            "furnished": str((index // 2) % 2),
            "price": str(base_price + index * 1_500 + (index % 10) * 2_000),
        }
    )
    return [
        values.get(column, "integration-only details marker")
        for column in SOURCE_COLUMNS
    ]


@pytest.mark.integration
def test_make_pipeline_writes_city_analysis_and_model_reports(tmp_path: Path) -> None:
    fixture = tmp_path / "synthetic.csv"
    with fixture.open("w", encoding="utf-8", newline="") as source:
        writer = csv.writer(source)
        writer.writerow(SOURCE_COLUMNS)
        for city, base_price in CITIES:
            for index in range(20):
                writer.writerow(synthetic_row(city, base_price, index))
    original_bytes = fixture.read_bytes()
    output_dir = tmp_path / "artifacts"
    environment = os.environ.copy()
    environment["AQAR_DATA_PATH"] = str(fixture)
    environment["AQAR_OUTPUT_DIR"] = str(output_dir)

    result = subprocess.run(
        ["make", "pipeline"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert fixture.read_bytes() == original_bytes

    analysis_path = output_dir / "reports" / "analysis_summary.md"
    model_path = output_dir / "reports" / "model_summary.md"
    metrics_path = output_dir / "model" / "metrics.json"
    analysis = analysis_path.read_text(encoding="utf-8")
    model_summary = model_path.read_text(encoding="utf-8")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    figure_paths = sorted((output_dir / "figures").glob("*.png"))

    assert all(path.stat().st_size > 0 for path in figure_paths)
    assert len(figure_paths) == 5
    assert "Deduplicated listings" in analysis
    assert "Eligible listings" in analysis
    assert "Riyadh" in analysis and "Jeddah" in analysis
    assert "Deduplicated" in model_summary and "Held out" in model_summary
    assert "Model MAE" in model_summary and "Baseline MAE" in model_summary
    assert "Baseline median AE (SAR)" in model_summary
    assert "City-median baseline median absolute error:" in model_summary
    assert "after permuting one input column at a time" in model_summary
    assert "valuation. A random holdout" in model_summary
    assert "columnat" not in model_summary
    assert "valuation.A random" not in model_summary
    assert "Held-out permutation importance" in model_summary
    assert "Correlated features" in model_summary
    assert "Size (m²)" in model_summary
    assert "Air conditioning" in model_summary
    assert "Property age" in model_summary
    assert len(metrics["per_city"]) == 4
    assert set(metrics["deduplicated_city_counts"].values()) == {20}
    assert set(metrics["eligible_city_counts"].values()) == {20}
    assert all(row["test_listings"] > 0 for row in metrics["per_city"])
    assert len(metrics["permutation_importance"]) == 12
    assert "permutation_importance.png" in {path.name for path in figure_paths}
    assert "integration-only details marker" not in analysis
    assert "integration-only details marker" not in model_summary
    assert (output_dir / "model" / "reference_model.joblib").is_file()
