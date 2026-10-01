"""CSV loading that validates record shape and excludes free-text details."""

import csv
from pathlib import Path
from typing import TextIO

import pandas as pd

from aqar_rent.schema import DETAILS_COLUMN, RETAINED_COLUMNS, SOURCE_COLUMNS


class DataLoadError(ValueError):
    """Raised when the input file does not match the expected CSV schema."""


def _load_records(source: TextIO) -> list[dict[str, str]]:
    reader = csv.reader(source, strict=True)
    try:
        header = next(reader)
    except StopIteration as error:
        raise DataLoadError("CSV is empty; expected a header row") from error
    except csv.Error as error:
        raise DataLoadError("CSV header could not be parsed") from error

    if tuple(header) != SOURCE_COLUMNS:
        raise DataLoadError("CSV header does not match the expected source schema")

    retained_indexes = {
        column: index for index, column in enumerate(header) if column != DETAILS_COLUMN
    }
    records = []
    try:
        for record_number, row in enumerate(reader, start=2):
            if len(row) != len(SOURCE_COLUMNS):
                raise DataLoadError(
                    f"CSV record {record_number} has {len(row)} fields; "
                    f"expected {len(SOURCE_COLUMNS)}"
                )
            records.append(
                {column: row[index] for column, index in retained_indexes.items()}
            )
    except csv.Error as error:
        raise DataLoadError("CSV record could not be parsed") from error
    return records


def load_listings(path: str | Path) -> pd.DataFrame:
    """Load retained raw values; free-text values are not kept in memory."""
    try:
        with Path(path).open(encoding="utf-8", newline="") as source:
            records = _load_records(source)
    except UnicodeDecodeError as error:
        raise DataLoadError("CSV must use UTF-8 encoding") from error
    except OSError as error:
        raise DataLoadError(f"Could not read input CSV: {error}") from error

    return pd.DataFrame(records, columns=RETAINED_COLUMNS, dtype="string")
