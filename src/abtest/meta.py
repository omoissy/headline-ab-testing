"""Meta-analysis across many experiments: how big are true headline effects,
and how much should any single observed lift be trusted?"""
from __future__ import annotations

import numpy as np


def log_odds_ratio(c_t, n_t, c_c, n_c):
    """Log odds ratio of treatment vs control and its standard error.
    A 0.5 continuity correction is applied only where a cell is zero."""
    c_t, n_t, c_c, n_c = np.broadcast_arrays(*(np.asarray(x, float) for x in (c_t, n_t, c_c, n_c)))
    cells = np.stack([c_t, n_t - c_t, c_c, n_c - c_c])
    cells = np.where((cells == 0).any(axis=0), cells + 0.5, cells)
    a, b, c, d = cells
    return np.log(a * d / (b * c)), np.sqrt(1 / a + 1 / b + 1 / c + 1 / d)


def dersimonian_laird(y, se):
    """Random-effects pooling. Returns (mu, tau2): the mean true effect and the
    variance of true effects across experiments, net of sampling noise."""
    y, v = np.asarray(y, float), np.asarray(se, float) ** 2
    w = 1 / v
    mu_fe = np.sum(w * y) / np.sum(w)
    q = np.sum(w * (y - mu_fe) ** 2)
    c = np.sum(w) - np.sum(w ** 2) / np.sum(w)
    tau2 = max(0.0, (q - (len(y) - 1)) / c)
    w_re = 1 / (v + tau2)
    return float(np.sum(w_re * y) / np.sum(w_re)), float(tau2)


def shrink(y, se, mu, tau2):
    """Empirical-Bayes (normal-normal) posterior mean and sd for each effect.
    Noisy estimates are pulled hardest toward the portfolio mean."""
    y, v = np.asarray(y, float), np.asarray(se, float) ** 2
    weight = tau2 / (tau2 + v)
    return mu + weight * (y - mu), np.sqrt(weight * v)
