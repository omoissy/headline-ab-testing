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

## Integrity

`scripts/download_data.py` and `abtest.data.load_packages()` check every file against the SHA-256 and row
count pinned in `src/abtest/data.py`. If the upstream data changes, loading fails loudly instead of quietly
producing different numbers.

| Sample | SHA-256 | Rows |
|---|---|---|
| exploratory | `8368313b060f4015a0c6fb34e6d788163cee29554144aba9390b14922eb9d8ce` | 22,666 |
| confirmatory | `b2a88288c88f2b67d40413c9bdbebe79a1c0b5d9a9354180549f59f3bfff685f` | 105,551 |

## Data dictionary

| Column | Meaning | Used as |
|---|---|---|
| `clickability_test_id` | ID of one randomized experiment. Packages that share it were randomized against each other. | renamed `test_id`, grouping key |
| `created_at` | When the package was created (timezone unknown) | orders arms; the earliest headline is the **control** |
| `headline` | Headline text shown to readers | treatment; identical headlines in a test are pooled into one arm |
| `eyecatcher_id` | ID of the image shown (images are not distributed) | defines test type; missing → `"missing"` |
| `impressions` | Number of times the package was shown | denominator |
| `clicks` | Clicks on the package | numerator |
| `first_place` | Leader in Upworthy's internal dashboard | compared with our statistics in notebook 02 |
| `winner` | Package editors chose to publish | not used |
| `excerpt`, `lede`, `share_text`, `slug`, `square` | Not part of the tested stimulus, per the archive documentation | not used |
| `significance`, `updated_at`, `test_week` | Dashboard internals and sampling stratum | not used |

**Derived fields** (in `abtest.data`)

| Field | Definition |
|---|---|
| `ctr` | `clicks / impressions` |
| `problem` | `created_at` within 25 Jun 2013 to 10 Jan 2014, the window the maintainers reported as having randomization problems. Tests touching it are excluded. |
| test `kind` | `headline` (headlines differ, image fixed) · `image` · `both` · `same_stim` (identical headline and image in every arm, used as near-A/A tests) |
| `is_control` | The earliest-created headline in a headline test, i.e. the editor's first draft |
