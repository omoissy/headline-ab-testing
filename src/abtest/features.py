"""Headline text features and within-test models of their effect on CTR.

Every comparison here is *within* a test: headlines written for the same story,
shown with the same image to the same audience at the same time. That removes
story, image, day and audience as confounders.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

NEGATIVE = (r"\b(?:worst|hate|never|wrong|sad|heartbreaking|terrible|awful|upsetting|horrible|scary|angry|"
            r"fail\w*|dead|die\w*|kill\w*|cry\w*|disturbing|shocking)\b")

LENGTH = "length (+10 words)"


def word_count(headlines: pd.Series) -> pd.Series:
    return headlines.str.split().str.len()


def headline_features(headlines: pd.Series) -> pd.DataFrame:
    """Eight candidate features. Binary features are 0/1; length is in units of 10 words."""
    s = headlines.str
    return pd.DataFrame({
        "number": s.contains(r"\d"),
        "question": s.contains(r"\?"),
        "exclamation": s.contains("!"),
        "you / your": s.contains(r"\b(?:you|your|you're|yourself)\b", case=False),
        "I / me / my": s.contains(r"\b(?:I|I'm|I've|I'd|me|my)\b"),
        "this / these / here's": s.contains(r"\b(?:this|these|here's)\b", case=False),
        "negative word": s.contains(NEGATIVE, case=False),
        LENGTH: word_count(headlines) / 10,
    }, index=headlines.index).astype(float)


FEATURES = list(headline_features(pd.Series(["x"])).columns)


def within_test_fit(arms: pd.DataFrame, X: pd.DataFrame | None = None):
    """Weighted within-test (fixed-effects) regression of empirical log-odds on features.

    Arms are weighted by the inverse sampling variance of their log-odds; outcome
    and features are demeaned within each test using those weights, so anything
    constant within a test drops out. Standard errors are clustered by test,
    which also absorbs extra-binomial noise. Returns (table, fitted model); the
    table reports odds ratios, which at ~1% CTR are close to relative lifts.
    """
    X = headline_features(arms["headline"]) if X is None else X
    c, n = arms["clicks"] + 0.5, arms["impressions"] + 1.0
    y = np.log(c / (n - c))
    w = 1 / (1 / c + 1 / (n - c))
    g = arms["test_id"]

    def demean(v):
        return v - (v.mul(w, axis=0).groupby(g).transform("sum")).div(w.groupby(g).transform("sum"), axis=0)

    Xd, yd = demean(X), demean(y.to_frame("y"))["y"]
    fit = sm.WLS(yd, Xd, weights=w).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(g)[0]})
    ci = fit.conf_int()
    out = pd.DataFrame({"odds_ratio": np.exp(fit.params), "or_lo": np.exp(ci[0]), "or_hi": np.exp(ci[1]),
                        "p": fit.pvalues})
    prevalence = X.gt(0).mean()
    out["share of headlines"] = prevalence.where(prevalence.index != LENGTH, np.nan)
    return out, fit


def pairwise_win_rates(arms: pd.DataFrame, min_word_gap: int = 3, n_boot: int = 2000, seed: int = 0) -> pd.DataFrame:
    """How often does the headline *with* a feature beat one *without* it in the same test?

    For each binary feature, every within-test pair that differs on it is a
    head-to-head matchup; for length, pairs differing by >= ``min_word_gap``
    words, and the longer headline counts as "with". Ties count half. Intervals
    come from a cluster bootstrap over tests, since pairs within a test share
    a control and an audience.
    """
    X = headline_features(arms["headline"])
    words = word_count(arms["headline"]).to_numpy()
    ctr = (arms["clicks"] / arms["impressions"]).to_numpy()
    codes, _ = pd.factorize(arms["test_id"])
    groups = [np.flatnonzero(codes == k) for k in range(codes.max() + 1)]
    rng = np.random.default_rng(seed)
    rows = []
    for feat in FEATURES:
        wins = np.zeros(len(groups))
        pairs = np.zeros(len(groups))
        for k, idx in enumerate(groups):
            if feat == LENGTH:
                i, j = np.triu_indices(len(idx), 1)
                gap = words[idx][i] - words[idx][j]
                keep = np.abs(gap) >= min_word_gap
                longer = np.where(gap > 0, idx[i], idx[j])[keep]
                shorter = np.where(gap > 0, idx[j], idx[i])[keep]
                a, b = ctr[longer], ctr[shorter]
            else:
                has = X[feat].to_numpy()[idx] > 0
                a, b = ctr[idx[has]][:, None], ctr[idx[~has]][None, :]
            pairs[k] = np.size(a > b)
            wins[k] = np.sum(a > b) + 0.5 * np.sum(a == b)
        used = pairs > 0
        if not used.any():
            rows.append({"feature": feat, "tests": 0, "pairs": 0, "win_rate": np.nan, "ci_lo": np.nan, "ci_hi": np.nan})
            continue
        w, p = wins[used], pairs[used]
        boot = rng.integers(0, used.sum(), size=(n_boot, used.sum()))
        rates = w[boot].sum(axis=1) / p[boot].sum(axis=1)
        rows.append({"feature": feat, "tests": int(used.sum()), "pairs": int(p.sum()), "win_rate": w.sum() / p.sum(),
                     "ci_lo": np.quantile(rates, 0.025), "ci_hi": np.quantile(rates, 0.975)})
    return pd.DataFrame(rows).set_index("feature")
