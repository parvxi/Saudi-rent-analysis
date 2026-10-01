"""Internal command entry point; the Makefile is the supported interface."""

import argparse
import sys

import pandas as pd

from aqar_rent.analysis import AnalysisError, write_analysis_outputs
from aqar_rent.cleaning import CleaningError, clean_listings, write_cleaning_outputs
from aqar_rent.io import DataLoadError, load_listings
from aqar_rent.modeling import ModelError, train_and_evaluate, write_model_outputs
from aqar_rent.paths import get_cleaned_data_path, get_data_path, get_output_dir
from aqar_rent.validation import validate_listings, write_validation_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aqar-rent")
    parser.add_argument(
        "command",
        nargs="?",
        choices=("validate-data", "clean-data", "analyze", "train", "pipeline"),
        help="internal command invoked by Make targets",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command is None:
        return 0
    if args.command == "pipeline":
        try:
            frame = load_listings(get_data_path())
            validation = validate_listings(frame)
            write_validation_report(validation, get_output_dir())
            if not validation["valid"]:
                print("Validation found issues; pipeline stopped.", file=sys.stderr)
                return 1
            cleaned, cleaning_summary = clean_listings(frame)
            write_cleaning_outputs(cleaned, cleaning_summary, get_output_dir())
            analysis_summary = write_analysis_outputs(cleaned, get_output_dir())
            model, metrics = train_and_evaluate(cleaned)
            write_model_outputs(model, metrics, get_output_dir())
        except (
            DataLoadError,
            CleaningError,
            AnalysisError,
            ModelError,
            OSError,
            KeyError,
            ValueError,
        ) as error:
            print(str(error), file=sys.stderr)
            return 1
        print(
            "Pipeline complete: "
            f"{analysis_summary['eligible_listing_count']} eligible listings; "
            f"held-out MAE {metrics['model']['mae_sar']:,.0f} SAR/year."
        )
        return 0

    if args.command == "analyze":
        try:
            cleaned = pd.read_csv(get_cleaned_data_path())
            summary = write_analysis_outputs(cleaned, get_output_dir())
        except (OSError, AnalysisError, KeyError, ValueError) as error:
            print(str(error), file=sys.stderr)
            return 1
        print(
            f"Analysis complete: {summary['eligible_listing_count']} eligible "
            "listings summarized across cities."
        )
        return 0

    if args.command == "train":
        try:
            cleaned = pd.read_csv(get_cleaned_data_path())
            model, metrics = train_and_evaluate(cleaned)
            write_model_outputs(model, metrics, get_output_dir())
        except (OSError, ModelError, KeyError, ValueError) as error:
            print(str(error), file=sys.stderr)
            return 1
        print(
            f"Training complete: held-out MAE "
            f"{metrics['model']['mae_sar']:,.0f} SAR/year across "
            f"{metrics['test_count']} listings."
        )
        return 0

    try:
        frame = load_listings(get_data_path())
    except DataLoadError as error:
        print(str(error), file=sys.stderr)
        return 1

    if args.command == "validate-data":
        report = validate_listings(frame)
        write_validation_report(report, get_output_dir())
        print(
            f"Validation {'passed' if report['valid'] else 'found issues'}: "
            f"{report['source_record_count']} records, "
            f"{report['duplicate_rows']} duplicate retained rows."
        )
        return 0 if report["valid"] else 1

    try:
        cleaned, summary = clean_listings(frame)
    except CleaningError as error:
        print(str(error), file=sys.stderr)
        return 1
    write_cleaning_outputs(cleaned, summary, get_output_dir())
    print(
        f"Cleaning complete: {summary['deduplicated_record_count']} rows, "
        f"{summary['analysis_excluded_count']} excluded from analysis/modeling."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
