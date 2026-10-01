from pathlib import Path

import pytest

from aqar_rent.paths import (
    DEFAULT_DATA_PATH,
    DEFAULT_OUTPUT_DIR,
    get_cleaned_data_path,
    get_data_path,
    get_output_dir,
)


@pytest.mark.unit
def test_path_defaults_are_project_local() -> None:
    assert (
        DEFAULT_DATA_PATH
        == Path(__file__).resolve().parents[2] / "data" / "SA_Aqar.csv"
    )
    assert DEFAULT_OUTPUT_DIR == Path(__file__).resolve().parents[2] / "artifacts"


@pytest.mark.unit
def test_path_environment_overrides(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    data_path = tmp_path / "fixture.csv"
    output_dir = tmp_path / "output"
    monkeypatch.setenv("AQAR_DATA_PATH", str(data_path))
    monkeypatch.setenv("AQAR_OUTPUT_DIR", str(output_dir))

    assert get_data_path() == data_path
    assert get_output_dir() == output_dir
    assert get_cleaned_data_path() == output_dir / "cleaned" / "listings.csv"
