// Evaluates docs/js/stats.js on fixed inputs; tests/test_js_parity.py compares with Python.
import * as S from "../docs/js/stats.js";

const arms = [
  { label: "A", clicks: 41, n: 7165 }, { label: "B", clicks: 92, n: 7164 }, { label: "C", clicks: 38, n: 7068 },
  { label: "D", clicks: 24, n: 7146 }, { label: "E", clicks: 23, n: 7217 },
];
const ro = S.readout(arms, { phi: 1.67, draws: 40000, seed: 3 });
console.log(JSON.stringify({
  norm_ppf: [S.normPpf(0.975), S.normPpf(0.001), S.normPpf(0.6)],
  norm_cdf: [S.normCdf(1.96), S.normCdf(-3.1), S.normCdf(0.2)],
  wilson: S.wilson(41, 7165),
  ztest: S.zTest(92, 7164, 41, 7165),
  lift: S.liftCI(92, 7164, 41, 7165, 0.05, 1.67),
  holm: S.holm([0.01, 0.04, 0.03, 0.2]),
  srm: S.srmP([5000, 5000, 4800]),
  omnibus: S.omnibusP([41, 92, 38, 24, 23], [7165, 7164, 7068, 7146, 7217]),
  n: S.sampleSizePerArm(0.0104, 0.1, 0.0125, 0.8),
  power: S.powerAt(0.0104, 0.38, 3200),
  mde: S.mde(0.0104, 3200),
  readout: { pHolm: ro.rows.slice(1).map(r => r.pHolm), pBest: ro.rows.map(r => r.pBest), ship: ro.ship, best: ro.best },
}));
