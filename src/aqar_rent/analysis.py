"""Aggregate eligible listings into concise, auditable findings."""

from pathlib import Path
from textwrap import fill
from typing import Any

import pandas as pd


class AnalysisError(ValueError):
    """Raised when the cleaned table has no usable analysis rows."""


def eligible_listings(cleaned: pd.DataFrame) -> pd.DataFrame:
    """Return rows within the confirmed price and size bounds."""
    eligibility = cleaned["analysis_eligible"]
    if not pd.api.types.is_bool_dtype(eligibility):
        normalized = eligibility.astype("string").str.lower()
        if not normalized.isin({"true", "false"}).all():
            raise AnalysisError("Cleaned data has invalid analysis eligibility flags")
        eligibility = normalized.eq("true")
    eligible = cleaned.loc[eligibility].copy()
    if eligible.empty:
        raise AnalysisError("No analysis-eligible listings are available")
    return eligible


def summarize_listings(cleaned: pd.DataFrame) -> dict[str, Any]:
    """Calculate city counts, rent summaries, and supported chart claims."""
    eligible = eligible_listings(cleaned)
    city_rows = []
    for city, city_eligible in eligible.groupby("city", sort=True):
        city_rows.append(
            {
                "city": str(city),
                "deduplicated_listings": int(cleaned["city"].eq(city).sum()),
                "eligible_listings": int(len(city_eligible)),
                "median_asking_rent_sar": float(city_eligible["price"].median()),
            }
        )

    highest_median = max(row["median_asking_rent_sar"] for row in city_rows)
    median_leaders = [
        row["city"]
        for row in city_rows
        if row["median_asking_rent_sar"] == highest_median
    ]
    if len(median_leaders) == 1:
        city_rent_title = (
            f"{median_leaders[0]} listings have the highest median asking rent "
            "in this sample"
        )
    else:
        city_rent_title = (
            f"{', '.join(median_leaders)} share the highest median asking rent "
            "in this sample"
        )

    count_leaders = [
        row["city"]
        for row in city_rows
        if row["deduplicated_listings"]
        == max(item["deduplicated_listings"] for item in city_rows)
    ]
    if len(count_leaders) == 1:
        count_title = (
            f"{count_leaders[0]} contributes the most listings after deduplication"
        )
    else:
        count_title = (
            f"{', '.join(count_leaders)} share the most listings after deduplication"
        )
    count_title += " in this sample"

    bedroom_groups = pd.to_numeric(eligible["bedrooms"], errors="raise").clip(upper=7)
    bedroom_summary = (
        eligible.assign(_bedroom_group=bedroom_groups)
        .groupby("_bedroom_group", sort=True)
        .agg(
            median_asking_rent_sar=("price", "median"), listing_count=("price", "size")
        )
    )
    bedroom_rows = [
        {
            "bedrooms": int(bedrooms),
            "bedroom_label": "7+" if bedrooms == 7 else str(int(bedrooms)),
            "listing_count": int(row["listing_count"]),
            "median_asking_rent_sar": float(row["median_asking_rent_sar"]),
        }
        for bedrooms, row in bedroom_summary.iterrows()
    ]
    peak_rent = max(row["median_asking_rent_sar"] for row in bedroom_rows)
    peak_bedroom = next(
        row for row in bedroom_rows if row["median_asking_rent_sar"] == peak_rent
    )
    if any(row["bedrooms"] > peak_bedroom["bedrooms"] for row in bedroom_rows):
        bedroom_title = (
            "Median asking rent peaks at "
            f"{peak_bedroom['bedroom_label']} bedrooms and does not keep rising "
            "with more bedrooms in this sample"
        )
    else:
        bedroom_title = (
            "Median asking rent peaks at "
            f"{peak_bedroom['bedroom_label']} bedrooms in this sample"
        )

    if eligible["size"].nunique() < 2 or eligible["price"].nunique() < 2:
        size_title = "Size and asking rent cannot be compared in this sample"
        correlation_value = None
    else:
        correlation = eligible["size"].corr(eligible["price"], method="spearman")
        if pd.isna(correlation):
            size_title = "Size and asking rent cannot be compared in this sample"
            correlation_value = None
        elif correlation > 0:
            size_title = (
                "Larger listings tend to have higher asking rents in this sample"
            )
            correlation_value = float(correlation)
        else:
            size_title = "Asking rent does not rise with listing size in this sample"
            correlation_value = float(correlation)

    return {
        "deduplicated_listing_count": int(len(cleaned)),
        "eligible_listing_count": int(len(eligible)),
        "city_counts": city_rows,
        "bedroom_median_rents": bedroom_rows,
        "size_rent_spearman": correlation_value,
        "chart_titles": {
            "rent_by_city": city_rent_title,
            "listing_counts_by_city": count_title,
            "rent_vs_size": size_title,
            "rent_by_bedrooms": bedroom_title,
        },
    }


def write_analysis_outputs(cleaned: pd.DataFrame, output_dir: Path) -> dict[str, Any]:
    """Write summary tables and charts, returning the calculated report."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import StrMethodFormatter

    summary = summarize_listings(cleaned)
    eligible = eligible_listings(cleaned)
    figure_dir = output_dir / "figures"
    report_dir = output_dir / "reports"
    figure_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    cities = [row["city"] for row in summary["city_counts"]]
    city_groups = [eligible.loc[eligible["city"].eq(city), "price"] for city in cities]
    city_labels = [
        f"{row['city']} (n={row['eligible_listings']})"
        for row in summary["city_counts"]
    ]
    figure, axis = plt.subplots(figsize=(9, 5))
    axis.boxplot(city_groups)
    axis.set_xticks(range(1, len(city_labels) + 1), labels=city_labels)
    axis.set_title(summary["chart_titles"]["rent_by_city"])
    axis.set_ylabel("Yearly asking rent (SAR)")
    axis.set_xlabel("City (eligible listings)")
    axis.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    figure.tight_layout()
    figure.savefig(figure_dir / "rent_by_city.png", dpi=150)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(9, 5))
    counts = [row["deduplicated_listings"] for row in summary["city_counts"]]
    axis.bar(cities, counts, color="#327a72")
    axis.set_title(summary["chart_titles"]["listing_counts_by_city"])
    axis.set_ylabel("Deduplicated listings")
    axis.set_xlabel("City")
    for index, count in enumerate(counts):
        axis.text(index, count, str(count), ha="center", va="bottom")
    figure.tight_layout()
    figure.savefig(figure_dir / "listing_counts_by_city.png", dpi=150)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(8, 5))
    axis.scatter(eligible["size"], eligible["price"], alpha=0.65, color="#c56b3f")
    axis.set_title(summary["chart_titles"]["rent_vs_size"])
    axis.set_xlabel("Property size (m²)")
    axis.set_ylabel("Yearly asking rent (SAR)")
    axis.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    figure.tight_layout()
    figure.savefig(figure_dir / "rent_vs_size.png", dpi=150)
    plt.close(figure)

    bedroom_rows = summary["bedroom_median_rents"]
    figure, axis = plt.subplots(figsize=(8, 5))
    bars = axis.bar(
        [row["bedroom_label"] for row in bedroom_rows],
        [row["median_asking_rent_sar"] for row in bedroom_rows],
        color="#327a72",
    )
    axis.set_title(fill(summary["chart_titles"]["rent_by_bedrooms"], width=46))
    axis.set_xlabel("Bedrooms")
    axis.set_ylabel("Median yearly asking rent (SAR)")
    axis.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    for bar, row in zip(bars, bedroom_rows):
        axis.annotate(
            f"n={row['listing_count']}",
            (bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
        )
    figure.tight_layout()
    figure.savefig(figure_dir / "rent_by_bedrooms.png", dpi=150)
    plt.close(figure)

    lines = [
        "# Analysis summary",
        "",
        f"The cleaned sample contains {summary['deduplicated_listing_count']:,} "
        f"deduplicated listings; {summary['eligible_listing_count']:,} meet the "
        "confirmed price and size bounds.",
        "",
        "## Listings and median yearly asking rent by city",
        "",
        (
            "| City | Deduplicated listings | Eligible listings | "
            "Median asking rent (SAR/year) |"
        ),
        "|---|---:|---:|---:|",
    ]
    lines.extend(
        f"| {row['city']} | {row['deduplicated_listings']} | "
        f"{row['eligible_listings']} | {row['median_asking_rent_sar']:,.0f} |"
        for row in summary["city_counts"]
    )
    lines.extend(
        [
            "",
            "## Findings",
            "",
            *[f"- {title}." for title in summary["chart_titles"].values()],
            "",
            "These are scraped asking listings, not completed lease prices; "
            "associations are descriptive and not causal.",
        ]
    )
    (report_dir / "analysis_summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return summary
