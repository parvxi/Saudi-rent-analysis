import pandas as pd
import pytest

from aqar_rent.analysis import AnalysisError, summarize_listings
from aqar_rent.charts import claim_first_titles


def cleaned_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "city": "Riyadh",
                "price": 100_000,
                "size": 100,
                "bedrooms": 2,
                "analysis_eligible": True,
            },
            {
                "city": "Riyadh",
                "price": 120_000,
                "size": 200,
                "bedrooms": 3,
                "analysis_eligible": True,
            },
            {
                "city": "Jeddah",
                "price": 60_000,
                "size": 150,
                "bedrooms": 2,
                "analysis_eligible": True,
            },
            {
                "city": "Jeddah",
                "price": 40_000,
                "size": 50,
                "bedrooms": 1,
                "analysis_eligible": False,
            },
        ]
    )


@pytest.mark.unit
def test_summary_reports_deduplicated_and_eligible_city_counts() -> None:
    summary = summarize_listings(cleaned_rows())

    assert summary["deduplicated_listing_count"] == 4
    assert summary["eligible_listing_count"] == 3
    assert summary["city_counts"] == [
        {
            "city": "Jeddah",
            "deduplicated_listings": 2,
            "eligible_listings": 1,
            "median_asking_rent_sar": 60_000.0,
        },
        {
            "city": "Riyadh",
            "deduplicated_listings": 2,
            "eligible_listings": 2,
            "median_asking_rent_sar": 110_000.0,
        },
    ]


@pytest.mark.unit
def test_titles_are_english_and_claim_first() -> None:
    titles = claim_first_titles(cleaned_rows())

    assert "Riyadh" in titles["rent_by_city"]
    assert "highest median asking rent" in titles["rent_by_city"]
    assert "most listings after deduplication" in titles["listing_counts_by_city"]
    assert all(title.isascii() for title in titles.values())


@pytest.mark.unit
def test_summary_rejects_empty_eligible_sample() -> None:
    rows = cleaned_rows()
    rows["analysis_eligible"] = False

    with pytest.raises(AnalysisError, match="No analysis-eligible listings"):
        summarize_listings(rows)


@pytest.mark.unit
def test_bedroom_summary_shows_sample_sizes_and_groups_seven_plus() -> None:
    rows = []
    for bedrooms, count, rent in (
        (1, 9, 30_000),
        (2, 12, 45_000),
        (3, 20, 100_000),
        (4, 10, 80_000),
        (7, 620, 70_000),
    ):
        rows.extend(
            {
                "city": "Riyadh",
                "price": rent,
                "size": 200,
                "bedrooms": bedrooms,
                "analysis_eligible": True,
            }
            for _ in range(count)
        )

    summary = summarize_listings(pd.DataFrame(rows))

    bedroom_rows = summary["bedroom_median_rents"]
    assert bedroom_rows[0]["listing_count"] == 9
    assert bedroom_rows[1]["listing_count"] == 12
    assert bedroom_rows[-1]["bedroom_label"] == "7+"
    assert bedroom_rows[-1]["listing_count"] == 620
    assert summary["chart_titles"]["rent_by_bedrooms"] == (
        "Median asking rent peaks at 3 bedrooms and does not keep rising "
        "with more bedrooms in this sample"
    )


@pytest.mark.unit
def test_bedroom_chart_labels_counts_and_rent_axes_use_separators(
    tmp_path, monkeypatch
) -> None:
    import matplotlib.pyplot as plt

    from aqar_rent.analysis import write_analysis_outputs

    rows = []
    for bedrooms, count, rent in (
        (1, 9, 30_000),
        (2, 12, 45_000),
        (3, 20, 100_000),
        (4, 10, 80_000),
        (7, 620, 70_000),
    ):
        rows.extend(
            {
                "city": "Riyadh",
                "price": rent,
                "size": 200,
                "bedrooms": bedrooms,
                "analysis_eligible": True,
            }
            for _ in range(count)
        )

    figures = []
    title_bounds = []
    original_close = plt.close

    def capture_figure(figure=None):
        figures.append(figure)
        figure.canvas.draw()
        bounds = figure.axes[0].title.get_window_extent(figure.canvas.get_renderer())
        title_bounds.append((bounds.x0, bounds.x1, figure.bbox.x0, figure.bbox.x1))
        original_close(figure)

    monkeypatch.setattr(plt, "close", capture_figure)
    write_analysis_outputs(pd.DataFrame(rows), tmp_path)

    bedroom_axis = figures[-1].axes[0]
    annotations = {text.get_text() for text in bedroom_axis.texts}
    assert {"n=9", "n=12", "n=620"} <= annotations
    assert bedroom_axis.get_xticklabels()[-1].get_text() == "7+"
    assert bedroom_axis.yaxis.get_major_formatter()(400_000) == "400,000"
    title = bedroom_axis.title.get_text()
    assert (
        title.replace("\n", " ")
        == summarize_listings(pd.DataFrame(rows))["chart_titles"]["rent_by_bedrooms"]
    )
    left, right, figure_left, figure_right = title_bounds[-1]
    assert left >= figure_left
    assert right <= figure_right
    city_axis = figures[0].axes[0]
    assert city_axis.yaxis.get_major_formatter()(400_000) == "400,000"
