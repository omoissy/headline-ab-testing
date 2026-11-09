"""Parity: the browser port (docs/js/stats.js) must agree with the Python library."""
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats
from statsmodels.stats.multitest import multipletests

from abtest import frequentist as fq
from abtest import power
from abtest.readout import analyze

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


@pytest.fixture(scope="module")
def js():
    out = subprocess.run(["node", str(ROOT / "tests" / "js_parity.mjs")], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def test_distributions(js):
    assert js["norm_ppf"] == pytest.approx(stats.norm.ppf([0.975, 0.001, 0.6]), abs=1e-7)
    assert js["norm_cdf"] == pytest.approx(stats.norm.cdf([1.96, -3.1, 0.2]), abs=2e-7)


def test_frequentist(js):
    assert js["wilson"] == pytest.approx(fq.wilson_ci(41, 7165), rel=1e-6)
    z, p = fq.two_proportion_ztest(92, 7164, 41, 7165)
    assert js["ztest"]["z"] == pytest.approx(z, rel=1e-9)
    assert js["ztest"]["p"] == pytest.approx(p, rel=1e-4)
    assert js["lift"] == pytest.approx(fq.relative_lift_ci(92, 7164, 41, 7165, phi=1.67), rel=1e-6)
    assert js["holm"] == pytest.approx(multipletests([0.01, 0.04, 0.03, 0.2], method="holm")[1])
    assert js["srm"] == pytest.approx(fq.srm_test([5000, 5000, 4800])[1], rel=1e-6)
    assert js["omnibus"] == pytest.approx(fq.omnibus_chi2([41, 92, 38, 24, 23], [7165, 7164, 7068, 7146, 7217])[2],
                                          rel=1e-4)


def test_power(js):
    assert js["n"] == power.sample_size_per_arm(0.0104, 0.1, alpha=0.0125)
    assert js["power"] == pytest.approx(power.power_at(0.0104, 0.38, 3200), abs=1e-6)
    assert js["mde"] == pytest.approx(power.mde(0.0104, 3200), rel=1e-5)


def test_readout_matches_python(js):
    arms = pd.DataFrame({"label": list("ABCDE"), "clicks": [41, 92, 38, 24, 23],
                         "impressions": [7165, 7164, 7068, 7146, 7217]})
    arms["ctr"] = arms["clicks"] / arms["impressions"]
    arms["is_control"] = arms.index == 0
    res = analyze(arms, phi=1.67, draws=200_000, seed=1)
    t = res["table"]
    assert js["readout"]["pHolm"] == pytest.approx(t["p_holm"].iloc[1:].to_numpy(), rel=1e-4)
    # Monte Carlo quantities: agree within simulation error.
    assert np.abs(np.array(js["readout"]["pBest"]) - t["p_best"].to_numpy()).max() < 0.01
    assert js["readout"]["ship"] == res["ship"] and js["readout"]["best"] == res["best"]
