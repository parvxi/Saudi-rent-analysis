Implement CSV loading with explicit UTF-8 handling and multiline-quoted-field support. Validate the source header and row widths, but omit `details` from the loaded table without reading or validating its values. Validate retained columns for structured nulls, numeric parseability/finiteness, indicator domains, known city/front categories, and duplicates. Write a concise machine-readable and human-readable validation report without mutating the source or reporting anything about `details`.
# Saudi Rental Listings: Project Plan

## Project overview

Build a small, reproducible Python project to explore rental listings in Riyadh, Jeddah, Dammam, and Khobar, explain which recorded property and location features are associated with asking rent, and estimate a reference rent for a comparable listing. This is an estimate from scraped asking listings, not a certified valuation or evidence of completed lease prices.

### Requirements

- Use Python 3.12 and a modular package, not a single script.
- Make the Makefile the public interface: `make install`, `make test`, `make validate-data`, `make clean-data`, `make analyze`, `make train`, `make pipeline`, `make docker-build`, `make docker-run`, and `make clean`.
- Validate the raw CSV without changing it; make cleaning deterministic and write derived files separately.
- Use pytest with `unit`, `regression`, and `integration` markers; use Black and Flake8.
- Produce English chart labels and claim-first English titles that state the finding, not merely the variable names.
- Include a Dockerfile and `.dockerignore`; the container must run a useful pipeline command.
- Keep the scope small enough to build in one afternoon: no scraper, web app, geocoding, text NLP, or extensive hyperparameter search.

### Important files and proposed structure

The repository currently contains `.gitignore`, the local `data/SA_Aqar.csv`, and this plan. There is no README, package, test suite, or build configuration. The existing `.gitignore` ignores all of `data/`, and the CSV is not tracked by Git. Add a README explaining how to obtain the dataset from Kaggle; never commit the CSV.

```text
.
├── README.md                  # setup, pipeline commands, and Kaggle data download
├── Makefile
├── pyproject.toml             # Python 3.12, dependencies, pytest/Black config
├── .flake8
├── Dockerfile
├── .dockerignore
├── data/
│   └── SA_Aqar.csv            # local raw input; never overwrite
├── docs/
│   └── plan.md
├── src/aqar_rent/
│   ├── __init__.py
│   ├── cli.py                 # internal command entry point
│   ├── paths.py               # input/output paths and environment settings
│   ├── schema.py              # expected columns and validation rules
│   ├── cleaning.py
│   ├── analysis.py
│   └── modeling.py
├── tests/
│   ├── unit/
│   ├── regression/
│   └── integration/
└── artifacts/                 # generated, ignored outputs; never raw input
    ├── cleaned/
    ├── reports/
    ├── figures/
    └── model/
```

The Makefile wraps all supported user actions; the Python CLI is an implementation detail. `make pipeline` runs `validate-data`, `clean-data`, `analyze`, and `train` sequentially. `make clean-data` creates cleaned data, while `make clean` removes generated artifacts only and must never delete or rewrite the raw CSV.

### README translation table

The README should include these Arabic-to-English mappings so readers can interpret the source categories. The `front` street-count values are normalized to the shared `Corner` category.

| Field | Arabic value | English label |
|---|---|---|
| `city` | الخبر | Al Khobar |
| `city` | الدمام | Dammam |
| `city` | الرياض | Riyadh |
| `city` | جدة | Jeddah |
| `front` | جنوب | South |
| `front` | جنوب شرقي | Southeast |
| `front` | جنوب غربي | Southwest |
| `front` | شرق | East |
| `front` | شمال | North |
| `front` | شمال شرقي | Northeast |
| `front` | شمال غربي | Northwest |
| `front` | غرب | West |
| `front` | 3 شوارع | Corner |
| `front` | 4 شوارع | Corner |

### Risks and design concerns

- `details` may contain contact information. Exclude the entire column as part of loading, never inspect, retain, process, or print its values, and do not include it in derived files.
- The CSV is a local Kaggle input: never commit or redistribute it. Document Kaggle download steps in the README and keep `data/` ignored by Git and outside the Docker build context.
- Treat `price` as yearly rent in SAR and `size` as m². Keep out-of-range values visible in cleaning flags/reports, but exclude them from analysis/model inputs using the confirmed bounds below.
- Asking prices are not transacted rents; a model cannot establish an objective or legally reliable "fair" price. Report validation error and sample limitations with every estimate.
- The file has no listing ID, scrape timestamp, or source-update field. Exact duplicates can be detected, but distinct homes with identical recorded values cannot be distinguished; temporal changes and reliable listing-level grouping are unavailable.
- Listings are unevenly distributed across cities/neighborhoods. A single pooled estimate can hide coverage gaps; show city-level results and avoid unsupported extrapolation.
- Small data and outliers can distort charts and model fit. Preserve source values, flag questionable records, and report sensitivity to exclusions rather than silently deleting observations.
- Keep the raw CSV local and read-only in pipeline/Docker use. Tests use small synthetic fixtures, not the Kaggle CSV.

### Initial data-quality findings and proposed handling

Inspected `data/SA_Aqar.csv` with a CSV-aware parser: 3,718 records and 24 columns. All rows have the expected width; every `city` and `district` value has surrounding whitespace. After excluding `details`, there are 2,207 extra exact duplicate rows and 1,511 unique signatures across the retained columns. All 14 amenity/room indicator fields inspected contain only `0` or `1`. City values correspond to the four stated cities, encoded in Arabic. The `front` field contains Arabic directions and street-count values, including `3 شوارع` and `4 شوارع` for corner houses. The `details` column is excluded from loading and is not inspected.

| Finding | Proposed handling |
|---|---|
| Every city/district string is whitespace-padded; city values are Arabic. | Preserve raw input; trim normalized values, map the four known city names explicitly to English labels for charts, and retain an unknown-value validation error rather than guessing transliterations. Do not use district in charts or the model. |
| 2,207 extra duplicate rows after excluding `details`, with no listing ID or timestamp. | Report duplicate counts in validation and remove exact duplicate rows across retained columns before analysis/modeling, recording before/after counts. `details` is never loaded or used for duplicate detection; do not collapse merely similar homes. |
| `details` may contain people/contact details. | Drop the `details` column completely while loading. Never inspect, retain, process, log, report, or model its values. |
| `size` ranges from 1 to 95,000 (median 330; 99th percentile 1,000); unit is m². | Validate finite numeric values, flag sizes below 50 or above 2,000 m² in the cleaning report, and exclude those rows from analysis/modeling. |
| `price` ranges from 1,000 to 1,700,000 (median 70,000; 99th percentile 300,000); it is yearly rent in SAR. | Validate finite numeric values, flag prices below 10,000 or above 500,000 SAR in the cleaning report, and exclude those rows from analysis/modeling. Do not annualize or convert the target. |
| `front` contains Arabic directions and street-count values such as `3 شوارع` and `4 شوارع`. | Translate direction values into English and map multi-street values to the `corner` category; test the mapping with synthetic fixtures. |
| There are no explicit nulls in structured columns and no malformed-width rows; checked indicators are consistently binary. | Keep these as baseline schema checks, but fail validation on future unexpected missing, nonnumeric, nonfinite, or nonbinary values and report offending column/count without exposing descriptions. |
| No ID, scrape time, or transaction/rent-period metadata is present. | State that temporal trends, listing-level leakage control, and transaction-price fairness cannot be established. Evaluate on a reproducible holdout after duplicate handling and report its limitations; do not claim causal feature effects. |

## Stage 0 — Project skeleton
### Goal
Create the Python 3.12 package, reproducible development setup, test layout, and Makefile interface before implementing analysis.
### Proposed changes
Add a minimal `src/` package, configuration, dependency list, standard Make targets including `validate-data` and sequential `pipeline`, README with Kaggle download instructions, and tests separated by marker. Configure Python 3.12, pytest markers, Black, and Flake8. Establish generated-output paths and ensure `make clean` never touches raw inputs.
### Important files
`pyproject.toml`, `.flake8`, `Makefile`, `src/aqar_rent/__init__.py`, `src/aqar_rent/cli.py`, `src/aqar_rent/paths.py`, `tests/unit/`, `tests/regression/`, `tests/integration/`.
### Architecture / boundaries
The package owns logic; Make targets are the supported interface and call package entry points. Paths/configuration are centralized. Keep dependencies limited to pandas, matplotlib, scikit-learn, pytest, Black, and Flake8 as needed by later stages.
### Risks
The current machine does not have pandas available as `python3`; setup must explicitly use Python 3.12 and install project dependencies in an isolated environment. Do not add or commit the ignored dataset as part of scaffolding.
### Automated tests (Unit / Regression / Integration)
- **Unit:** path/config defaults and Python-version/config smoke checks.
- **Regression:** verify expected public Make targets, including `pipeline`, and stable package entry point behavior.
- **Integration:** install package in an isolated environment and invoke a harmless CLI help/usage path.
### Manual Smoke Test
#### What we're proving
The project installs under Python 3.12 and the skeleton and expected test directories exist.
#### Terminal (pasteable make commands)
```sh
make install
find src tests -maxdepth 3 -type f -print
make -n analyze
```
#### Watch for
`make install` must not depend on a system-wide package install; `make -n analyze` should resolve to the project package, not a one-off script.
#### Stop
Stop if the selected interpreter is not Python 3.12, package installation requires elevated privileges, or the Makefile bypasses the package interface.

## Stage 1 — Load and validate raw data
### Goal
Read the CSV safely and make its schema and data-quality state visible before cleaning.
### Proposed changes
Implement CSV loading with explicit UTF-8 handling and multiline-quoted-field support. Validate the source header and row widths, but omit `details` from the loaded table without reading or validating its values. Validate retained columns for structured nulls, numeric parseability/finiteness, indicator domains, city values, and duplicates. Write a concise machine-readable and human-readable validation report without mutating the source or reporting anything about `details`.
### Important files
`src/aqar_rent/schema.py`, `src/aqar_rent/io.py` (add if useful), `src/aqar_rent/validation.py` (add if useful), `Makefile`, `artifacts/reports/data_validation.json`, `artifacts/reports/data_validation.txt`.
### Architecture / boundaries
The loader returns retained raw values with `details` omitted; validation reports findings and never cleans or drops rows. User-facing operations are exposed through a `make validate-data` target. The loaded table has the 23 retained columns; `details` contents are never read or included in reports.
### Risks
CSV fields can contain embedded newlines, so physical line counts are not record counts. Drop `details` from the loaded table before any downstream operation; validation must not inspect or report its contents.
### Automated tests (Unit / Regression / Integration)
- **Unit:** source-header/schema checks, details-column omission, malformed-row handling, and numeric/binary checks using tiny synthetic CSV fixtures including quoted newlines.
- **Regression:** assert the expected 24-column source schema, 23-column loaded schema, and stable aggregate validation facts using synthetic fixtures.
- **Integration:** create a small synthetic CSV fixture, set `AQAR_DATA_PATH` to its path, and run `make validate-data`; verify it leaves fixture bytes unchanged and writes the report without requiring the Kaggle CSV.
### Manual Smoke Test
#### What we're proving
The loader counts logical CSV records correctly, reports the observed quality issues, and leaves the raw file unchanged.
#### Terminal (pasteable make commands)
```sh
make validate-data
cat artifacts/reports/data_validation.txt
```
#### Watch for
The report should show 3,718 records, 24 source columns, and duplicate counts; the loaded table must contain 23 columns and the report must not include details-related values or counts.
#### Stop
Stop on a schema/encoding/row-width error or any report that exposes free-text content; do not proceed to cleaning until validation can be repeated deterministically.

## Stage 2 — Clean the data
### Goal
Produce a reproducible analysis table while preserving raw data and making every transformation auditable.
### Proposed changes
Drop `details` during loading. Trim whitespace; map the four known Arabic city values to English category labels while retaining a raw city field; translate `front` directions to English and map street-count values such as `3 شوارع` and `4 شوارع` to `corner`; coerce validated numeric and indicator fields; remove exact duplicate rows across retained columns; and emit a cleaning summary. Flag prices below 10,000 or above 500,000 SAR and sizes below 50 or above 2,000 m², then exclude those records from analysis/modeling while retaining their flags and counts in the report. Preserve raw price/size values for audit; price is yearly rent in SAR and size is m².
### Important files
`src/aqar_rent/cleaning.py`, `src/aqar_rent/validation.py`, `Makefile`, `artifacts/cleaned/listings.csv`, `artifacts/reports/cleaning_summary.txt`.
### Architecture / boundaries
Cleaning is a deterministic transformation from raw input to a new output path; it never edits `data/SA_Aqar.csv`. Validation/cleaning flags remain available for audit and sensitivity analysis. `make clean-data` runs this transformation; `make clean` only deletes generated artifacts.
### Risks
Exact-row deduplication cannot distinguish separate listings with identical recorded values; document this limitation. Apply the confirmed bounds consistently and report exclusion counts so the filtered sample is transparent.
### Automated tests (Unit / Regression / Integration)
- **Unit:** whitespace and city/front mapping, numeric conversion, details-column removal, outlier flags, and exact dedupe semantics on small synthetic fixtures.
- **Regression:** stable cleaned column contract and counts/summary for the dedupe and confirmed exclusion policy using synthetic fixtures.
- **Integration:** set `AQAR_DATA_PATH` to a small synthetic CSV fixture and run `make clean-data`; verify outputs are repeatable and fixture bytes are unchanged.
### Manual Smoke Test
#### What we're proving
Cleaning writes a separate, readable dataset and summary, with transformations and exclusions accounted for.
#### Terminal (pasteable make commands)
```sh
make clean-data
head -n 5 artifacts/cleaned/listings.csv
cat artifacts/reports/cleaning_summary.txt
```
#### Watch for
English city and `front` categories should be explicit. Check flagged exclusions and before/after counts; verify the `details` column is absent.
#### Stop
Stop if raw data changes, rows disappear without a reported rule, or the cleaning report does not account for duplicate and out-of-range exclusions.

## Stage 3 — Analysis and charts
### Goal
Describe the observed rent distribution and how recorded features vary across the four cities.
### Proposed changes
Create a compact set of reproducible tables and charts: listing/rent distributions by city, rent versus size, and bedroom comparisons. Bedroom bars show sample counts, group seven or more bedrooms as `7+`, and use a claim-first title reflecting the observed rent peak. Format rent axes with thousands separators. Use English labels and claim-first titles based on actual computed findings (for example, “Riyadh listings have the highest median asking rent in this sample” only if the result supports it). Write a concise text/Markdown summary and PNGs.
### Important files
`src/aqar_rent/analysis.py`, `src/aqar_rent/charts.py`, `Makefile`, `artifacts/reports/analysis_summary.md`, `artifacts/figures/`.
### Architecture / boundaries
Analysis consumes the cleaned table and produces aggregate reports/figures only. Keep chart wording data-driven, label yearly asking rent in SAR and size in m², and show city sample sizes. Avoid causal language and exclude `details` and district.
### Risks
The sample is scraped listing inventory, not a random sample of homes or completed rents; exclusions and duplicate removal can change results. Do not make a claim-first title until the calculated finding supports it. Exclude district and details from charts.
### Automated tests (Unit / Regression / Integration)
- **Unit:** grouped summaries, sorting, chart labels/title generation, and empty/unknown-category behavior.
- **Regression:** assert stable aggregate outputs on a small fixture and required English, claim-first chart text.
- **Integration:** set `AQAR_DATA_PATH` to a small synthetic CSV fixture and run the pipeline through analysis; verify it creates a readable summary and nonempty chart files without the Kaggle CSV.
### Manual Smoke Test
#### What we're proving
The analysis produces reviewable findings and figures with correct English titles and no hidden dependence on notebooks.
#### Terminal (pasteable make commands)
```sh
make analyze
cat artifacts/reports/analysis_summary.md
file artifacts/figures/*.png
```
#### Watch for
Summary counts should match the validated/cleaned data; figure files should be nonempty; titles must state supported findings, not just “Rent by City.” Label the target as yearly asking rent in SAR and size as m².
#### Stop
Stop if a chart omits a city/sample-size context, renders an unsupported comparison, or includes any `details` content.

## Stage 4 — Simple rent model
### Goal
Estimate a reference asking rent for a property profile and show how reliable that estimate is on held-out listings.
### Proposed changes
Use yearly rent in SAR as the target and implement a modest scikit-learn pipeline using city, translated `front` category, size, bedrooms, bathrooms, property age, and selected binary amenities. Exclude district and `details`. Train only after exact deduplication and the confirmed price/size exclusions. Compare with a city-level median baseline. Report MAE and median absolute error overall and by city, plus a prediction for a clearly specified example. Compute permutation importance on held-out data using MAE increase, include its ranking in the report and a figure, and explain that correlated features can share or obscure importance. Do not use built-in forest importances or coefficients. Call output a reference estimate, not a definitive fair/market rent.
### Important files
`src/aqar_rent/modeling.py`, `src/aqar_rent/charts.py`, `src/aqar_rent/cli.py`, `Makefile`, `artifacts/model/metrics.json`, `artifacts/model/reference_model.joblib`, `artifacts/reports/model_summary.md`, `artifacts/figures/permutation_importance.png`.
### Architecture / boundaries
Training consumes only the cleaned table, uses a fixed random seed and a documented holdout, and compares against the baseline. Deduplicate before splitting; disclose that absent listing IDs prevent robust listing-level grouping. Save model and metrics under generated artifacts only.
### Risks
Small effective sample size (1,511 unique retained-column signatures after exact deduplication), city imbalance, and lack of transaction data constrain accuracy and generalization. A random holdout does not prove performance on unseen neighborhoods or future market conditions; district is intentionally excluded because of its sparse categories.
### Automated tests (Unit / Regression / Integration)
- **Unit:** feature/target selection, preprocessing, fixed-seed split, baseline, and metric calculation.
- **Regression:** metrics and example prediction remain within documented tolerances on a small synthetic fixture; no text feature enters the model.
- **Integration:** set `AQAR_DATA_PATH` to a small synthetic CSV fixture and run the pipeline through training; verify it fits, evaluates against the baseline, and writes model/metrics/summary artifacts without the Kaggle CSV.
### Manual Smoke Test
#### What we're proving
Training produces a saved model, an interpretable validation report, and a usable reference estimate without presenting training fit as expected real-world accuracy.
#### Terminal (pasteable make commands)
```sh
make train
cat artifacts/model/metrics.json
cat artifacts/reports/model_summary.md
```
#### Watch for
The model must be compared with the baseline and use held-out data. Check per-city sample counts/error, unit labeling, and the stated split limitations.
#### Stop
Stop if the model uses district/details, fails to apply the confirmed exclusions, omits held-out error, or is described as a guaranteed/certified fair rent.

## Stage 5 — Docker
### Goal
Run a meaningful pipeline command in a reproducible Python 3.12 container without embedding the ignored raw CSV in the image.
### Proposed changes
Add a small `python:3.12-slim`-based `Dockerfile` and `.dockerignore`. Install only runtime dependencies, copy package/config files, and set the container command to run the full pipeline (`python -m aqar_rent.cli pipeline`). Add `make pipeline`, `make docker-build`, and `make docker-run`; `make pipeline` runs validation, cleaning, analysis, and training sequentially. Run with a read-only bind mount for the host `data/` directory and a writable bind mount for `artifacts/`; the image must not fetch data from the network.
### Important files
`Dockerfile`, `.dockerignore`, `Makefile`, `src/aqar_rent/paths.py`, `data/SA_Aqar.csv` (host-provided input), `artifacts/` (host-visible output).
### Architecture / boundaries
Build context excludes `.git/`, virtual environments, caches, generated `artifacts/`, and `data/`. At runtime, mount `$(CURDIR)/data` at `/app/data:ro` and `$(CURDIR)/artifacts` at `/app/artifacts`; the container reads `/app/data/SA_Aqar.csv` by default and writes reports/figures/model outputs under `/app/artifacts`. `make docker-run` invokes the image's full-pipeline command with `--rm` and these mounts. Proposed environment variables: `AQAR_DATA_PATH=/app/data/SA_Aqar.csv` and `AQAR_OUTPUT_DIR=/app/artifacts`. This uses the local ignored file rather than copying it into Git or the image.
### Risks
Container paths and output permissions must work on macOS Docker Desktop. Avoid baking the Kaggle CSV, credentials, or generated reports into image layers; the README documents how to obtain the local input, which remains uncommitted.
### Automated tests (Unit / Regression / Integration)
- **Unit:** environment-variable path resolution and missing-input errors.
- **Regression:** confirm image configuration uses Python 3.12 and the default command runs the full pipeline entry point.
- **Integration:** build the image, create a small synthetic CSV fixture, mount it read-only, set container `AQAR_DATA_PATH` to the fixture path, and run the full pipeline; verify the host sees validation, cleaning, analysis, and model artifacts and the image has no Kaggle CSV.
### Manual Smoke Test
#### What we're proving
The container can read the host-provided CSV read-only, run the analysis, and leave readable results on the host.
#### Terminal (pasteable make commands)
```sh
make docker-build
make docker-run
cat artifacts/reports/analysis_summary.md
file artifacts/figures/*.png
```
#### Watch for
Build context/image must not contain `data/SA_Aqar.csv`; run must not require a network download. Confirm paths, environment variables, read-only input, writable output, English claim-first titles, and no raw text in reports.
#### Stop
Stop on any attempt to copy the CSV into the image or mutate the mounted input. Verify README download instructions and that the CSV remains untracked.
