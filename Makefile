PY ?= python

.PHONY: all install data lint test notebooks site serve

all: install data lint test notebooks site

install:
	$(PY) -m pip install -e ".[dev]"

data:
	$(PY) scripts/download_data.py

lint:
	ruff check src scripts tests

test:
	$(PY) -m pytest -q

notebooks:
	cd notebooks && for nb in 01_experiment_case_study 02_portfolio_meta_analysis 03_simulations 04_headline_features; do \
		jupyter nbconvert --to notebook --execute --inplace $$nb.ipynb || exit 1; \
	done

site:
	$(PY) scripts/build_site_data.py

serve:
	$(PY) -m http.server 8000 -d docs
