"""Power analysis for two-proportion tests, framed in relative lift."""
from __future__ import annotations

import numpy as np
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

_SOLVER = NormalIndPower()


def _h(p0, rel_lift):
    """Cohen's h for a move from p0 to p0 * (1 + rel_lift)."""
    return proportion_effectsize(p0 * (1 + rel_lift), p0)


def sample_size_per_arm(p0, rel_lift, alpha=0.05, power=0.8, alternative="two-sided"):
    """Impressions per arm needed to detect a relative lift."""
    n = _SOLVER.solve_power(effect_size=abs(_h(p0, rel_lift)), alpha=alpha, power=power,
                            ratio=1.0, alternative=alternative)
    return int(np.ceil(n))


def power_at(p0, rel_lift, n_per_arm, alpha=0.05, alternative="two-sided"):
    """Probability of detecting a true relative lift with n impressions per arm."""
    return _SOLVER.power(effect_size=abs(_h(p0, rel_lift)), nobs1=n_per_arm, alpha=alpha,
                         ratio=1.0, alternative=alternative)


def mde(p0, n_per_arm, alpha=0.05, power=0.8, alternative="two-sided"):
    """Minimum detectable *relative* lift (upward) for a given sample size."""
    h = _SOLVER.solve_power(nobs1=n_per_arm, alpha=alpha, power=power, ratio=1.0,
                            alternative=alternative)
    p1 = np.sin(np.arcsin(np.sqrt(p0)) + h / 2) ** 2
    return p1 / p0 - 1
