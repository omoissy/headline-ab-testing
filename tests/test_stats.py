import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportions_ztest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from abtest import bayesian as bayes  # noqa: E402
from abtest import frequentist as fq  # noqa: E402
from abtest import meta, power, simulate  # noqa: E402


def test_ztest_matches_statsmodels():
    z, p = fq.two_proportion_ztest(92, 7164, 41, 7165)
    z_ref, p_ref = proportions_ztest([92, 41], [7164, 7165])
    assert z == pytest.approx(z_ref)
    assert p == pytest.approx(p_ref)


def test_wilson_interval_contains_estimate_and_stays_positive():
    lo, hi = fq.wilson_ci(0, 500)
    assert lo == pytest.approx(0, abs=1e-12) and hi > 0
    lo, hi = fq.wilson_ci(41, 7165)
    assert lo < 41 / 7165 < hi


def test_relative_lift_ci_brackets_point_estimate():
    lift, lo, hi = fq.relative_lift_ci(92, 7164, 41, 7165)
    assert lift == pytest.approx((92 / 7164) / (41 / 7165) - 1)
    assert lo < lift < hi


def test_srm_detects_imbalance():
    assert fq.srm_test([5000, 5000, 5000])[1] == pytest.approx(1.0)
    assert fq.srm_test([5000, 5000, 4500])[1] < 0.001


def test_compare_to_control_corrections_are_ordered():
    arms = pd.DataFrame({"label": list("ABCDE"), "clicks": [41, 92, 38, 24, 23],
                         "impressions": [7165, 7164, 7068, 7146, 7217]})
    arms["ctr"] = arms.clicks / arms.impressions
    arms["is_control"] = arms.label == "A"
    out = fq.compare_to_control(arms)
    assert len(out) == 4
    assert (out.p_bonferroni >= out.p_holm - 1e-12).all()
    assert (out.p_holm >= out.p_raw - 1e-12).all()


def test_power_functions_are_mutually_consistent():
    n = power.sample_size_per_arm(0.01, 0.2)
    assert power.power_at(0.01, 0.2, n) == pytest.approx(0.8, abs=0.005)
    assert power.mde(0.01, n) == pytest.approx(0.2, rel=0.02)
    # Stricter alpha needs more traffic.
    assert power.sample_size_per_arm(0.01, 0.2, alpha=0.0125) > n


def test_prob_best_and_expected_loss():
    draws = bayes.sample_posteriors([50, 50], [5000, 5000], draws=100_000, seed=1)
    pb = bayes.prob_best(draws)
    assert pb.sum() == pytest.approx(1)
    assert pb[0] == pytest.approx(0.5, abs=0.01)
    draws = bayes.sample_posteriors([40, 90], [5000, 5000], draws=100_000, seed=1)
    assert bayes.prob_best(draws)[1] > 0.99
    loss = bayes.expected_loss(draws)
    assert loss[1] < loss[0]


def test_normal_approximation_close_to_monte_carlo():
    draws = bayes.sample_posteriors([60, 75], [6000, 6000], draws=400_000, seed=3)
    mc = bayes.prob_beats(draws, 1, 0)
    approx = bayes.prob_beats_normal(75, 6000, 60, 6000)
    assert approx == pytest.approx(mc, abs=0.01)


def test_dersimonian_laird_recovers_heterogeneity():
    rng = np.random.default_rng(0)
    true = rng.normal(0.1, 0.3, 5000)
    se = np.full(5000, 0.2)
    y = true + rng.normal(0, se)
    mu, tau2 = meta.dersimonian_laird(y, se)
    assert mu == pytest.approx(0.1, abs=0.02)
    assert np.sqrt(tau2) == pytest.approx(0.3, abs=0.02)
    assert meta.dersimonian_laird(rng.normal(0, se), se)[1] < 0.005


def test_shrinkage_pulls_noisy_estimates_harder():
    post, _ = meta.shrink(np.array([1.0, 1.0]), np.array([0.1, 1.0]), 0.0, 0.25)
    assert 0 < post[1] < post[0] < 1


@pytest.mark.parametrize("method", ["bonferroni", "holm", "fdr_bh"])
def test_vectorised_rejections_match_statsmodels(method):
    rng = np.random.default_rng(5)
    pv = rng.uniform(0, 0.1, size=(200, 5))
    ours = simulate.rejections(pv, method)
    ref = np.array([multipletests(r, alpha=0.05, method=method)[0] for r in pv])
    assert (ours == ref).all()
