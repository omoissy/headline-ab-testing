# Changelog

All notable changes to this project. Versions follow [SemVer](https://semver.org/).

## [1.2.0] - 2026-11-09

### Added
- Notebook 05 (robustness): head-to-head win rates with cluster-bootstrap CIs, "long headline" threshold sweep (10–20 words), per-year stability, and failure cases (decisive duels the shorter headline won).
- `abtest.features`: headline features, within-test model and win rates moved out of notebook 04 into the tested library (+4 tests).
- Site: the features section shows head-to-head win rates and the robustness takeaway.

### Changed
- Notebook 04 imports `abtest.features`. Its results are identical to 1.1.0.

## [1.1.0] - 2026-11-09

### Added
- **Interactive site** (`docs/`, GitHub Pages): an explorer for all 1,825 tests, an "analyze your own test" readout, a sample-size planner, an in-browser peeking simulator, and the headline-feature results.
- **`abtest` CLI**: `analyze`, `size` and `mde` subcommands. The package is installable with `pip install -e .`.
- `abtest.readout`: a single readout function shared by the CLI and the site data build.
- Optional A/A variance calibration (`phi`) in intervals, p-values and posteriors.
- Data integrity: pinned SHA-256 and row counts, verified on download and on load.
- Provenance (git commit, dirty flag, package versions, input checksums, seeds) in every results JSON.
- Tests: data contracts, CLI end-to-end and input validation, and JS ↔ Python parity (29 tests in total).
- CI (lint + tests on Python 3.11 and 3.13), issue/PR templates, `CLAUDE.md` project rules, and a data dictionary.

### Changed
- Notebooks import the installed package instead of modifying `sys.path`. All results were regenerated and are numerically identical to 1.0.0.

## [1.0.0] - 2026-11-09

### Added
- Case-study, portfolio meta-analysis, simulation and headline-feature notebooks, the `abtest` library, figures and README.
