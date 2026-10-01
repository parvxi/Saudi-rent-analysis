import re
import sys
import tomllib
from pathlib import Path

import pytest

from aqar_rent.schema import RETAINED_COLUMNS, SOURCE_COLUMNS

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.regression
def test_schema_column_contract() -> None:
    assert len(SOURCE_COLUMNS) == 24
    assert len(RETAINED_COLUMNS) == 23
    assert "details" not in RETAINED_COLUMNS


@pytest.mark.regression
def test_python_and_pytest_configuration_contract() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert sys.version_info[:2] == (3, 12)
    assert project["project"]["requires-python"] == ">=3.12,<3.13"
    markers = project["tool"]["pytest"]["ini_options"]["markers"]
    assert {"unit", "regression", "integration"} <= {
        marker.split(":", maxsplit=1)[0] for marker in markers
    }


@pytest.mark.regression
def test_public_make_targets_and_package_entrypoint() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    targets = set(re.findall(r"^([a-z][a-z-]*):", makefile, re.MULTILINE))
    expected = {
        "install",
        "test",
        "validate-data",
        "clean-data",
        "analyze",
        "train",
        "pipeline",
        "docker-build",
        "docker-run",
        "clean",
    }
    assert expected <= targets
    assert "-m aqar_rent.cli analyze" in makefile
    assert "$(MAKE) validate-data" in makefile


@pytest.mark.regression
def test_docker_configuration_uses_python_312_and_full_pipeline() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    assert "FROM python:3.12-slim" in dockerfile
    assert 'CMD ["python", "-m", "aqar_rent.cli", "pipeline"]' in dockerfile
    assert "COPY data" not in dockerfile
    assert "data/" in dockerignore
    assert "artifacts/" in dockerignore
