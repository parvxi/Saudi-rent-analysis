"""Aggregate retained-column data-quality checks and report writers."""

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from aqar_rent.schema import (
    BINARY_COLUMNS,
    KNOWN_CITIES,
    KNOWN_FRONTS,
    NUMERIC_COLUMNS,
    RETAINED_COLUMNS,
    SOURCE_COLUMNS,
)


def validate_listings(frame: pd.DataFrame) -> dict[str, Any]:
    """Return counts and aggregate errors without exposing cell values."""
    null_counts = {
        column: int((frame[column].isna() | frame[column].eq("")).sum())
        for column in RETAINED_COLUMNS
    }
    parse_errors: dict[str, int] = {}
    non_finite: dict[str, int] = {}
    for column in NUMERIC_COLUMNS:
        values = frame[column]
        numeric = pd.to_numeric(values, errors="coerce")
        parse_errors[column] = int((values.ne("") & numeric.isna()).sum())
        non_finite[column] = sum(
            not math.isfinite(float(value)) for value in numeric.dropna()
        )

    binary_errors = {
        column: int((frame[column].ne("") & ~frame[column].isin({"0", "1"})).sum())
        for column in BINARY_COLUMNS
    }
    city_values = frame["city"].str.strip()
    city_errors = int((city_values.ne("") & ~city_values.isin(KNOWN_CITIES)).sum())
    front_values = frame["front"].str.strip()
    front_errors = int((front_values.ne("") & ~front_values.isin(KNOWN_FRONTS)).sum())
    duplicate_rows = int(frame.duplicated(keep="first").sum())

    checks = {
        "structured_nulls": null_counts,
        "numeric_parse_errors": parse_errors,
        "numeric_non_finite": non_finite,
        "binary_domain_errors": binary_errors,
        "unknown_city_values": city_errors,
        "unknown_front_values": front_errors,
    }
    errors = []
    for check_name, counts in checks.items():
        if isinstance(counts, dict):
            errors.extend(
                f"{check_name}: {column}={count}"
                for column, count in counts.items()
                if count
            )
        elif counts:
            errors.append(f"{check_name}: {counts}")

    return {
        "valid": not errors,
        "source_record_count": len(frame),
        "source_column_count": len(SOURCE_COLUMNS),
        "loaded_column_count": len(RETAINED_COLUMNS),
        "duplicate_rows": duplicate_rows,
        "checks": checks,
        "errors": errors,
    }


def write_validation_report(report: dict[str, Any], output_dir: Path) -> None:
    """Write machine-readable and concise human-readable reports."""
    report_dir = output_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "data_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "Data validation",
        f"Status: {'valid' if report['valid'] else 'invalid'}",
        f"Records: {report['source_record_count']}",
        f"Source columns: {report['source_column_count']}",
        f"Loaded columns: {report['loaded_column_count']}",
        f"Duplicate retained rows: {report['duplicate_rows']}",
        "",
        "Nonzero findings:",
    ]
    findings = report["errors"] or ["None"]
    lines.extend(f"- {finding}" for finding in findings)
    (report_dir / "data_validation.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
