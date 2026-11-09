"""Frequentist tools for comparing click-through rates."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint

CORRECTIONS = {"bonferroni": "Bonferroni", "holm": "Holm", "fdr_bh": "Benjamini-Hochberg"}


def wilson_ci(clicks, n, alpha: float = 0.05):
    """Wilson score interval - well behaved for small CTRs, unlike Wald."""
    return proportion_confint(clicks, n, alpha=alpha, method="wilson")


def two_proportion_ztest(c_t, n_t, c_c, n_c):
    """Pooled two-sided z-test of H0: p_t == p_c. Returns (z, p)."""
    c_t, n_t, c_c, n_c = map(np.asarray, (c_t, n_t, c_c, n_c))
    p_pool = (c_t + c_c) / (n_t + n_c)
    se = np.sqrt(p_pool * (1 - p_pool) * (1 / n_t + 1 / n_c))
    with np.errstate(divide="ignore", invalid="ignore"):
        z = (c_t / n_t - c_c / n_c) / se
    return z, 2 * stats.norm.sf(np.abs(z))


def diff_ci(c_t, n_t, c_c, n_c, alpha: float = 0.05):
    """Absolute CTR difference (treatment - control) with an unpooled Wald CI."""
    p_t, p_c = c_t / n_t, c_c / n_c
    se = np.sqrt(p_t * (1 - p_t) / n_t + p_c * (1 - p_c) / n_c)
    z = stats.norm.ppf(1 - alpha / 2)
    d = p_t - p_c
    return d, d - z * se, d + z * se


def relative_lift_ci(c_t, n_t, c_c, n_c, alpha: float = 0.05):
    """Relative lift p_t/p_c - 1 with a delta-method CI on the log risk ratio."""
    log_rr = np.log((c_t / n_t) / (c_c / n_c))
    se = np.sqrt(1 / c_t - 1 / n_t + 1 / c_c - 1 / n_c)
    z = stats.norm.ppf(1 - alpha / 2)
    return np.expm1(log_rr), np.expm1(log_rr - z * se), np.expm1(log_rr + z * se)


def srm_test(impressions, expected_share=None):
    """Sample-ratio-mismatch check: chi-square goodness of fit of the observed
    traffic split against the intended split (equal by default)."""
    impressions = np.asarray(impressions)
    if expected_share is None:
        expected = None
    else:
        expected = np.asarray(expected_share) / np.sum(expected_share) * impressions.sum()
    res = stats.chisquare(impressions, expected)
    return res.statistic, res.pvalue


def omnibus_chi2(clicks, impressions):
    """k x 2 chi-square test of independence: do any arms differ at all?"""
    clicks, impressions = np.asarray(clicks), np.asarray(impressions)
    chi2, p, dof, _ = stats.chi2_contingency(np.vstack([clicks, impressions - clicks]))
    return chi2, dof, p


def adjust_pvalues(pvals, methods=tuple(CORRECTIONS), alpha: float = 0.05) -> pd.DataFrame:
    """Adjusted p-values for several multiple-comparison procedures."""
    out = {"p_raw": np.asarray(pvals)}
    for m in methods:
        out[f"p_{m}"] = multipletests(pvals, alpha=alpha, method=m)[1]
    return pd.DataFrame(out)


def compare_to_control(arms: pd.DataFrame, alpha: float = 0.05, label_col: str = "label") -> pd.DataFrame:
    """Every treatment vs the control row (``is_control``), with corrections."""
    ctl = arms.loc[arms["is_control"]].iloc[0]
    trt = arms.loc[~arms["is_control"]].copy()
    c_c, n_c = ctl["clicks"], ctl["impressions"]
    c_t, n_t = trt["clicks"].to_numpy(), trt["impressions"].to_numpy()
    trt["z"], trt["p_raw"] = two_proportion_ztest(c_t, n_t, c_c, n_c)
    trt["diff"], trt["diff_lo"], trt["diff_hi"] = diff_ci(c_t, n_t, c_c, n_c, alpha)
    trt["lift"], trt["lift_lo"], trt["lift_hi"] = relative_lift_ci(c_t, n_t, c_c, n_c, alpha)
    adj = adjust_pvalues(trt["p_raw"].to_numpy(), alpha=alpha)
    for m in CORRECTIONS:
        trt[f"p_{m}"] = adj[f"p_{m}"].to_numpy()
    cols = [label_col, "impressions", "clicks", "ctr", "diff", "diff_lo", "diff_hi",
            "lift", "lift_lo", "lift_hi", "z", "p_raw"] + [f"p_{m}" for m in CORRECTIONS]
    return trt[[c for c in cols if c in trt.columns]].reset_index(drop=True)
