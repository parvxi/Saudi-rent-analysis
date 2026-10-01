FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AQAR_DATA_PATH=/app/data/SA_Aqar.csv \
    AQAR_OUTPUT_DIR=/app/artifacts \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/

RUN python -m pip install --no-cache-dir .

CMD ["python", "-m", "aqar_rent.cli", "pipeline"]