PYTHON := .venv/bin/python
PIP := .venv/bin/pip

.PHONY: install test validate-data clean-data analyze train pipeline docker-build docker-run clean

install: $(PYTHON)
	$(PIP) install -e ".[dev]"

$(PYTHON):
	python3.12 -m venv .venv

test: install
	$(PYTHON) -m pytest

validate-data: install
	$(PYTHON) -m aqar_rent.cli validate-data

clean-data: install
	$(PYTHON) -m aqar_rent.cli clean-data

analyze: install
	$(PYTHON) -m aqar_rent.cli analyze

train: install
	$(PYTHON) -m aqar_rent.cli train

pipeline:
	$(MAKE) validate-data
	$(MAKE) clean-data
	$(MAKE) analyze
	$(MAKE) train

docker-build:
	docker build -t aqar-rent .

docker-run:
	docker run --rm -e AQAR_DATA_PATH=/app/data/SA_Aqar.csv -e AQAR_OUTPUT_DIR=/app/artifacts -v "$(CURDIR)/data:/app/data:ro" -v "$(CURDIR)/artifacts:/app/artifacts" aqar-rent

clean:
	rm -rf artifacts
