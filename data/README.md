# Data

Raw files are not committed. Run `python scripts/download_data.py` to fetch them from the
[Upworthy Research Archive on OSF](https://osf.io/jd64p/) into `data/raw/`:

| File | Sample | Packages | Used in |
|---|---|---|---|
| `upworthy-exploratory.csv` | exploratory | 22,666 | notebooks 01–04 |
| `upworthy-confirmatory.csv` | confirmatory | 105,551 | notebook 04 (confirmation only) |

The holdout sample is intentionally never downloaded.

Citation: Matias, J. N., Munger, K., Aubin Le Quere, M., & Ebersole, C. (2021). The Upworthy Research
Archive, a time series of 32,487 experiments in U.S. media. *Scientific Data*, 8, 195.
https://doi.org/10.1038/s41597-021-00934-7 — licensed CC BY 4.0.
