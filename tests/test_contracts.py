"""Data-contract and CLI tests on tiny synthetic fixtures (no download needed)."""
import pandas as pd
import pytest

from abtest import cli, data
from abtest.readout import analyze


def packages(rows):
    df = pd.DataFrame(rows, columns=["test_id", "created_at", "headline", "eyecatcher_id", "impressions", "clicks"])
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["first_place"] = False
    df["test_week"] = 1
    df["ctr"] = df["clicks"] / df["impressions"]
    df["problem"] = df["created_at"].between(data.PROBLEM_START, data.PROBLEM_END, inclusive="left")
    return df


FIXTURE = packages([
    # headline test: control is the EARLIEST headline even though it is listed last
    ("t1", "2014-05-01 10:05", "Second draft", "img1", 1000, 20),
    ("t1", "2014-05-01 10:00", "First draft", "img1", 1000, 10),
    ("t1", "2014-05-01 10:07", "Second draft", "img1", 500, 5),   # same stimulus -> pooled
    # image-only test
    ("t2", "2014-05-02 09:00", "Same", "img1", 900, 9),
    ("t2", "2014-05-02 09:01", "Same", "img2", 900, 12),
    # same-stimulus (near A/A) test
    ("t3", "2014-05-03 09:00", "Same", "img1", 800, 8),
    ("t3", "2014-05-03 09:01", "Same", "img1", 800, 9),
    # headline test inside the randomization-problem window -> excluded
    ("t4", "2013-08-01 09:00", "X", "img1", 700, 7),
    ("t4", "2013-08-01 09:01", "Y", "img1", 700, 8),
])


def test_classify_tests():
    assert data.classify_tests(FIXTURE).to_dict() == {"t1": "headline", "t2": "image", "t3": "same_stim",
                                                      "t4": "headline"}


def test_headline_arms_contract():
    arms = data.headline_arms(FIXTURE)
    assert set(arms["test_id"]) == {"t1"}                      # problem window excluded
    t1 = arms.set_index("headline")
    assert t1.loc["First draft", "is_control"]                 # earliest-created is control
    assert t1.loc["Second draft", "impressions"] == 1500       # identical stimuli pooled
    assert t1.loc["Second draft", "clicks"] == 25
    assert arms["is_control"].sum() == 1


def test_vs_control_joins_one_control_per_test():
    trt = data.vs_control(data.package_arms(FIXTURE, "same_stim"))
    assert len(trt) == 1 and trt["impressions_c"].iloc[0] == 800


def test_problem_window_boundaries():
    window = pd.to_datetime(["2013-06-24 23:59", "2013-06-25 00:00", "2014-01-10 23:59", "2014-01-11 00:00"])
    flags = window.to_series().between(data.PROBLEM_START, data.PROBLEM_END, inclusive="left").tolist()
    assert flags == [False, True, True, False]


def test_unknown_sample_rejected():
    with pytest.raises(ValueError):
        data.raw_path("holdout")


def test_readout_requires_one_control():
    arms = pd.DataFrame({"label": ["A", "B"], "clicks": [10, 12], "impressions": [1000, 1000]})
    arms["ctr"] = arms["clicks"] / arms["impressions"]
    arms["is_control"] = True
    with pytest.raises(ValueError):
        analyze(arms)


def test_phi_makes_evidence_weaker():
    arms = cli.parse_arms(["A=41/7165", "B=92/7164"])
    naive, calibrated = analyze(arms, draws=50_000), analyze(arms, phi=1.67, draws=50_000)
    assert calibrated["table"]["p_holm"].iloc[1] > naive["table"]["p_holm"].iloc[1]
    assert calibrated["table"]["lift_hi"].iloc[1] > naive["table"]["lift_hi"].iloc[1]


def test_cli_end_to_end(capsys):
    assert cli.main(["analyze", "A=41/7165", "B=92/7164", "C=38/7068"]) == 0
    out = capsys.readouterr().out
    assert "Decision: SHIP B" in out and "PASS" in out
    assert cli.main(["size", "--baseline", "0.0104", "--lift", "0.1", "--arms", "5"]) == 0
    assert "222,583 impressions per arm" in capsys.readouterr().out


@pytest.mark.parametrize("bad", [["A=5/10"], ["A=5/10", "B=11/10"], ["A=5/10", "A=6/10"], ["A=5/10", "B=x"]])
def test_cli_rejects_bad_arms(bad):
    with pytest.raises(SystemExit):
        cli.main(["analyze", *bad])
