"""Monte Carlo experiments on how A/B testing procedures behave."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from .bayesian import prob_beats_normal
from .frequentist import two_proportion_ztest
from .meta import log_odds_ratio


def peeking(p=0.015, n_max=6000, look_every=200, n_sims=20_000, alpha=0.05,
            bayes_threshold=0.95, seed=1):
    """A/A tests (no true difference) monitored after every ``look_every``
    impressions per arm. Returns the cumulative false-positive rate by look for:
    stop-at-first-p<alpha, stop-at-first-P(B>A)>threshold (either direction),
    and a Pocock-style constant boundary with alpha spread over all looks."""
    rng = np.random.default_rng(seed)
    looks = n_max // look_every
    n = look_every * np.arange(1, looks + 1)
    ca = rng.binomial(look_every, p, size=(n_sims, looks)).cumsum(axis=1)
    cb = rng.binomial(look_every, p, size=(n_sims, looks)).cumsum(axis=1)
    _, pval = two_proportion_ztest(cb, n, ca, n)
    pval = np.nan_to_num(pval, nan=1.0)
    pb = prob_beats_normal(cb, n, ca, n)
    pocock_alpha = _pocock_nominal(looks, alpha)
    rules = {
        "z-test, stop when p < 0.05": pval < alpha,
        "Bayesian, stop when P(B>A) > 95%": (pb > bayes_threshold) | (pb < 1 - bayes_threshold),
        "Pocock boundary (corrected)": pval < pocock_alpha,
    }
    out = pd.DataFrame({"look": np.arange(1, looks + 1), "n_per_arm": n})
    for name, hit in rules.items():
        out[name] = np.maximum.accumulate(hit, axis=1).mean(axis=0)
    return out, pocock_alpha


def _pocock_nominal(looks, alpha, n_sims=200_000, seed=7):
    """Nominal per-look alpha that keeps the overall type I error at ``alpha``
    under equally spaced looks (found by simulating the Brownian z-path)."""
    rng = np.random.default_rng(seed)
    z = rng.standard_normal((n_sims, looks)).cumsum(axis=1) / np.sqrt(np.arange(1, looks + 1))
    max_abs = np.abs(z).max(axis=1)
    crit = np.quantile(max_abs, 1 - alpha)
    return 2 * stats.norm.sf(crit)


def rejections(pv, method, alpha=0.05):
    """Vectorised multiple-testing decisions, one family per row of ``pv``."""
    pv = np.asarray(pv, float)
    m = pv.shape[1]
    if method == "none":
        return pv < alpha
    if method == "bonferroni":
        return pv < alpha / m
    order = np.argsort(pv, axis=1)
    sorted_p = np.take_along_axis(pv, order, axis=1)
    i = np.arange(1, m + 1)
    if method == "holm":
        rej_sorted = np.cumprod(sorted_p <= alpha / (m - i + 1), axis=1).astype(bool)
    elif method == "fdr_bh":
        ok = sorted_p <= i * alpha / m
        last = np.where(ok.any(axis=1), m - 1 - np.argmax(ok[:, ::-1], axis=1), -1)
        rej_sorted = i[None, :] - 1 <= last[:, None]
    else:
        raise ValueError(method)
    out = np.empty_like(rej_sorted)
    np.put_along_axis(out, order, rej_sorted, axis=1)
    return out


METHODS = {"none": "No correction", "bonferroni": "Bonferroni", "holm": "Holm",
           "fdr_bh": "Benjamini-Hochberg"}


def multiple_arms(k_values=range(2, 11), p=0.015, n=3000, true_lift=0.0, n_sims=20_000,
                  alpha=0.05, seed=2):
    """Simulate k-arm tests (arm 0 = control) where arm 1 has ``true_lift`` and
    every other treatment is identical to control.

    Returns, per k and method, the family-wise error rate (any null arm declared
    a winner) and the power to flag arm 1 when it truly differs."""
    rng = np.random.default_rng(seed)
    rows = []
    for k in k_values:
        probs = np.full(k, p)
        probs[1] = p * (1 + true_lift)
        clicks = rng.binomial(n, probs, size=(n_sims, k))
        _, pv = two_proportion_ztest(clicks[:, 1:], n, clicks[:, [0]], n)
        pv = np.nan_to_num(pv, nan=1.0)
        null_cols = slice(0, None) if true_lift == 0 else slice(1, None)
        for method, label in METHODS.items():
            rej = rejections(pv, method, alpha)
            rows.append({
                "arms": k, "method": label,
                "fwer": rej[:, null_cols].any(axis=1).mean() if k > 2 or true_lift == 0 else 0.0,
                "power": rej[:, 0].mean() if true_lift != 0 else np.nan,
            })
    return pd.DataFrame(rows)


def winners_curse(p0=0.015, n=3000, true_log_or=None, tau=0.15, n_sims=200_000, alpha=0.05, seed=3):
    """Simulate many two-arm tests whose true log-odds effects come from
    N(0, tau^2). Returns per-test truth, estimate and significance so type M
    (exaggeration) and type S (wrong sign) errors can be measured."""
    rng = np.random.default_rng(seed)
    if true_log_or is None:
        true_log_or = rng.normal(0, tau, n_sims)
    odds0 = p0 / (1 - p0)
    p1 = odds0 * np.exp(true_log_or) / (1 + odds0 * np.exp(true_log_or))
    cc = rng.binomial(n, p0, n_sims)
    ct = rng.binomial(n, p1)
    est, se = log_odds_ratio(ct, n, cc, n)
    _, pv = two_proportion_ztest(ct, n, cc, n)
    return pd.DataFrame({"true": true_log_or, "est": est, "se": se, "sig": np.nan_to_num(pv, nan=1) < alpha})
