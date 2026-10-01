# Saudi Rental Listings

A reproducible Python project for validating and exploring scraped rental
listings from Riyadh, Jeddah, Dammam, and Al Khobar. These are asking listings,
not completed lease prices or certified valuations.

## Setup

Use Python 3.12 and the project-local virtual environment:

```sh
make install
make test
```

The Makefile is the supported interface. Raw input defaults to
`data/SA_Aqar.csv`; set `AQAR_DATA_PATH` to use another CSV. Generated files
default to `artifacts/`; set `AQAR_OUTPUT_DIR` to change that location.

## Obtain the data

Download `SA_Aqar.csv` from [Saudi Arabia Real Estate (AQAR) by Lama Alharbi](
https://www.kaggle.com/datasets/lama122/saudi-arabia-real-estate-aqar) using
your Kaggle account. Place the file at `data/SA_Aqar.csv`. The raw file is
ignored by Git; do not commit or copy it into the project image. Tests use small
synthetic fixtures and do not need the Kaggle download.

## Data labels

The following source categories are translated for readers and charts:

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

## Current commands

`make validate-data` checks the retained structured fields. `make clean-data`
writes the transformed table and audit summary. `make analyze` creates city and
property summaries plus PNG charts; `make train` writes a held-out reference
model report. `make pipeline` runs those steps in order. Generated reports,
figures, and model files live under `artifacts/`.

The analysis reports deduplicated and eligible listing counts by city. The
bedroom chart shows sample counts and groups seven or more bedrooms as `7+`.
Rent charts use yearly SAR and thousands separators. The model report compares
held-out MAE and median absolute error with a city-median baseline, reports
errors and sample sizes by city, and includes permutation importance measured
on the held-out set. Importance is descriptive, not causal; correlated inputs
can share or mask one another's importance.

## Docker

With Docker Desktop running and the local Kaggle file in `data/`, run:

```sh
make docker-build
make docker-run
```

The image uses Python 3.12 and defaults to the full validation, cleaning,
analysis, and training pipeline. `data/` is excluded from the build context and
mounted read-only at `/app/data`; generated `artifacts/` are mounted writable
at `/app/artifacts`. The container does not download the dataset. The same
pipeline can be run locally with `make pipeline`.
