"""Loading and cleaning the Upworthy Research Archive.

Each row in the archive is a *package* (one arm of an experiment). Packages that
share a ``clickability_test_id`` were randomized against each other. Readers saw
the headline and the image (``eyecatcher_id``); excerpt, lede and share text
were not part of the tested stimulus according to the archive documentation.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"

OSF_URLS = {
    "exploratory": "https://osf.io/download/3vqmp/",
    "confirmatory": "https://osf.io/download/vy8mj/",
}
# SHA-256 of the files this analysis was run on (OSF versions dated 03.12.2020).
# A mismatch means the upstream data changed and every result must be re-checked.
SHA256 = {
    "exploratory": "8368313b060f4015a0c6fb34e6d788163cee29554144aba9390b14922eb9d8ce",
    "confirmatory": "b2a88288c88f2b67d40413c9bdbebe79a1c0b5d9a9354180549f59f3bfff685f",
}
EXPECTED_ROWS = {"exploratory": 22_666, "confirmatory": 105_551}

# The archive maintainers reported systematic randomization problems for tests
# run in this window (June 2024 update) and discourage using them.
PROBLEM_START = pd.Timestamp("2013-06-25")
PROBLEM_END = pd.Timestamp("2014-01-11")  # exclusive: covers Jan 10, 2014


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def raw_path(sample: str) -> Path:
    if sample not in OSF_URLS:
        raise ValueError(f"unknown sample {sample!r}; expected one of {sorted(OSF_URLS)}")
    return RAW_DIR / f"upworthy-{sample}.csv"


def load_packages(sample: str = "exploratory", verify: bool = True) -> pd.DataFrame:
    """Load one archive sample and add derived columns.

    With ``verify`` the file's checksum and row count must match the versions
    this analysis was built on; anything else raises rather than silently
    producing different numbers.
    """
    path = raw_path(sample)
    if not path.exists():
        raise FileNotFoundError(f"{path} not found - run `python scripts/download_data.py` first.")
    if verify and (digest := sha256(path)) != SHA256[sample]:
        raise ValueError(f"{path.name}: sha256 {digest} does not match the expected {SHA256[sample]}")
    df = pd.read_csv(path, index_col=0, low_memory=False)
    if verify and len(df) != EXPECTED_ROWS[sample]:
        raise ValueError(f"{path.name}: {len(df):,} rows, expected {EXPECTED_ROWS[sample]:,}")
    df["created_at"] = pd.to_datetime(df["created_at"], format="mixed")
    df = df.rename(columns={"clickability_test_id": "test_id"})
    df["eyecatcher_id"] = df["eyecatcher_id"].fillna("missing")
    df["ctr"] = df["clicks"] / df["impressions"]
    df["problem"] = df["created_at"].between(PROBLEM_START, PROBLEM_END, inclusive="left")
    return df


def classify_tests(df: pd.DataFrame) -> pd.Series:
    """Label each test by what varied between its arms.

    headline  - headlines differ, image constant
    image     - image differs, headline constant
    both      - both differ
    same_stim - headline and image identical in every arm (near A/A test)
    """
    g = df.groupby("test_id")
    h = g["headline"].nunique() > 1
    e = g["eyecatcher_id"].nunique() > 1
    kind = np.select([h & ~e, ~h & e, h & e], ["headline", "image", "both"], default="same_stim")
    return pd.Series(kind, index=h.index, name="kind")


def headline_arms(df: pd.DataFrame, exclude_problem: bool = True) -> pd.DataFrame:
    """Arm-level table for headline-only tests.

    Packages with an identical headline inside a test are the same stimulus, so
    they are pooled. The control is the earliest-created headline - the
    editor's first draft - and every other headline is a treatment.
    """
    kinds = classify_tests(df)
    sub = df[df["test_id"].isin(kinds.index[kinds == "headline"])]
    if exclude_problem:
        bad = sub.groupby("test_id")["problem"].transform("max")
        sub = sub[~bad]
    arms = (
        sub.groupby(["test_id", "headline"], sort=False)
        .agg(created_at=("created_at", "min"), impressions=("impressions", "sum"),
             clicks=("clicks", "sum"), first_place=("first_place", "max"),
             test_week=("test_week", "first"))
        .reset_index()
        .sort_values(["test_id", "created_at"])
    )
    arms["arm"] = arms.groupby("test_id").cumcount()
    arms["is_control"] = arms["arm"] == 0
    arms["n_arms"] = arms.groupby("test_id")["arm"].transform("size")
    arms["ctr"] = arms["clicks"] / arms["impressions"]
    return arms.reset_index(drop=True)


def test_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per test: type, size, SRM check and omnibus chi-square p-value."""
    kinds = classify_tests(df)
    rows = []
    for tid, x in df.groupby("test_id"):
        imp, clk = x["impressions"].to_numpy(), x["clicks"].to_numpy()
        omni = np.nan
        if clk.sum() > 0 and len(x) > 1:
            omni = stats.chi2_contingency(np.vstack([clk, imp - clk]))[1]
        rows.append({
            "test_id": tid,
            "kind": kinds[tid],
            "n_arms": len(x),
            "created_at": x["created_at"].min(),
            "problem": bool(x["problem"].any()),
            "impressions": imp.sum(),
            "clicks": clk.sum(),
            "srm_p": stats.chisquare(imp).pvalue if len(x) > 1 else np.nan,
            "omnibus_p": omni,
        })
    return pd.DataFrame(rows)


def package_arms(df: pd.DataFrame, kind: str, exclude_problem: bool = True) -> pd.DataFrame:
    """Arm table where every package is its own arm, for tests of one ``kind``.
    Used for same-stimulus (near A/A) tests, where pooling by headline would
    collapse the whole test into a single arm."""
    kinds = classify_tests(df)
    sub = df[df["test_id"].isin(kinds.index[kinds == kind])]
    if exclude_problem:
        sub = sub[~sub.groupby("test_id")["problem"].transform("max")]
    arms = sub.sort_values(["test_id", "created_at"]).reset_index(drop=True)
    arms["arm"] = arms.groupby("test_id").cumcount()
    arms["is_control"] = arms["arm"] == 0
    arms["n_arms"] = arms.groupby("test_id")["arm"].transform("size")
    return arms


def vs_control(arms: pd.DataFrame) -> pd.DataFrame:
    """One row per treatment arm with its test's control counts alongside
    (``clicks_c``, ``impressions_c``, ``ctr_c``)."""
    ctl = (arms.loc[arms["is_control"]]
           .set_index("test_id")[["clicks", "impressions", "ctr"]]
           .add_suffix("_c"))
    return arms.loc[~arms["is_control"]].merge(ctl, left_on="test_id", right_index=True)
