"""Build the JSON that powers the interactive site in docs/.

Every per-test number comes from ``abtest.readout.analyze`` (the same code the
CLI uses) and the portfolio estimates written by notebook 02, so the site can
never disagree with the analysis. Run after the notebooks:

    python scripts/build_site_data.py
"""
import json
from pathlib import Path

import numpy as np

from abtest import data, meta, provenance
from abtest.readout import DECISION_RULE, analyze

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "reports" / "results"
OUT = ROOT / "docs" / "data"


def r(x, digits=5):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), digits)


def build_tests(portfolio: dict) -> list[dict]:
    phi, mu, tau2 = portfolio["phi"], portfolio["mu_hl"], portfolio["tau_net"] ** 2
    arms = data.headline_arms(data.load_packages("exploratory"))
    arms["label"] = arms["arm"].map(lambda i: chr(ord("A") + i))
    tests = []
    for tid, x in arms.groupby("test_id", sort=False):
        x = x.reset_index(drop=True)
        res = analyze(x, phi=phi, draws=20_000, seed=0)
        t = res["table"]
        ctl = x.loc[x["is_control"]].iloc[0]
        y, se = meta.log_odds_ratio(x["clicks"], x["impressions"], ctl["clicks"], ctl["impressions"])
        eb, _ = meta.shrink(y, se * np.sqrt(phi), mu, tau2)
        tests.append({
            "id": tid,
            "date": x["created_at"].min().strftime("%Y-%m-%d"),
            "ship": res["ship"],
            "best": res["best"],
            "srm_p": r(res["srm_p"]),
            "arms": [{
                "label": row["label"], "headline": row["headline"], "control": bool(row["is_control"]),
                "n": int(row["impressions"]), "clicks": int(row["clicks"]),
                "ctr": r(row["ctr"], 6), "lo": r(row["ctr_lo"], 6), "hi": r(row["ctr_hi"], 6),
                "lift": r(row["lift"], 4), "lift_lo": r(row["lift_lo"], 4), "lift_hi": r(row["lift_hi"], 4),
                "p_holm": r(row["p_holm"], 6), "p_best": r(row["p_best"], 4),
                "eb_lift": None if row["is_control"] else r(np.expm1(eb[i]), 4),
            } for i, row in t.iterrows()],
        })
    return tests


def main():
    portfolio = json.loads((RESULTS / "02_portfolio.json").read_text())
    sims = json.loads((RESULTS / "03_simulations.json").read_text())
    features = json.loads((RESULTS / "04_headline_features.json").read_text())
    case = json.loads((RESULTS / "01_case_study.json").read_text())

    tests = build_tests(portfolio)
    disc = {(d["p-values"], d["rule"]): d["challenger better"] for d in portfolio["discoveries"]}
    summary = {
        "decision_rule": DECISION_RULE,
        "phi": portfolio["phi"],
        "n_tests": len(tests),
        "n_ship": sum(t["ship"] for t in tests),
        "winners_naive": disc[("Naive", "No correction")],
        "winners_cal_holm": disc[("A/A-calibrated", "Holm (within test)")],
        "winners_obs_median": portfolio["winners_obs_median"],
        "winners_eb_median": portfolio["winners_eb_median"],
        "fp_aa": portfolio["fp_aa"],
        "srm_fail_inside": portfolio["srm_fail_inside"],
        "srm_fail_outside": portfolio["srm_fail_outside"],
        "median_mde": portfolio["median_mde"],
        "median_ctr_c": portfolio["median_ctr_c"],
        "median_n_arm": portfolio["median_n_arm"],
        "peek_fpr": sims["peek_fpr"],
        "case_lift": case["lift_median"],
        "features": [{k: f[k] for k in ("feature", "odds_ratio", "or_lo", "or_hi", "replicated", "preregistered")}
                     for f in features["confirm"]],
        "provenance": provenance.collect(samples=("exploratory",), seeds={"posterior_draws": 0}),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "tests.json").write_text(json.dumps(tests, separators=(",", ":"), ensure_ascii=False))
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=float))
    print(f"wrote {len(tests):,} tests ({(OUT / 'tests.json').stat().st_size / 1e6:.1f} MB); "
          f"{summary['n_ship']} ship under the rule")


if __name__ == "__main__":
    main()
