# Metrics, formulas and defaults

Every number in a run comes from `scripts/gapscan.py`. This page explains what the scripts compute so you can interpret the results; you never need to compute these by hand. Defaults live in `assets/defaults.json`, each with its source. Worked examples are the published test vectors that the unit tests check.

Contents
1. Search saturation (D04)
2. Statistical stopping for large pools (D08)
3. Theme saturation (D14)
4. Inter-rater reliability (D06, D14)
5. Demand signals (D11)
6. Gap map and proxy opportunity (D16)
7. Certainty of evidence (D22)
8. Scoring and sensitivity (D23)
9. Sizing (D24)
10. Reproducibility between runs

## 1. Search saturation (D04)
**Sampling unit:** one scout × one channel family in one round. **Incidence:** which units found each verified, included entity. Snowball-only finds are excluded.

Notation:
- T: number of sampling units
- Q_k: entities found by exactly k units
- S_obs: entities observed
- U = Σ k·Q_k
- A = (T−1)/T

**Chao2** (Chao & Colwell 2017):
- **Estimate.** If Q2 > 0: Ŝ = S_obs + A·Q1²/(2·Q2). If Q2 = 0: Ŝ = S_obs + A·Q1(Q1−1)/2. If Q1 = 0: Ŝ = S_obs.
- **Variance** (Q1, Q2 > 0): var = Q2·[¼A²r⁴ + A²r³ + ½A·r²], where r = Q1/Q2.
- **95% interval:** [S_obs + D/R, S_obs + D·R], where D = Ŝ − S_obs and R = exp(1.96·√ln(1 + var/D²)).
- **Worked example:** T=12, Q1=9, Q2=4, S_obs=27 → Ŝ = 36.28, SE 8.31, CI 29.06–68.77.

**Sample coverage** (Chao & Jost 2012):
- Ĉ = 1 − (Q1/U)·B, where B = (T−1)Q1/((T−1)Q1 + 2Q2). If Q2 = 0, B = (T−1)(Q1−1)/((T−1)(Q1−1)+2).
- Ĉ is the estimated chance that the next unit's find is already known. Worked example (U = 102): Ĉ = 0.918.

**Extra units needed:**
- **To reach coverage C\*:** t = ⌈ln((1−C\*)U/Q1)/ln B⌉ − 1. Example: C\* = 0.95 → 7.
- **To find a fraction g of Ŝ** (Chao et al. 2009): m_g = ln[1 − (T/(T−1))(2Q2/Q1²)(g·Ŝ − S_obs)] / ln[1 − 2Q2/((T−1)Q1 + 2Q2)]. Example: g = 0.9 → 12.1.
- Never extrapolate beyond 2T.

**Marginal yield:** new verified entities in the latest round ÷ entities known before it.

**Probe new-share:** the share of the holdout probe's verified finds that no earlier unit found.

**Verdict:**
- **SATURATED** requires all of:
  - Q1 = 0, or Ĉ ≥ 0.95 (`landscape.coverage_target`) and S_obs/Ŝ ≥ 0.90 (`landscape.completeness_target_theta`, the doctoral "~90%" rule)
  - yield ≤ 0.05 from round 2
  - T ≥ 6
  - at least 3 verified products
  - a probe run after the latest round with new-share ≤ 0.10
- **NEEDS_PROBE** when everything but the probe holds.
- **EXPAND** otherwise. It adds k units, where k is t clamped to at least one per scout and at most T.
- **STOP_UNSATURATED** once `landscape.max_rounds` (4) is reached.
- **Correlated scouts** are flagged when mean pairwise Jaccard is above 0.85 while S_obs is below 15.

All of these are **lower bounds**: correlated searches and hard-to-find products make coverage look higher than it is. Write "at least N products (95% CI a–b)".

**Two-source audit** (Webster & Kemp 2013; used in `compare`):
- Estimated items missed by both runs: X̂ = (A−AB+1)(B−AB+1)/AB, with SD √[(A−AB+1)(B−AB+1)(A+1)(B+1)/(AB²(AB−1))].
- Example: A=177, B=265, AB=171 → 3.9 ± 2.5.

## 2. Statistical stopping for large pools (D08)
For ranked candidate pools larger than 200 (Callaghan & Müller-Hansen 2020):
1. Screen in rank order and find R relevant items.
2. Draw n at random from the N unseen items; k of them are relevant.
3. Compute K_tar = ⌊(R+k)/τ − R + 1⌋ and p = P(X ≤ k), where X ~ Hypergeometric(N, K_tar, n).
4. **STOP** when p < 1 − confidence, with τ = 0.95 and confidence 0.95.

Never stop on "N irrelevant in a row". `gapscan.py stoptest` computes this.

## 3. Theme saturation (D14)
Records are the sampling units and the run's own codes are the "species". Standard X-, F- and T- codes are left out; accepted new-code proposals count. Themes are **saturated** when both hold:
- **Coverage Ĉ** over records × codes ≥ 0.95 (formula as in §1).
- **Guest, Namey & Chen 2020:** new themes in a run of 10 records ÷ themes in the base of the first 20 records ≤ 5%. The run slides one record at a time, and the result is reported as "k+r". The interview defaults are base 4 and run 2; desk posts are shorter, so this skill uses 20/10 and reports it as an adaptation.

## 4. Inter-rater reliability (D06, D14)
**Krippendorff's α, nominal:**
1. Build the coincidence matrix: o_ck = Σ_u (number of c–k pairs in unit u)/(m_u − 1).
2. n_c = Σ_k o_ck and n = Σ_c n_c.
3. α = [(n−1)·Σ_c o_cc − Σ_c n_c(n_c−1)] / [n(n−1) − Σ_c n_c(n_c−1)].

Published examples give .095, .692 and .743.

Codes are multi-label, so α is computed **per code** as a present/absent value across the double-coded records:
- **Accept:** ≥ .80.
- **Provisional:** .667–.80. Gaps built on these codes get a certainty downgrade.
- **Revise:** below .667.
- **Not assessable:** fewer than 5 positives in the whole ledger, which is too rare to back a gap card. A **constant** code, present on every record, has undefined α (no variation).
- **Eligible codes** (at least 5 of coder A's positives) must each be measured. The double-coded set is a 20% random core plus a stratified top-up that gives each eligible code 5 positives and 5 negatives. Until every eligible code is measured, the verdict is **insufficient**, and `next` asks for a top-up.

Cohen's κ = (p_o − p_e)/(1 − p_e) is reported alongside, with Landis–Koch bands: slight ≤ .20, fair ≤ .40, moderate ≤ .60, substantial ≤ .80, almost perfect above that.

## 5. Demand signals (D11)
**Proportion series:** monthly d (all documents) and r (documents mentioning the term), from `fetch hn-counts` or `se-counts`. Kleinberg (2002) two-state bursts:
- p0 = Σr/Σd, p1 = min(2·p0, ~1).
- Cost σ_i(t) = −ln[C(d,r)·p_i^r·(1−p_i)^(d−r)].
- Going up a state costs γ·ln(n) with γ = 1; going down is free. The Viterbi path gives the burst periods.
- Significance: a 200× shuffle of periods, with p = (1 + #{shuffled max weight ≥ observed})/(1 + 200). A burst is significant when p < 0.05.

**Absolute series** (Wikipedia pageviews): trend only, as the ratio of the last 12 months to the 12 before, and the slope of log(1+views).

## 6. Gap map and proxy opportunity (D16)
For each job or outcome code:
- **Demand D:** Σ over distinct authors of their highest strength weight among demand records (stance pain, wish, workaround, switch or wtp). Weights: S0 0.25, S1 0.5, S2 1.0, S3 1.5, S4 2.0.
- **Supply:** the number of included products whose `jobs_served` contains the code.
- **Satisfaction proxy:** S_p = 10 × praise ÷ (praise + pain), counted in distinct authors, over records about the incumbents serving the code. It is 0 and flagged `no_satisfaction_data` when no such records exist.
- **Importance proxy:** I_p = 10 × D ÷ max D.
- **Proxy opportunity:** Opp_p = I_p + max(I_p − S_p, 0). Use it to **rank only**. It is never compared to the survey thresholds 10, 12 or 15.
- **Cell type:**
  - absolute gap: supply ≤ 1 and ≥ 5 demand authors
  - synthesis gap: supply ≥ 5 and ≥ 20% of demand records coded X-FRAG or X-INTEG
- **Association strength:** AS_ij = c_ij/(c_i·c_j), where c_i = Σ_{j≠i} c_ij. Observed ÷ expected = 2m·AS_ij with m = ½Σc_i. Segment × pain pairs with c_ij ≥ 3 and a ratio above 1 are segment-specific pains. Worked example: c_ab = 3 with totals 4 and 4, m = 5 → AS = 0.1875, ratio 1.875.

## 7. Certainty of evidence (D22)
This is an operationalisation adapted from GRADE and GRADE-CERQual. Its thresholds are in `defaults.json → certainty`.

**Concerns:**
- **Risk of bias:** share of vendor, incentivized or affiliate sources; moderate above 0.15, serious above 0.30.
- **Inconsistency:** contra ÷ (support + contra); moderate above 0.15, serious above 0.30.
- **Indirectness:** share flagged `indirect`; moderate above 0.50, serious above 0.75.
- **Imprecision:** fewer than 5 distinct authors is serious and fewer than 10 is moderate. A Wilson interval on prevalence (pain-code records ÷ job-code records) wider than 0.30 is moderate.
- **Methodological limitations:** resting on provisional codes is moderate; on codes that failed reliability, serious.
- **Publication bias / coverage:** low landscape coverage or STOP_UNSATURATED is moderate; degraded independence is moderate; both together are serious.

**Pain certainty (CERQual-style):** 2 points per serious and 1 per moderate concern, across methodological limitations, coherence, adequacy and relevance:
- 0 points: High
- 1 point: Moderate
- 2–3 points: Low
- 4 or more: Very low

**Demand certainty (GRADE-style):** start at Low.
- Downgrade one level per serious concern, and one level per two moderate concerns.
- Upgrade one level for magnitude: S4 records from ≥3 authors in ≥2 domains.
- Upgrade one level for dose–response: X-SCALE coded for ≥3 authors.
- The cap is Moderate for desk-only evidence.

**Demand strength** stays "weak" until validation experiments raise it.

## 8. Scoring and sensitivity (D23)
**Gates come first.** Exclude a card when:
- the red team killed it
- regulatory load is above medium
- human-ops burden is above medium
- agent-buildability is below partial
- platform risk is above 2
- the source terms make it infeasible

**Anchored 0–3 scores** (full anchors in D23): pain, pay, size, competition, why_now, reach, right_to_win.

**Total** = 100 × Σ(weight × score)/3. Default weights: pain .22, pay .18, size .12, competition .14, why-now .10, reach .14, right-to-win .10.

**Sensitivity:** 2,000 weight vectors drawn from Dirichlet(50 × weights), re-ranked each time. p_top3 is the share of draws in which a gap ranks in the top 3; the median rank is reported too.

**Ties:** pain certainty, then demand certainty, then distinct authors.

## 9. Sizing (D24)
For each of low, base and high:
- **TAM** = accounts × ARPA per year
- **SAM** = TAM × reachable share
- **SOM** = SAM × conversion × win rate

Counts need a source. Conversion and win rate are assumptions that validation tests. Never compute a size as "x% of TAM". The size score compares base SOM with `protocol.ambition.min_arr_usd`:
- 0: below a quarter of it
- 1: below it
- 2: at least it
- 3: at least three times it

## 10. Reproducibility between runs
`compare RUN_A RUN_B` reports:
- entity Jaccard (target ≥ 0.7)
- the Webster–Kemp estimate of items missed by both runs
- top-5 gap matches, where gaps match when the Jaccard of their incumbents and evidence URLs is ≥ 0.3 (target: at least 3 of 5 match)
- rank-biased overlap with p = 0.9: RBO = (X_k/k)·p^k + ((1−p)/p)·Σ_{d≤k}(X_d/d)·p^d
