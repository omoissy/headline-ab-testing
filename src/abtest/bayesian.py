"""Beta-Binomial inference for click-through rates.

With a Beta(a, b) prior and binomial clicks, each arm's posterior is
Beta(a + clicks, b + impressions - clicks). Decision quantities that have no
closed form (probability of being best, expected loss) are estimated by Monte
Carlo draws from those posteriors.
"""
from __future__ import annotations

import numpy as np
from scipy import stats


def posterior_params(clicks, impressions, prior=(1.0, 1.0)):
    clicks, impressions = np.asarray(clicks, float), np.asarray(impressions, float)
    return prior[0] + clicks, prior[1] + impressions - clicks


def sample_posteriors(clicks, impressions, prior=(1.0, 1.0), draws=200_000, seed=0):
    """Posterior CTR draws, shape (draws, n_arms)."""
    a, b = posterior_params(clicks, impressions, prior)
    rng = np.random.default_rng(seed)
    return rng.beta(a, b, size=(draws, len(a)))


def prob_best(samples):
    """P(arm has the highest true CTR) for each arm."""
    winners = samples.argmax(axis=1)
    return np.bincount(winners, minlength=samples.shape[1]) / samples.shape[0]


def prob_beats(samples, i, j):
    """P(CTR_i > CTR_j)."""
    return float((samples[:, i] > samples[:, j]).mean())


def expected_loss(samples):
    """Expected CTR given up by shipping each arm instead of the true best:
    E[max_k CTR_k - CTR_i]. Small loss means choosing it is a safe bet."""
    return (samples.max(axis=1, keepdims=True) - samples).mean(axis=0)


def relative_lift(samples, t, c):
    """Posterior draws of CTR_t / CTR_c - 1."""
    return samples[:, t] / samples[:, c] - 1


def credible_interval(draws, level=0.95):
    tail = (1 - level) / 2
    return tuple(np.quantile(draws, [tail, 1 - tail]))


def fit_beta_prior(ctrs, strength=None):
    """Method-of-moments Beta prior from historical CTRs.

    ``strength`` optionally caps a + b (the prior's worth in impressions) so a
    portfolio-wide prior informs, rather than dominates, a single test.
    """
    ctrs = np.asarray(ctrs, float)
    m, v = ctrs.mean(), ctrs.var(ddof=1)
    k = m * (1 - m) / v - 1
    if strength is not None:
        k = min(k, strength)
    return m * k, (1 - m) * k


def prob_beats_normal(c_t, n_t, c_c, n_c, prior=(1.0, 1.0)):
    """Fast normal approximation to P(CTR_t > CTR_c) for vectorised use
    (simulations, thousands of tests). Accurate once each arm has dozens of clicks."""
    a_t, b_t = posterior_params(c_t, n_t, prior)
    a_c, b_c = posterior_params(c_c, n_c, prior)
    m_t, m_c = a_t / (a_t + b_t), a_c / (a_c + b_c)
    v_t = a_t * b_t / ((a_t + b_t) ** 2 * (a_t + b_t + 1))
    v_c = a_c * b_c / ((a_c + b_c) ** 2 * (a_c + b_c + 1))
    return stats.norm.cdf((m_t - m_c) / np.sqrt(v_t + v_c))
