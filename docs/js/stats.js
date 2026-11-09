// Browser port of the abtest Python library, used by the interactive site.
// tests/test_js_parity.py checks these functions against the Python
// implementation, so the two cannot silently drift apart.

// ---------- distributions ----------
export function normCdf(x) {
  // Complementary error function, W. J. Cody-style rational approximation
  // (Numerical Recipes erfc, |rel. error| < 1.2e-7).
  const z = Math.abs(x) / Math.SQRT2;
  const t = 1 / (1 + 0.5 * z);
  const r = t * Math.exp(-z * z - 1.26551223 + t * (1.00002368 + t * (0.37409196 + t * (0.09678418 +
    t * (-0.18628806 + t * (0.27886807 + t * (-1.13520398 + t * (1.48851587 + t * (-0.82215223 + t * 0.17087277)))))))));
  return x >= 0 ? 1 - r / 2 : r / 2;
}

export function normSf(x) { return normCdf(-x); }

export function normPpf(p) {
  // Acklam's rational approximation plus one Newton refinement step.
  if (p <= 0) return -Infinity;
  if (p >= 1) return Infinity;
  const a = [-3.969683028665376e1, 2.209460984245205e2, -2.759285104469687e2, 1.38357751867269e2, -3.066479806614716e1, 2.506628277459239];
  const b = [-5.447609879822406e1, 1.615858368580409e2, -1.556989798598866e2, 6.680131188771972e1, -1.328068155288572e1];
  const c = [-7.784894002430293e-3, -3.223964580411365e-1, -2.400758277161838, -2.549732539343734, 4.374664141464968, 2.938163982698783];
  const d = [7.784695709041462e-3, 3.224671290700398e-1, 2.445134137142996, 3.754408661907416];
  const lo = 0.02425;
  let x;
  if (p < lo) {
    const q = Math.sqrt(-2 * Math.log(p));
    x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  } else if (p <= 1 - lo) {
    const q = p - 0.5, r = q * q;
    x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
  } else {
    const q = Math.sqrt(-2 * Math.log(1 - p));
    x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1);
  }
  const e = normCdf(x) - p;
  return x - e * Math.sqrt(2 * Math.PI) * Math.exp(x * x / 2);
}

function lnGamma(x) {
  const g = [76.18009172947146, -86.50532032941677, 24.01409824083091, -1.231739572450155, 0.1208650973866179e-2, -0.5395239384953e-5];
  let y = x, tmp = x + 5.5;
  tmp -= (x + 0.5) * Math.log(tmp);
  let ser = 1.000000000190015;
  for (const gj of g) ser += gj / ++y;
  return -tmp + Math.log(2.5066282746310005 * ser / x);
}

function gammaQ(a, x) {
  // Regularized upper incomplete gamma Q(a, x) (series / continued fraction).
  if (x <= 0) return 1;
  const gln = lnGamma(a);
  if (x < a + 1) {
    let sum = 1 / a, del = sum, ap = a;
    for (let n = 0; n < 500; n++) { ap += 1; del *= x / ap; sum += del; if (Math.abs(del) < Math.abs(sum) * 1e-14) break; }
    return 1 - sum * Math.exp(-x + a * Math.log(x) - gln);
  }
  let b = x + 1 - a, c = 1 / 1e-300, d = 1 / b, h = d;
  for (let i = 1; i < 500; i++) {
    const an = -i * (i - a); b += 2;
    d = an * d + b; if (Math.abs(d) < 1e-300) d = 1e-300;
    c = b + an / c; if (Math.abs(c) < 1e-300) c = 1e-300;
    d = 1 / d; const del = d * c; h *= del;
    if (Math.abs(del - 1) < 1e-14) break;
  }
  return Math.exp(-x + a * Math.log(x) - gln) * h;
}

export function chi2Sf(x, df) { return gammaQ(df / 2, x / 2); }

// ---------- frequentist ----------
export function wilson(clicks, n, alpha = 0.05) {
  const z = normPpf(1 - alpha / 2), p = clicks / n, z2 = z * z;
  const centre = (p + z2 / (2 * n)) / (1 + z2 / n);
  const half = (z / (1 + z2 / n)) * Math.sqrt(p * (1 - p) / n + z2 / (4 * n * n));
  return [Math.max(0, centre - half), Math.min(1, centre + half)];
}

export function zTest(ct, nt, cc, nc) {
  const pool = (ct + cc) / (nt + nc);
  const z = (ct / nt - cc / nc) / Math.sqrt(pool * (1 - pool) * (1 / nt + 1 / nc));
  return { z, p: 2 * normSf(Math.abs(z)) };
}

export function liftCI(ct, nt, cc, nc, alpha = 0.05, phi = 1) {
  const logRR = Math.log((ct / nt) / (cc / nc));
  const se = Math.sqrt(phi * (1 / ct - 1 / nt + 1 / cc - 1 / nc));
  const z = normPpf(1 - alpha / 2);
  return [Math.expm1(logRR), Math.expm1(logRR - z * se), Math.expm1(logRR + z * se)];
}

export function holm(pvals) {
  const m = pvals.length, order = pvals.map((p, i) => [p, i]).sort((a, b) => a[0] - b[0]);
  const adj = new Array(m);
  let running = 0;
  order.forEach(([p, i], k) => { running = Math.max(running, Math.min(1, (m - k) * p)); adj[i] = running; });
  return adj;
}

export function srmP(impressions) {
  const total = impressions.reduce((s, x) => s + x, 0), e = total / impressions.length;
  const chi2 = impressions.reduce((s, x) => s + (x - e) ** 2 / e, 0);
  return chi2Sf(chi2, impressions.length - 1);
}

export function omnibusP(clicks, impressions) {
  const C = clicks.reduce((s, x) => s + x, 0), N = impressions.reduce((s, x) => s + x, 0);
  let chi2 = 0;
  clicks.forEach((c, i) => {
    const n = impressions[i], ec = n * C / N, en = n * (N - C) / N;
    chi2 += (c - ec) ** 2 / ec + (n - c - en) ** 2 / en;
  });
  return chi2Sf(chi2, clicks.length - 1);
}

// ---------- power (two-sided, equal allocation; matches statsmodels NormalIndPower) ----------
export const cohenH = (p1, p0) => 2 * Math.asin(Math.sqrt(p1)) - 2 * Math.asin(Math.sqrt(p0));

export function powerAt(p0, lift, n, alpha = 0.05) {
  const h = Math.abs(cohenH(p0 * (1 + lift), p0)), crit = normPpf(1 - alpha / 2), s = h * Math.sqrt(n / 2);
  return normCdf(s - crit) + normCdf(-s - crit);
}

export function sampleSizePerArm(p0, lift, alpha = 0.05, power = 0.8) {
  let lo = 2, hi = 2;
  while (powerAt(p0, lift, hi, alpha) < power) hi *= 2;
  for (let i = 0; i < 200; i++) { const mid = (lo + hi) / 2; if (powerAt(p0, lift, mid, alpha) < power) lo = mid; else hi = mid; }
  return Math.ceil(hi - 1e-9);
}

export function mde(p0, n, alpha = 0.05, power = 0.8) {
  const crit = normPpf(1 - alpha / 2);
  const pw = h => normCdf(h * Math.sqrt(n / 2) - crit) + normCdf(-h * Math.sqrt(n / 2) - crit);
  let lo = 0, hi = 4;
  for (let i = 0; i < 200; i++) { const mid = (lo + hi) / 2; if (pw(mid) < power) lo = mid; else hi = mid; }
  const p1 = Math.sin(Math.asin(Math.sqrt(p0)) + hi / 2) ** 2;
  return p1 / p0 - 1;
}

// ---------- Bayesian (Monte Carlo from Beta posteriors) ----------
export function rng(seed = 1) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

function gauss(rand) { let u = 0; while (u === 0) u = rand(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rand()); }

function gamma(shape, rand) {
  if (shape < 1) return gamma(shape + 1, rand) * Math.pow(rand(), 1 / shape);
  const d = shape - 1 / 3, c = 1 / Math.sqrt(9 * d);
  for (;;) {
    let x, v;
    do { x = gauss(rand); v = 1 + c * x; } while (v <= 0);
    v = v * v * v; const u = rand();
    if (u < 1 - 0.0331 * x ** 4 || Math.log(u) < 0.5 * x * x + d * (1 - v + Math.log(v))) return d * v;
  }
}

export function posteriorSummary(clicks, impressions, { prior = [1, 1], phi = 1, draws = 20000, seed = 1 } = {}) {
  // phi-discounted counts: each impression carries 1/phi of a Bernoulli trial.
  const rand = rng(seed), k = clicks.length, wins = new Array(k).fill(0), loss = new Array(k).fill(0);
  const a = clicks.map(c => prior[0] + c / phi), b = clicks.map((c, i) => prior[1] + (impressions[i] - c) / phi);
  const theta = new Array(k);
  for (let s = 0; s < draws; s++) {
    let best = -1, bi = 0;
    for (let i = 0; i < k; i++) { const x = gamma(a[i], rand); theta[i] = x / (x + gamma(b[i], rand)); if (theta[i] > best) { best = theta[i]; bi = i; } }
    wins[bi]++;
    for (let i = 0; i < k; i++) loss[i] += best - theta[i];
  }
  return { pBest: wins.map(w => w / draws), expectedLoss: loss.map(l => l / draws) };
}

// ---------- readout: mirrors abtest.readout.analyze ----------
export function readout(arms, { alpha = 0.05, phi = 1, draws = 20000, seed = 1, lossThreshold = 1e-4 } = {}) {
  const clicks = arms.map(a => a.clicks), n = arms.map(a => a.n);
  const post = posteriorSummary(clicks, n, { phi, draws, seed });
  const [c0, n0] = [clicks[0], n[0]];
  const raw = arms.slice(1).map(a => 2 * normSf(Math.abs(zTest(a.clicks, a.n, c0, n0).z / Math.sqrt(phi))));
  const adj = holm(raw);
  const rows = arms.map((a, i) => {
    const [lo, hi] = wilson(a.clicks, a.n, alpha);
    const row = { ...a, control: i === 0, ctr: a.clicks / a.n, lo, hi, pBest: post.pBest[i], loss: post.expectedLoss[i] };
    if (i > 0) {
      const [lift, liftLo, liftHi] = liftCI(a.clicks, a.n, c0, n0, alpha, phi);
      Object.assign(row, { lift, liftLo, liftHi, p: raw[i - 1], pHolm: adj[i - 1] });
    }
    return row;
  });
  const challengers = rows.slice(1), best = challengers.reduce((m, r) => (r.ctr > m.ctr ? r : m), challengers[0]);
  const ship = best.pHolm < alpha && best.lift > 0 && best.pBest >= 0.95 && best.loss < lossThreshold;
  return { rows, best: best.label, ship, srmP: srmP(n), omnibusP: omnibusP(clicks, n) };
}

// ---------- peeking simulation (A/A) ----------
function binomial(n, p, rand) {
  if (n * p < 30) { let k = 0; for (let i = 0; i < n; i++) if (rand() < p) k++; return k; }
  return Math.max(0, Math.min(n, Math.round(n * p + Math.sqrt(n * p * (1 - p)) * gauss(rand))));
}

export function simulatePeeking({ p = 0.0104, perLook = 200, looks = 32, sims = 2000, alpha = 0.05, threshold = 0.95, seed = 7 } = {}) {
  const rand = rng(seed), hitZ = new Array(looks).fill(0), hitB = new Array(looks).fill(0);
  for (let s = 0; s < sims; s++) {
    let ca = 0, cb = 0, doneZ = false, doneB = false;
    for (let l = 0; l < looks; l++) {
      ca += binomial(perLook, p, rand); cb += binomial(perLook, p, rand);
      const n = perLook * (l + 1);
      if (!doneZ && ca + cb > 0 && zTest(cb, n, ca, n).p < alpha) doneZ = true;
      if (!doneB) {
        const ma = (1 + ca) / (n + 2), mb = (1 + cb) / (n + 2);
        const v = m => m * (1 - m) / (n + 3);
        const pb = normCdf((mb - ma) / Math.sqrt(v(ma) + v(mb)));
        if (pb > threshold || pb < 1 - threshold) doneB = true;
      }
      if (doneZ) hitZ[l]++;
      if (doneB) hitB[l]++;
    }
  }
  return { n: Array.from({ length: looks }, (_, l) => perLook * (l + 1)), z: hitZ.map(h => h / sims), bayes: hitB.map(h => h / sims) };
}
