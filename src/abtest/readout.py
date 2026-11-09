"""One-call readout of a finished multi-arm test, shared by the CLI and the
website data build so every surface applies the same statistics and rule."""
from __future__ import annotations

import pandas as pd

from . import bayesian as bayes
from . import frequentist as fq

DECISION_RULE = ("ship the best challenger only if it beats control after Holm correction "
                 "AND P(best) >= 95% AND expected loss < 0.01 percentage points")


def analyze(arms: pd.DataFrame, alpha: float = 0.05, phi: float = 1.0, prior=(1.0, 1.0),
            draws: int = 200_000, seed: int = 0, loss_threshold: float = 1e-4) -> dict:
    """Frequentist + Bayesian readout and a ship/keep decision.

    ``arms`` needs label, clicks, impressions, ctr and is_control (exactly one
    control). ``phi`` is the A/A variance inflation: p-values and intervals are
    calibrated by it, and the posteriors use phi-discounted counts (each
    impression carries 1/phi of a binomial trial's information).
    """
    if arms["is_control"].sum() != 1:
        raise ValueError("arms must contain exactly one control row")
    lo, hi = fq.wilson_ci(arms["clicks"], arms["impressions"], alpha=alpha)
    samples = bayes.sample_posteriors(arms["clicks"] / phi, arms["impressions"] / phi,
                                      prior=prior, draws=draws, seed=seed)
    table = arms.assign(ctr_lo=lo, ctr_hi=hi, p_best=bayes.prob_best(samples),
                        expected_loss=bayes.expected_loss(samples))
    comp = fq.compare_to_control(arms, alpha=alpha, phi=phi).set_index("label")
    table = table.join(comp[["lift", "lift_lo", "lift_hi", "p_raw", "p_holm"]], on="label")
    _, srm_p = fq.srm_test(arms["impressions"])
    omni_p = fq.omnibus_chi2(arms["clicks"], arms["impressions"])[2] if arms["clicks"].sum() else float("nan")

    challengers = table[~table["is_control"]]
    best = challengers.loc[challengers["ctr"].idxmax()]
    ship = bool(best["p_holm"] < alpha and best["lift"] > 0 and best["p_best"] >= 0.95
                and best["expected_loss"] < loss_threshold)
    return {"table": table.reset_index(drop=True), "srm_p": srm_p, "omnibus_p": omni_p,
            "best": best["label"], "ship": ship}
