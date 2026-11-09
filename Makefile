PY ?= python

.PHONY: all data test notebooks

all: data test notebooks

data:
	$(PY) scripts/download_data.py

test:
	$(PY) -m pytest -q

notebooks:
	cd notebooks && for nb in 01_experiment_case_study 02_portfolio_meta_analysis 03_simulations 04_headline_features; do \
		jupyter nbconvert --to notebook --execute --inplace $$nb.ipynb || exit 1; \
	done
