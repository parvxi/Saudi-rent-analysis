"""Centralized input and generated-output paths."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "SA_Aqar.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "artifacts"


def get_data_path() -> Path:
    """Return the raw CSV path, honoring the test/runtime override."""
    return Path(os.environ.get("AQAR_DATA_PATH", DEFAULT_DATA_PATH)).expanduser()


def get_output_dir() -> Path:
    """Return the generated-artifact directory, honoring the override."""
    return Path(os.environ.get("AQAR_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)).expanduser()


def get_cleaned_data_path() -> Path:
    """Return the cleaned listings path under the configured output directory."""
    return get_output_dir() / "cleaned" / "listings.csv"
