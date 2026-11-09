"""Command-line interface.

    abtest analyze A=41/7165 B=92/7164 C=38/7068        # first arm is the control
    abtest size --baseline 0.0104 --lift 0.10 --arms 5
    abtest mde --baseline 0.0104 --n 3200
"""
from __future__ import annotations

import argparse
import re
import sys

import numpy as np
import pandas as pd

from . import power
from .readout import DECISION_RULE, analyze

ARM = re.compile(r"^(?P<label>[^=]+)=(?P<clicks>\d+)/(?P<n>\d+)$")


def parse_arms(specs: list[str]) -> pd.DataFrame:
    rows = []
    for spec in specs:
        m = ARM.match(spec.strip())
        if not m:
            raise argparse.ArgumentTypeError(f"bad arm {spec!r}: use LABEL=CLICKS/IMPRESSIONS, e.g. B=92/7164")
        clicks, n = int(m["clicks"]), int(m["n"])
        if n == 0 or clicks > n:
            raise argparse.ArgumentTypeError(f"bad arm {spec!r}: need 0 <= clicks <= impressions and impressions > 0")
        rows.append({"label": m["label"], "clicks": clicks, "impressions": n})
    if len(rows) < 2:
        raise argparse.ArgumentTypeError("need at least two arms (control first)")
    arms = pd.DataFrame(rows)
    if arms["label"].duplicated().any():
        raise argparse.ArgumentTypeError("arm labels must be unique")
    arms["ctr"] = arms["clicks"] / arms["impressions"]
    arms["is_control"] = arms.index == 0
    return arms


def _pct(x, digits=2):
    return "—" if pd.isna(x) else f"{x * 100:.{digits}f}%"


def _p(x):
    return "—" if pd.isna(x) else (f"{x:.2e}" if x < 1e-3 else f"{x:.3f}")


def format_report(res: dict, phi: float) -> str:
    t = res["table"]
    header = f"{'arm':<10}{'impr.':>9}{'clicks':>8}{'CTR':>8}{'95% CI':>18}{'lift vs ctl':>26}" \
             f"{'p':>10}{'p (Holm)':>10}{'P(best)':>9}{'exp. loss':>11}"
    lines = [header, "-" * len(header)]
    for _, r in t.iterrows():
        name = f"{r['label']}{' *' if r['is_control'] else ''}"
        lift = "control" if r["is_control"] else f"{r['lift']:+.1%} [{r['lift_lo']:+.0%}, {r['lift_hi']:+.0%}]"
        lines.append(f"{name:<10}{r['impressions']:>9,}{r['clicks']:>8,}{_pct(r['ctr']):>8}"
                     f"{_pct(r['ctr_lo']) + '–' + _pct(r['ctr_hi']):>18}{lift:>26}{_p(r['p_raw']):>10}"
                     f"{_p(r['p_holm']):>10}{r['p_best']:>9.3f}{r['expected_loss'] * 100:>10.4f}pp")
    srm = "PASS" if res["srm_p"] >= 0.001 else "FAIL - check randomization before trusting anything below"
    lines += [
        "",
        "* control. CIs, p-values and posteriors "
        + (f"calibrated with phi = {phi:g}." if phi != 1 else "assume binomial noise."),
        f"Sample-ratio check (equal split): p = {_p(res['srm_p'])} -> {srm}",
        f"Omnibus chi-square (any difference): p = {_p(res['omnibus_p'])}",
        f"Decision: {'SHIP ' + str(res['best']) if res['ship'] else 'KEEP CONTROL'} (rule: {DECISION_RULE})",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="abtest", description="Frequentist + Bayesian A/B test readouts.")
    sub = parser.add_subparsers(dest="command", required=True)

    a = sub.add_parser("analyze", help="read out a finished test; first arm is the control")
    a.add_argument("arms", nargs="+", metavar="LABEL=CLICKS/IMPRESSIONS")
    a.add_argument("--alpha", type=float, default=0.05)
    a.add_argument("--phi", type=float, default=1.0, help="A/A variance inflation (default 1 = binomial)")
    a.add_argument("--prior", default="1,1", help="Beta prior a,b for every arm (default 1,1)")
    a.add_argument("--seed", type=int, default=0)

    s = sub.add_parser("size", help="impressions per arm needed to detect a relative lift")
    s.add_argument("--baseline", type=float, required=True, help="control CTR, e.g. 0.0104")
    s.add_argument("--lift", type=float, required=True, help="relative lift, e.g. 0.10 for +10%%")
    s.add_argument("--arms", type=int, default=2, help="arms including control (Bonferroni over challengers)")
    s.add_argument("--alpha", type=float, default=0.05)
    s.add_argument("--power", type=float, default=0.8)
    s.add_argument("--phi", type=float, default=1.0)

    m = sub.add_parser("mde", help="minimum detectable relative lift for a given sample size")
    m.add_argument("--baseline", type=float, required=True)
    m.add_argument("--n", type=int, required=True, help="impressions per arm")
    m.add_argument("--alpha", type=float, default=0.05)
    m.add_argument("--power", type=float, default=0.8)

    args = parser.parse_args(argv)
    if args.command == "analyze":
        try:
            arms = parse_arms(args.arms)
            prior = tuple(float(x) for x in args.prior.split(","))
        except (argparse.ArgumentTypeError, ValueError) as e:
            parser.error(str(e))
        print(format_report(analyze(arms, alpha=args.alpha, phi=args.phi, prior=prior, seed=args.seed), args.phi))
    elif args.command == "size":
        alpha = args.alpha / max(args.arms - 1, 1)
        n = int(np.ceil(power.sample_size_per_arm(args.baseline, args.lift, alpha=alpha, power=args.power) * args.phi))
        print(f"{n:,} impressions per arm ({n * args.arms:,} total across {args.arms} arms) to detect "
              f"{args.lift:+.0%} on a {args.baseline:.2%} baseline with {args.power:.0%} power, "
              f"alpha {alpha:.4g} per comparison" + (f", phi {args.phi:g}" if args.phi != 1 else ""))
    else:
        print(f"Minimum detectable lift: {power.mde(args.baseline, args.n, alpha=args.alpha, power=args.power):+.1%} "
              f"({args.n:,} impressions per arm, {args.baseline:.2%} baseline, {args.power:.0%} power)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
