import * as S from "./stats.js";

const $ = (id) => document.getElementById(id);
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const pct = (x, d = 2) => (x == null || !isFinite(x) ? "—" : `${(x * 100).toFixed(d)}%`);
const signed = (x, d = 0) => (x == null || !isFinite(x) ? "—" : `${x >= 0 ? "+" : ""}${(x * 100).toFixed(d)}%`);
const pval = (p) => (p == null || !isFinite(p) ? "—" : p < 1e-4 ? p.toExponential(1) : p.toFixed(4));
const num = (x) => Math.round(x).toLocaleString("en-US");
const prob = (x) => (x == null || !isFinite(x) ? "—" : x > 0.999 ? ">99.9%" : x < 0.001 ? "<0.1%" : `${(x * 100).toFixed(1)}%`);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const CASE_ID = "54345144b2454b5a9d000061";

let SUMMARY, TESTS = [], filtered = [];

// ---------- tooltip ----------
const tip = $("tooltip");
function showTip(evt, html) {
  tip.innerHTML = html; tip.style.display = "block";
  const pad = 14, w = tip.offsetWidth, h = tip.offsetHeight;
  let x = evt.clientX + pad, y = evt.clientY + pad;
  if (x + w > innerWidth - 8) x = evt.clientX - w - pad;
  if (y + h > innerHeight - 8) y = evt.clientY - h - pad;
  tip.style.left = `${x}px`; tip.style.top = `${y}px`;
}
const hideTip = () => (tip.style.display = "none");

// ---------- tiny SVG chart kit ----------
const NS = "http://www.w3.org/2000/svg";
function el(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}
function niceTicks(lo, hi, n = 5) {
  const span = hi - lo || 1, step0 = span / n, mag = 10 ** Math.floor(Math.log10(step0));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => span / s <= n) || mag * 10;
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-12; v += step) out.push(+v.toFixed(12));
  return out;
}
function hit(target, html) {
  target.addEventListener("mousemove", (e) => showTip(e, html));
  target.addEventListener("mouseleave", hideTip);
}

// Horizontal dot + interval chart. rows: {label, v, lo, hi, color, tip, hollow}
function dotChart(container, rows, { xFmt = (v) => v, xLabel = "", ref = null, labelWidth = 120, domain } = {}) {
  container.innerHTML = "";
  const W = Math.max(container.clientWidth, 320), rowH = 30, top = 8, bottom = 40;
  const H = top + rows.length * rowH + bottom, left = labelWidth, right = 16;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img" }, container);
  const vals = rows.flatMap((r) => [r.lo, r.hi, r.v]).filter((v) => v != null && isFinite(v));
  if (ref != null) vals.push(ref);
  let [lo, hi] = domain || [Math.min(...vals), Math.max(...vals)];
  const padv = (hi - lo) * 0.06 || 0.01; lo -= padv; hi += padv;
  const x = (v) => left + ((v - lo) / (hi - lo)) * (W - left - right);
  for (const t of niceTicks(lo, hi)) {
    el("line", { x1: x(t), x2: x(t), y1: top, y2: H - bottom, stroke: css("--grid"), "stroke-width": 1 }, svg);
    el("text", { x: x(t), y: H - bottom + 16, "text-anchor": "middle", fill: css("--ink-2"), "font-size": 11 }, svg).textContent = xFmt(t);
  }
  el("text", { x: left + (W - left - right) / 2, y: H - 6, "text-anchor": "middle", fill: css("--ink-2"), "font-size": 12 }, svg).textContent = xLabel;
  if (ref != null) el("line", { x1: x(ref), x2: x(ref), y1: top, y2: H - bottom, stroke: css("--ink-2"), "stroke-width": 1 }, svg);
  rows.forEach((r, i) => {
    const y = top + i * rowH + rowH / 2;
    el("text", { x: left - 10, y: y + 4, "text-anchor": "end", fill: css("--ink"), "font-size": 12 }, svg).textContent = r.label;
    if (r.v == null || !isFinite(r.v)) return;
    const g = el("g", {}, svg);
    if (isFinite(r.lo) && isFinite(r.hi))
      el("line", { x1: x(Math.max(r.lo, lo)), x2: x(Math.min(r.hi, hi)), y1: y, y2: y, stroke: r.color, "stroke-width": 2.5, "stroke-linecap": "round" }, g);
    el("circle", { cx: x(r.v), cy: y, r: 5.5, fill: r.hollow ? css("--surface") : r.color, stroke: r.hollow ? r.color : css("--surface"), "stroke-width": 2 }, g);
    el("rect", { x: left, y: y - rowH / 2, width: W - left - right, height: rowH, fill: "transparent" }, g);
    if (r.tip) hit(g, r.tip);
  });
}

// Line chart. series: {name, color, pts:[[x,y]]}; refs: [{y, label}]
function lineChart(container, series, { xLabel = "", yLabel = "", yFmt = (v) => v, xFmt = (v) => v, logY = false, refs = [], marker = null, yMin } = {}) {
  container.innerHTML = "";
  const W = Math.max(container.clientWidth, 320), H = 300, left = 64, right = 46, top = 12, bottom = 44;
  const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img" }, container);
  const xs = series.flatMap((s) => s.pts.map((p) => p[0])), ys = series.flatMap((s) => s.pts.map((p) => p[1])).concat(refs.map((r) => r.y));
  if (marker) ys.push(marker[1]);
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)];
  const tf = logY ? Math.log10 : (v) => v;
  let y0 = yMin ?? (logY ? Math.min(...ys) : 0), y1 = Math.max(...ys);
  if (logY) { y0 = 10 ** Math.floor(Math.log10(y0)); y1 = 10 ** Math.ceil(Math.log10(y1)); } else y1 *= 1.08;
  const X = (v) => left + ((v - x0) / (x1 - x0 || 1)) * (W - left - right);
  const Y = (v) => H - bottom - ((tf(v) - tf(y0)) / (tf(y1) - tf(y0) || 1)) * (H - top - bottom);
  const yt = logY ? Array.from({ length: Math.log10(y1 / y0) + 1 }, (_, i) => y0 * 10 ** i) : niceTicks(y0, y1);
  for (const t of yt) {
    el("line", { x1: left, x2: W - right, y1: Y(t), y2: Y(t), stroke: css("--grid") }, svg);
    el("text", { x: left - 8, y: Y(t) + 4, "text-anchor": "end", fill: css("--ink-2"), "font-size": 11 }, svg).textContent = yFmt(t);
  }
  for (const t of niceTicks(x0, x1, 6)) el("text", { x: X(t), y: H - bottom + 16, "text-anchor": "middle", fill: css("--ink-2"), "font-size": 11 }, svg).textContent = xFmt(t);
  el("line", { x1: left, x2: W - right, y1: H - bottom, y2: H - bottom, stroke: css("--axis") }, svg);
  el("text", { x: left + (W - left - right) / 2, y: H - 6, "text-anchor": "middle", fill: css("--ink-2"), "font-size": 12 }, svg).textContent = xLabel;
  el("text", { x: 14, y: top + (H - top - bottom) / 2, transform: `rotate(-90 14 ${top + (H - top - bottom) / 2})`, "text-anchor": "middle", fill: css("--ink-2"), "font-size": 12 }, svg).textContent = yLabel;
  for (const r of refs) {
    el("line", { x1: left, x2: W - right, y1: Y(r.y), y2: Y(r.y), stroke: css("--ink-2"), "stroke-width": 1 }, svg);
    el("text", { x: left + 6, y: Y(r.y) - 5, fill: css("--ink-2"), "font-size": 11 }, svg).textContent = r.label;
  }
  for (const s of series) {
    el("path", { d: s.pts.map((p, i) => `${i ? "L" : "M"}${X(p[0])},${Y(p[1])}`).join(""), fill: "none", stroke: s.color, "stroke-width": 2, "stroke-linejoin": "round" }, svg);
    const last = s.pts[s.pts.length - 1];
    el("text", { x: X(last[0]) + 6, y: Y(last[1]) + 4, fill: css("--ink"), "font-size": 11 }, svg).textContent = yFmt(last[1]);
  }
  if (marker) el("circle", { cx: X(marker[0]), cy: Y(marker[1]), r: 6, fill: css("--s1"), stroke: css("--surface"), "stroke-width": 2 }, svg);
  // crosshair + tooltip
  const cross = el("line", { y1: top, y2: H - bottom, stroke: css("--axis"), visibility: "hidden" }, svg);
  const overlay = el("rect", { x: left, y: top, width: W - left - right, height: H - top - bottom, fill: "transparent" }, svg);
  overlay.addEventListener("mousemove", (e) => {
    const box = svg.getBoundingClientRect(), vx = x0 + ((e.clientX - box.left) * (W / box.width) - left) / (W - left - right) * (x1 - x0);
    const pts = series.map((s) => s.pts.reduce((b, p) => (Math.abs(p[0] - vx) < Math.abs(b[0] - vx) ? p : b)));
    cross.setAttribute("x1", X(pts[0][0])); cross.setAttribute("x2", X(pts[0][0])); cross.setAttribute("visibility", "visible");
    showTip(e, `<b>${xLabel}: ${xFmt(pts[0][0])}</b><br>` + series.map((s, i) => `<span style="color:${s.color}">●</span> ${esc(s.name)}: ${yFmt(pts[i][1])}`).join("<br>"));
  });
  overlay.addEventListener("mouseleave", () => { cross.setAttribute("visibility", "hidden"); hideTip(); });
}

function legend(container, items) {
  container.innerHTML = items.map(([name, color]) => `<span><i style="background:${color}"></i>${esc(name)}</span>`).join("");
}

// ---------- shared readout renderer ----------
function renderReadout(out, rows, { ship, best, srmP, note }) {
  const bestRow = rows.find((r) => r.label === best);
  out.innerHTML = `
    <div class="verdict ${ship ? "ship" : "keep"}">${ship ? "✓ Ship " + esc(best) : "— Keep the control"}</div>
    <p class="meta">${ship ? `Headline ${esc(best)} beats the control after Holm correction, with P(best) ${prob(bestRow.pBest)}.`
      : `No challenger clears the bar: best challenger ${esc(best)} has Holm p = ${pval(bestRow.pHolm)} and P(best) = ${prob(bestRow.pBest)}.`}
      Sample-ratio check p = ${pval(srmP)} (${srmP >= 0.001 ? "pass" : "FAIL"}).</p>
    <div class="chart"></div>
    <div class="tablewrap"><table><thead><tr><th>Arm</th>${rows.some((r) => r.headline) ? '<th class="hl">Headline</th>' : ""}<th>Impressions</th><th>Clicks</th><th>CTR [95% CI]</th><th>Lift vs control [95% CI]</th><th>Holm p</th><th>P(best)</th>${rows.some((r) => r.eb != null) ? "<th>Shrunk lift</th>" : ""}</tr></thead><tbody>
    ${rows.map((r) => `<tr class="${r.control ? "ctl" : ""}"><td>${esc(r.label)}${r.control ? " (control)" : ""}</td>${r.headline ? `<td class="hl">${esc(r.headline)}</td>` : ""}
      <td>${num(r.n)}</td><td>${num(r.clicks)}</td><td>${pct(r.ctr)} [${pct(r.lo)}, ${pct(r.hi)}]</td>
      <td>${r.control ? "—" : `${signed(r.lift)} [${signed(r.liftLo)}, ${signed(r.liftHi)}]`}</td><td>${r.control ? "—" : pval(r.pHolm)}</td><td>${prob(r.pBest)}</td>
      ${rows.some((x) => x.eb != null) ? `<td>${r.eb == null ? "—" : signed(r.eb)}</td>` : ""}</tr>`).join("")}
    </tbody></table></div>
    <p class="note">${note}</p>`;
  const chart = out.querySelector(".chart");
  dotChart(chart, rows.map((r) => ({
    label: `${r.label}${r.control ? " (control)" : ""}`, v: r.ctr, lo: r.lo, hi: r.hi,
    color: r.control ? css("--ink-2") : r.label === best ? css("--s1") : css("--context"),
    tip: `<b>${esc(r.label)}${r.control ? " (control)" : ""}</b>${r.headline ? `<br>${esc(r.headline)}` : ""}<br>CTR ${pct(r.ctr)} [${pct(r.lo)}, ${pct(r.hi)}]<br>${num(r.clicks)} clicks / ${num(r.n)} impressions${r.control ? "" : `<br>Lift ${signed(r.lift)} · Holm p ${pval(r.pHolm)}`}<br>P(best) ${prob(r.pBest)}`,
  })), { xFmt: (v) => `${(v * 100).toFixed(2)}%`, xLabel: "Click-through rate with 95% Wilson interval", ref: rows[0].ctr, labelWidth: 96, domain: [0, Math.max(...rows.map((r) => r.hi))] });
}

// ---------- explorer ----------
function testLabel(t) {
  const ctl = t.arms[0].headline;
  return `${t.date} · ${t.arms.length} headlines · ${t.ship ? "ships " + t.best : "keep control"} · ${ctl.length > 70 ? ctl.slice(0, 70) + "…" : ctl}`;
}
function applyFilter(keepId) {
  const q = $("q").value.trim().toLowerCase(), shipOnly = $("shipOnly").checked;
  filtered = TESTS.filter((t) => (!shipOnly || t.ship) && (!q || t.arms.some((a) => a.headline.toLowerCase().includes(q))));
  $("matchCount").textContent = filtered.length.toLocaleString();
  const sel = $("testSelect"), shown = filtered.slice(0, 400), keep = filtered.find((t) => t.id === keepId);
  if (keep && !shown.includes(keep)) shown.unshift(keep);
  sel.innerHTML = shown.map((t) => `<option value="${t.id}">${esc(testLabel(t))}</option>`).join("");
  if (keep) sel.value = keep.id;
  showTest(sel.value);
}
function showTest(id) {
  const t = TESTS.find((x) => x.id === id), out = $("explorerOut");
  if (!t) { out.innerHTML = '<p class="meta">No tests match this search.</p>'; return; }
  const rows = t.arms.map((a) => ({ label: a.label, headline: a.headline, control: a.control, n: a.n, clicks: a.clicks, ctr: a.ctr, lo: a.lo, hi: a.hi,
    lift: a.lift, liftLo: a.lift_lo, liftHi: a.lift_hi, pHolm: a.p_holm, pBest: a.p_best, eb: a.eb_lift }));
  renderReadout(out, rows, { ship: t.ship, best: t.best, srmP: t.srm_p,
    note: `Test ${t.id.slice(0, 8)}… started ${t.date}. Lift intervals, Holm p-values and P(best) are A/A-calibrated (φ = ${SUMMARY.phi.toFixed(2)}). "Shrunk lift" is the empirical-Bayes estimate after accounting for the winner's curse.` });
}

// ---------- analyzer ----------
const DEFAULT_ARMS = [["A", 41, 7165], ["B", 92, 7164], ["C", 38, 7068], ["D", 24, 7146], ["E", 23, 7217]];
function armRow([label, clicks, n]) {
  const div = document.createElement("div");
  div.className = "armrow";
  div.innerHTML = `<label class="f">Arm<input type="text" value="${esc(label)}" maxlength="12"></label>
    <label class="f">Clicks<input type="number" min="0" value="${clicks}"></label>
    <label class="f">Impressions<input type="number" min="1" value="${n}"></label>
    <button class="btn" aria-label="Remove arm">Remove</button>`;
  div.querySelector("button").onclick = () => { if ($("armRows").children.length > 2) div.remove(); };
  return div;
}
function runAnalyze() {
  const out = $("analyzeOut");
  const arms = [...$("armRows").children].map((d) => {
    const [l, c, n] = d.querySelectorAll("input");
    return { label: l.value.trim() || "?", clicks: Math.round(+c.value), n: Math.round(+n.value) };
  });
  const bad = arms.find((a) => !(a.n > 0) || a.clicks < 0 || a.clicks > a.n || !Number.isFinite(a.clicks));
  if (bad) { out.innerHTML = `<p class="meta">Check arm ${esc(bad.label)}: clicks must be between 0 and impressions.</p>`; return; }
  if (new Set(arms.map((a) => a.label)).size !== arms.length) { out.innerHTML = '<p class="meta">Arm labels must be unique.</p>'; return; }
  if (arms.some((a) => a.clicks === 0)) { out.innerHTML = '<p class="meta">Every arm needs at least one click for lift intervals.</p>'; return; }
  const phi = $("phi").value === "cal" ? SUMMARY.phi : 1;
  const res = S.readout(arms, { phi, draws: 20000, seed: 1 });
  renderReadout(out, res.rows, { ship: res.ship, best: res.best, srmP: res.srmP,
    note: `Noise model: φ = ${phi.toFixed(2)}${phi > 1 ? ", the variance inflation measured from 2,418 near-A/A comparisons in the archive" : " (pure binomial)"}. Decision rule: ${SUMMARY.decision_rule}. Omnibus χ² p = ${pval(res.omnibusP)}.` });
}

// ---------- planner ----------
function runPlan() {
  const p0 = +$("pBase").value / 100, lift = +$("pLift").value / 100, arms = Math.max(2, Math.round(+$("pArms").value));
  const pw = +$("pPower").value / 100, phi = $("pPhi").checked ? SUMMARY.phi : 1, alpha = 0.05 / (arms - 1);
  if (!(p0 > 0 && p0 < 1 && lift > 0 && pw > 0.5 && pw < 1)) { $("planResult").textContent = "Check the inputs."; return; }
  const n = Math.ceil(S.sampleSizePerArm(p0, lift, alpha, pw) * phi);
  $("planResult").textContent = `${num(n)} impressions per arm`;
  $("planMeta").innerHTML = `${num(n * arms)} in total across ${arms} arms · ${(n / SUMMARY.median_n_arm).toFixed(1)}× a typical Upworthy test (${num(SUMMARY.median_n_arm)} per arm).<br>Bonferroni α = ${alpha.toPrecision(3)} per comparison${phi > 1 ? `, A/A calibration φ = ${phi.toFixed(2)}` : ""}.`;
  const pts = [];
  for (let l = 0.05; l <= 1.0001; l += 0.025) pts.push([l * 100, Math.ceil(S.sampleSizePerArm(p0, l, alpha, pw) * phi)]);
  lineChart($("planChart"), [{ name: "Impressions per arm", color: css("--s1"), pts }],
    { xLabel: "Relative lift to detect (%)", yLabel: "Impressions per arm (log)", logY: true, xFmt: (v) => `${Math.round(v)}%`,
      yFmt: (v) => (v >= 1e6 ? `${+(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `${+(v / 1e3).toFixed(1)}k` : num(v)),
      refs: [{ y: SUMMARY.median_n_arm, label: "typical Upworthy test" }], marker: lift <= 1 ? [lift * 100, n] : null });
}

// ---------- peeking ----------
function runSim() {
  const btn = $("runSim"); btn.disabled = true; btn.textContent = "Running…";
  setTimeout(() => {
    const p = +$("sBase").value / 100, perLook = Math.round(+$("sPer").value), looks = Math.min(100, Math.round(+$("sLooks").value));
    const sims = Math.min(5000, Math.round(+$("sSims").value));
    const r = S.simulatePeeking({ p, perLook, looks, sims, seed: 7 });
    const series = [
      { name: "z-test, stop at first p < 0.05", color: css("--s1"), pts: r.n.map((n, i) => [n, r.z[i]]) },
      { name: "Bayesian, stop at first P(B>A) > 95%", color: css("--s2"), pts: r.n.map((n, i) => [n, r.bayes[i]]) },
    ];
    legend($("simLegend"), series.map((s) => [s.name, s.color]));
    lineChart($("simChart"), series, { xLabel: "Impressions per arm when you stop looking", yLabel: "A/A tests declared a winner",
      yFmt: (v) => `${Math.round(v * 100)}%`, xFmt: (v) => num(v), refs: [{ y: 0.05, label: "nominal 5%" }] });
    $("simNote").textContent = `${num(sims)} simulated A/A tests in your browser. With these settings: ${pct(r.z.at(-1), 0)} false winners for the z-test and ${pct(r.bayes.at(-1), 0)} for the Bayesian rule. The full-size study in notebook 03 (40,000 runs) found ${pct(SUMMARY.peek_fpr["z-test, stop when p < 0.05"], 0)} and ${pct(SUMMARY.peek_fpr["Bayesian, stop when P(B>A) > 95%"], 0)}; a planned Pocock boundary held it to ${pct(SUMMARY.peek_fpr["Pocock boundary (corrected)"], 0)}.`;
    btn.disabled = false; btn.textContent = "Run simulation";
  }, 20);
}

// ---------- features ----------
function renderFeatures() {
  const f = [...SUMMARY.features].sort((a, b) => b.odds_ratio - a.odds_ratio);
  dotChart($("featChart"), f.map((x) => ({
    label: x.feature, v: x.odds_ratio - 1, lo: x.or_lo - 1, hi: x.or_hi - 1, hollow: !x.preregistered,
    color: x.replicated ? css("--s1") : css("--context"),
    tip: `<b>${esc(x.feature)}</b><br>${signed(x.odds_ratio - 1, 1)} CTR within a test<br>95% CI ${signed(x.or_lo - 1, 1)} to ${signed(x.or_hi - 1, 1)}<br>${x.replicated ? "Pre-registered and replicated" : x.preregistered ? "Pre-registered, not replicated" : "Not pre-registered (hypothesis only)"}`,
  })), { xFmt: (v) => `${v > 0 ? "+" : ""}${Math.round(v * 100)}%`, xLabel: "Effect on CTR within a test (odds ratio − 1)", ref: 0, labelWidth: 170 });
}

// ---------- boot ----------
function renderKpis() {
  const k = [
    [num(SUMMARY.n_tests), "real headline experiments analyzed"],
    [`${num(SUMMARY.winners_naive)} → ${num(SUMMARY.winners_cal_holm)}`, "apparent winners after A/A calibration + Holm"],
    [`${signed(SUMMARY.winners_obs_median)} → ${signed(SUMMARY.winners_eb_median)}`, "median winning lift after winner's-curse shrinkage"],
    [`${pct(SUMMARY.peek_fpr["z-test, stop when p < 0.05"], 0)}`, "false winners when you peek at an A/A test"],
  ];
  $("kpis").innerHTML = k.map(([v, l]) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`).join("");
  const p = SUMMARY.provenance;
  $("footer").innerHTML = `Data: <a href="https://upworthy.natematias.com/">Upworthy Research Archive</a> (Matias et al., 2021, <em>Scientific Data</em>; CC BY 4.0), exploratory sample <code>sha256 ${p.inputs.exploratory.sha256.slice(0, 12)}…</code>.
    Built from commit <code>${(p.git_commit || "unknown").slice(0, 7)}</code> with Python ${p.python}, numpy ${p.packages.numpy}, statsmodels ${p.packages.statsmodels}.
    Code: <a href="https://github.com/omoissy/headline-ab-testing">github.com/omoissy/headline-ab-testing</a> (MIT).`;
}
function renderAll() {
  renderKpis(); showTest($("testSelect").value); renderFeatures(); runPlan();
  if ($("simChart").innerHTML) runSim();
  if ($("analyzeOut").innerHTML) runAnalyze();
}

async function boot() {
  try {
    [SUMMARY, TESTS] = await Promise.all([fetch("data/summary.json").then((r) => r.json()), fetch("data/tests.json").then((r) => r.json())]);
  } catch (e) {
    $("explorerOut").innerHTML = `<p class="meta">Could not load data (${esc(e.message)}). Serve the docs/ folder over HTTP, e.g. <code>python -m http.server -d docs</code>.</p>`;
    return;
  }
  const opt = $("phi").querySelector('option[value="cal"]');
  opt.textContent = `A/A-calibrated (φ = ${SUMMARY.phi.toFixed(2)})`;
  DEFAULT_ARMS.forEach((a) => $("armRows").appendChild(armRow(a)));
  $("addArm").onclick = () => { const k = $("armRows").children.length; if (k < 12) $("armRows").appendChild(armRow([String.fromCharCode(65 + k), 50, 5000])); };
  $("runAnalyze").onclick = runAnalyze;
  $("q").addEventListener("input", () => applyFilter($("testSelect").value));
  $("shipOnly").addEventListener("change", () => applyFilter($("testSelect").value));
  $("testSelect").addEventListener("change", (e) => showTest(e.target.value));
  $("random").onclick = () => { const t = filtered[Math.floor(Math.random() * filtered.length)]; if (t) applyFilter(t.id); };
  $("caseStudy").onclick = () => { $("q").value = ""; $("shipOnly").checked = false; applyFilter(CASE_ID); };
  for (const id of ["pBase", "pLift", "pArms", "pPower", "pPhi"]) $(id).addEventListener("input", runPlan);
  $("runSim").onclick = runSim;
  renderKpis();
  applyFilter(CASE_ID);
  renderFeatures(); runPlan(); runAnalyze(); runSim();
  let t;
  addEventListener("resize", () => { clearTimeout(t); t = setTimeout(renderAll, 150); });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", renderAll);
}
boot();
