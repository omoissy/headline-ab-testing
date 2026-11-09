import numpy as np
import pandas as pd
import pytest

from abtest import features as F


def test_feature_extraction():
    h = pd.Series([
        "These 7 Kids Did What?",
        "I Can't Believe You Missed This!",
        "The Worst Day Ever, And Here's Why",
        "Imagine a quiet morning in the island",   # 'I' only inside words -> no first person
    ])
    X = F.headline_features(h)
    assert X["number"].tolist() == [1, 0, 0, 0]
    assert X["question"].tolist() == [1, 0, 0, 0]
    assert X["exclamation"].tolist() == [0, 1, 0, 0]
    assert X["you / your"].tolist() == [0, 1, 0, 0]
    assert X["I / me / my"].tolist() == [0, 1, 0, 0]
    assert X["this / these / here's"].tolist() == [1, 1, 1, 0]
    assert X["negative word"].tolist() == [0, 0, 1, 0]
    assert X[F.LENGTH].tolist() == pytest.approx([0.5, 0.6, 0.7, 0.7])


HEADLINES = ["Plain Headline Here Today", "Is This A Question Headline?",
             "Another Plain Headline Option", "What About This One?"]


def synthetic_tests(effect=-0.2231, n_tests=400, seed=0):
    """Tests where a question mark truly multiplies the odds of a click by exp(effect) (default 0.8)."""
    rng = np.random.default_rng(seed)
    rows = []
    for t in range(n_tests):
        base = rng.uniform(0.008, 0.02)
        for headline in HEADLINES:
            odds = base / (1 - base) * (np.exp(effect) if "?" in headline else 1.0)
            p = odds / (1 + odds)
            n = 20_000
            rows.append({"test_id": f"t{t}", "headline": headline, "impressions": n, "clicks": rng.binomial(n, p)})
    return pd.DataFrame(rows)


def test_within_test_fit_recovers_known_effect():
    arms = synthetic_tests()
    X = F.headline_features(arms["headline"])[["question"]]
    out, _ = F.within_test_fit(arms, X)
    assert out.loc["question", "odds_ratio"] == pytest.approx(0.8, abs=0.02)
    assert out.loc["question", "or_lo"] < 0.8 < out.loc["question", "or_hi"]


def test_pairwise_win_rates_direction_and_bounds():
    arms = synthetic_tests(effect=np.log(0.5), n_tests=200)
    wr = F.pairwise_win_rates(arms, n_boot=200)
    q = wr.loc["question"]
    assert q["tests"] == 200 and q["pairs"] == 200 * 4
    assert q["win_rate"] < 0.2                      # a halving of odds loses almost every matchup
    assert 0 <= q["ci_lo"] <= q["win_rate"] <= q["ci_hi"] <= 1
    assert wr.loc["number", "pairs"] == 0 and np.isnan(wr.loc["number", "win_rate"])   # no headline has a digit


def test_pairwise_win_rates_null_is_near_half():
    arms = synthetic_tests(effect=0.0, n_tests=400, seed=3)
    q = F.pairwise_win_rates(arms, n_boot=200).loc["question"]
    assert q["ci_lo"] < 0.5 < q["ci_hi"]
