import csv
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from aqar_rent.schema import RETAINED_COLUMNS, SOURCE_COLUMNS

ROOT = Path(__file__).resolve().parents[2]
IMAGE = "aqar-rent:round4-test"
SYNTHETIC_CITIES = (
    ("الخبر", 50_000),
    ("الدمام", 60_000),
    ("جدة", 70_000),
    ("الرياض", 90_000),
)
SYNTHETIC_FRONTS = ("شمال", "شرق", "3 شوارع", "غرب")


def make_csv_row(city: str, base_price: int, index: int) -> list[str]:
    values = {column: "1" for column in RETAINED_COLUMNS}
    values.update(
        {
            "city": city,
            "district": "منطقة اختبار",
            "front": SYNTHETIC_FRONTS[index % len(SYNTHETIC_FRONTS)],
            "size": str(100 + index * 5),
            "property_age": str(index % 12),
            "bedrooms": str(2 + index % 3),
            "bathrooms": str(1 + index % 2),
            "livingrooms": "1",
            "garage": str(index % 2),
            "furnished": str((index // 2) % 2),
            "price": str(base_price + index * 1_000),
        }
    )
    return [
        values.get(column, "docker-only synthetic details") for column in SOURCE_COLUMNS
    ]


def docker_is_available() -> bool:
    if shutil.which("docker") is None:
        return False
    result = subprocess.run(
        ["docker", "info", "--format", "{{.ServerVersion}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


@pytest.mark.integration
def test_docker_image_runs_pipeline_with_read_only_synthetic_input(
    tmp_path: Path,
) -> None:
    if not docker_is_available():
        pytest.skip("Docker daemon is unavailable")

    fixture_dir = tmp_path / "data"
    fixture_dir.mkdir()
    fixture = fixture_dir / "synthetic.csv"
    with fixture.open("w", encoding="utf-8", newline="") as source:
        writer = csv.writer(source)
        writer.writerow(SOURCE_COLUMNS)
        for city, base_price in SYNTHETIC_CITIES:
            for index in range(12):
                writer.writerow(make_csv_row(city, base_price, index))
    original_bytes = fixture.read_bytes()
    output_dir = tmp_path / "artifacts"
    output_dir.mkdir()

    build = subprocess.run(
        ["docker", "build", "--tag", IMAGE, str(ROOT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert build.returncode == 0, build.stdout + build.stderr

    image_check = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "python",
            IMAGE,
            "-c",
            "from pathlib import Path; "
            "assert not Path('/app/data/SA_Aqar.csv').exists()",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert image_check.returncode == 0, image_check.stderr

    run = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-e",
            "AQAR_DATA_PATH=/app/data/synthetic.csv",
            "-e",
            "AQAR_OUTPUT_DIR=/app/artifacts",
            "-v",
            f"{fixture_dir}:/app/data:ro",
            "-v",
            f"{output_dir}:/app/artifacts:rw",
            IMAGE,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert run.returncode == 0, run.stdout + run.stderr
    assert fixture.read_bytes() == original_bytes
    assert (output_dir / "reports" / "data_validation.json").is_file()
    assert (output_dir / "cleaned" / "listings.csv").is_file()
    assert (output_dir / "reports" / "analysis_summary.md").is_file()
    assert (output_dir / "reports" / "model_summary.md").is_file()
    assert (output_dir / "model" / "reference_model.joblib").is_file()
    metrics = json.loads(
        (output_dir / "model" / "metrics.json").read_text(encoding="utf-8")
    )
    assert len(metrics["per_city"]) == 4
    assert not list(output_dir.rglob("*details*"))
