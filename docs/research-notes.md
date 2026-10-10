# Research notes (provenance record)

This file records what was checked during the 2026-10-09 research pass behind the market-gap skills: formulas, worked examples, defaults, caveats and sources. There were three research tracks, plus a portability check made while planning. The scripts implement these formulas, and the unit tests use the worked examples below as test vectors.

Tags used throughout:
- **[V]** — checked against the primary text during the session.
- **[2°]** — secondary source only.
- **[U]** or **UNVERIFIED** — not confirmed.
- **(derived)** — an agent's own derivation from verified formulas.

Every worked example in §5 was also recomputed by hand during the session.

Contents
1. Scope of the research pass
2. Track A: research-method statistics
3. Track B: market and product methods
4. Track C: data sources, terms of service, prior art, skill authoring
5. Unit-test vectors
6. Design decisions derived from the research
7. Disclosure: User-Agent incident and the MGD_CONTACT rule

## 1. Scope of the research pass
- **Track A** checked the statistics that make the method systematic: stopping rules, estimators, reliability, certainty grading, gap frameworks, reporting standards.
- **Track B** checked the product and market frameworks and their math: ODI, JTBD, Kano, Van Westendorp, PMF, interviews, Testing Business Ideas, OST, Blue Ocean, sizing, smoke tests, RICE/ICE.
- **Track C** checked what data agents may legally and practically use in 2026, which prior tools exist, and how to author portable Agent Skills.
- **Portability check** (from the planning review): Claude Code, OpenCode and Codex CLI all load the Agent Skills `SKILL.md` format, from different folders; see §4.7.

## 2. Track A: research-method statistics

### 2.1 Capture–recapture as a stopping rule
- **Kastner et al. 2009** [A1][V, abstract only]: capture–mark–recapture across 4 databases. The "Horizon Estimate" predicted 1,838 relevant records at title/abstract (the databases held 68% of them) and 49 at full text (81%). Which estimator they used is **UNVERIFIED**.
- **Two complete sources** (Webster & Kemp 2013, eqs 23–24) [A2][V]: missed items X̂ = (A−AB+1)(B−AB+1)/AB for AB > 0; variance σ² = (A−AB+1)(B−AB+1)(A+1)(B+1) / (AB²(AB−1)) for AB > 1. Chapman's estimator gives a lower number.
- **Assumptions:** sources are independent and every item is equally catchable. A hard-to-find subgroup or correlated sources make coverage look better than it is, so treat results as lower bounds [A2].
- **More than two sources:** use Chao2 (§2.2), with T = number of sources and Q_k = items found by exactly k sources. Log-linear models apply when sources look dependent [A3].
- **Bron et al. 2024** [A4][V]: the classifiers in an ensemble act as capture occasions. Stop when found ÷ (upper-CI N̂) ≥ target recall, after at least 100 labels.

### 2.2 Chao2 (Chao & Colwell 2017, eqs 2b, 3a–3c) [A5][V]
Let A = (T−1)/T.
- **Estimate:** Q2 > 0: Ŝ = S_obs + A·Q1²/(2·Q2); Q2 = 0: Ŝ = S_obs + A·Q1(Q1−1)/2. The "bias-corrected" form used by EstimateS and vegan is S_obs + A·Q1(Q1−1)/(2(Q2+1)) [A6][2°].
- **Variance:** Q1, Q2 > 0: var = Q2·[¼A²r⁴ + A²r³ + ½A·r²], with r = Q1/Q2; Q2 = 0: var = ¼A²Q1(2Q1−1)² + ½A·Q1(Q1−1) − ¼A²Q1⁴/Ŝ.
- **95% CI (log-normal):** [S_obs + D/R, S_obs + D·R], with D = Ŝ − S_obs and R = exp(1.96·√ln(1 + var/D²)).
- **Q1 = 0:** Ŝ = S_obs, and the variance comes from a bootstrap. EstimateS's analytic incidence formula for this case is **UNVERIFIED** (the EstimateS site was offline).
- **Caveat:** Chao2 is nearly unbiased only if the rarest items have similar detection odds; otherwise it is a lower bound.

### 2.3 Sample coverage and remaining effort [A5][V]
These restate Chao & Jost 2012 and Chao et al. 2009.
- **Coverage:** U = Σ k·Q_k; B = (T−1)Q1 / ((T−1)Q1 + 2Q2), or B = (T−1)(Q1−1) / ((T−1)(Q1−1) + 2) when Q2 = 0; Ĉ = 1 − (Q1/U)·B. 1 − Ĉ approximates the share of next-round sightings that will be new items.
- **Extra units to reach a target coverage C\*** (derived): Ĉ(T+t) = 1 − (Q1/U)·B^(t+1), which gives t = ⌈ln((1−C\*)·U/Q1) / ln B⌉ − 1.
- **Projected richness:** Ŝ(T+t) = S_obs + Q̂0·[1 − (1 − Q1/(T·Q̂0 + Q1))^t]. Never project beyond 2T.
- **Extra units to detect a fraction g of Ŝ:** m_g ≈ ln[1 − (T/(T−1))·(2Q2/Q1²)·(g·Ŝ − S_obs)] / ln[1 − 2Q2/((T−1)Q1 + 2Q2)].
- **Extra units to reach Ŝ itself:** t = T·x\*, where x\* solves 2Q1(1+x) = exp[x·2Q2 / ((1−1/T)Q1 + 2Q2/T)].
- **UNVERIFIED:** the Q2 = 0 versions of the effort formulas.

### 2.4 Statistical stopping for screening and search
- **Callaghan & Müller-Hansen 2020** [A7][V]:
  - Setup: after ranked screening has found ρ_AL relevant items, draw n items at random from the N unseen; k of them are relevant. Compute ρ_seen = ρ_AL + k and K_tar = ⌊ρ_seen/τ − ρ_AL + 1⌋.
  - p = P(X ≤ k), with X ~ Hypergeometric(N, K_tar, n). Stop when p < 1 − confidence.
  - Results: the test reached 95% recall in more than 95% of runs and saved 15–17% of screening. The "50 irrelevant in a row" rule and the baseline-sample rule missed the target in about 39% of runs.
- **Target method** [A8][V]: random-sample until 10 relevant items are found (the paper states this guarantees recall ≥ 0.7 at 95% confidence), then screen until all 10 have been re-found.
- **What transfers to markets:** use a statistical test to stop on ranked candidate lists, and never stop on "N irrelevant in a row".

### 2.5 Thematic saturation (Guest, Namey & Chen 2020) [A9][V]
- **Base size:** the first interviews. Their unique themes form the fixed denominator (default 4 interviews).
- **Run length:** how many following interviews are checked for new themes (2 or 3). Runs slide forward one interview at a time.
- **New information:** themes not seen in any earlier interview.
- **Computation:** new themes in the run ÷ themes in the base. Saturation is reached at ≤ 5% (a strict variant requires 0%).
- **Reporting:** k⁺ʳ, where k is the last interview before the run that met the threshold (for example 6⁺²).
- **Caveat:** validated only on individual interviews with flat codebooks, using random-order bootstraps. The desk-post defaults (base 20, run 10) are an adaptation and are labelled as one.

### 2.6 Inter-rater reliability
- **Cohen's κ:** κ = (p_o − p_e)/(1 − p_e), with p_e = Σ_c p_c(rater 1)·p_c(rater 2).
- **Multi-label codes** [A10][V]: build a unit × code 0/1 matrix for each coder and compute reliability per code. Report the spread of values; one pooled number hides weak codes.
- **Krippendorff's α, nominal** [A11][V]:
  - o_ck = Σ_u (number of c–k pairs in unit u)/(m_u − 1), dropping units with fewer than 2 values; n_c = Σ_k o_ck; n = Σ_c n_c.
  - α = [(n−1)·Σ o_cc − Σ n_c(n_c−1)] / [n(n−1) − Σ n_c(n_c−1)]. Binary case with two coders: α = 1 − (n−1)·o_01/(n_0·n_1).
- **Thresholds:** Krippendorff [A12][2°]: rely on α ≥ .800; .667–.800 supports tentative conclusions only. Landis & Koch [A10]: below 0 none, .00–.20 slight, .21–.40 fair, .41–.60 moderate, .61–.80 substantial, .81–1 almost perfect.
- **Practice** [A10][V]: double-code 10–25% of units, chosen at random or stratified, and fix the threshold in advance. Keep the codebook to roughly 20–40 codes. Rare codes depress κ and α, so require a minimum number of positives per code.

### 2.7 GRADE and GRADE-CERQual
- **GRADE** [A13][V]:
  - Randomized evidence starts High; observational evidence starts Low.
  - Downgrade 1–2 levels each for risk of bias, inconsistency, indirectness, imprecision and publication bias.
  - Upgrade for a large effect (RR > 2 or < 0.5: +1; RR > 5 or < 0.2: +2), for a dose–response gradient, or when plausible confounding would shrink the effect.
- **CERQual** [A14][2°]:
  - Start at High.
  - Rate methodological limitations, coherence, adequacy and relevance as no/very minor, minor, moderate or serious concerns.
  - A serious concern lowers confidence by at least one level.
- **Proposed market adaptation** (the agent's proposal, adopted in D22 and in `certainty.*` in `defaults.json`):

  | GRADE domain | Market reading |
  |---|---|
  | Risk of bias | Source credibility (vendor-written, incentivised, astroturfed) |
  | Inconsistency | Disagreement across platforms or segments |
  | Indirectness | A neighbouring persona, or stated rather than revealed behaviour |
  | Imprecision | Few independent authors, or a wide Wilson CI on prevalence |
  | Publication bias | Complaints more visible than satisfaction; low Ĉ |
  | Upgrade: magnitude | Paying for workarounds |
  | Upgrade: dose–response | Pain that rises with usage |

  CERQual is used for "this pain exists and looks like X". GRADE-style rating, starting Low, is used for prevalence and willingness-to-pay claims. The numeric cut-offs in `defaults.json → certainty` are design operationalisations, not published values.

### 2.8 Research-gap frameworks
- **Robinson et al. 2011** [A15][2°]: describe a gap with PICOS. Its reason is one of: insufficient or imprecise; biased; inconsistent or of unknown consistency; not the right information.
- **Miles 2017** (not peer-reviewed) [A16][2°]: evidence gap (findings contradict accepted conclusions); knowledge gap (the knowledge is absent); practical-knowledge conflict (practice differs from what is advocated); methodological gap; empirical gap (a claim was never tested); theoretical gap; population gap (a group is under-represented).
- **Müller-Bloch & Kranz 2015** [A17] (only the type names were confirmed): contradictory evidence, knowledge void, action-knowledge conflict, methodological conflict, evaluation void, theory application void.
- **Sandberg & Alvesson 2011** [A18][V]:
  - Confusion spotting: evidence exists but contradicts itself.
  - Neglect spotting: an overlooked or under-researched area, or one lacking empirical support.
  - Application spotting: an area lacking a particular theory or perspective.
  - The agent's tally of their 52 papers: 6 confusion, 33 neglect, 13 application.
- **Alvesson & Sandberg 2011, problematization** [A19][2°]:
  - Steps: identify the literature domain → articulate its assumptions → evaluate them → develop alternative assumptions → consider the audience → evaluate the alternatives.
  - Assumption types: in-house, root metaphor, paradigm, ideology, field.

### 2.9 Concept matrix and Evidence Gap Maps
- **Webster & Watson 2002:** articles × concepts, optionally split by unit of analysis [2°; the paper itself was not accessed].
- **Evidence Gap Maps** [A20][2°]:
  - The grid is interventions × outcomes. Bubble size = number of studies; colour = design or confidence.
  - Absolute gap: a cell with few or no primary studies.
  - Synthesis gap: many primary studies but no recent systematic review.
  - SaaS translation (adopted in D16): solution approaches × jobs/pains; products count as primary studies, and comparison or review content counts as synthesis.

### 2.10 Snowballing (Wohlin 2014) [A21][V]
- **Start set:** diverse in communities, publishers, years and authors, found with synonyms.
- **Each iteration**, run on the newly included items:
  - Backward: reference title, venue and authors → where and how it is cited → abstract → full text.
  - Forward: the citations of the item.
  - Include an item only after a full-text decision.
- **Stop** when an iteration adds nothing, then contact active authors.
- **Expected pattern:** yield per iteration should fall. The worked example went 3/13, 7/25, 1/223, 0/33. If yield does not fall, search again with synonyms.

### 2.11 PRISMA reporting
- **PRISMA 2020 flow** [A22][2°]:
  - Identification: records per database or register, minus duplicates, automation exclusions and other removals.
  - Screening: records screened and excluded; reports sought and not retrieved; reports assessed and excluded, with reasons.
  - Included.
  - A parallel column covers other search methods.
- **PRISMA-S, what to log for every search** [A23][V]: database and platform; multi-database platform; registries; websites and how they were browsed; citation searching; contacts; other methods; the strategy exactly as run; limits, with justification; filters; reused strategies; update method; date last run; peer review (PRESS); records per source; de-duplication method.
- **PRISMA-P** [A24][2°]: 17 items, including registration, eligibility, sources, search, data items, outcome prioritisation, risk of bias, synthesis, meta-bias and confidence.
- **PROSPERO** accepts only reviews with health outcomes (its field list is **UNVERIFIED**); OSF Registries is the alternative.

### 2.12 Lightweight bibliometrics
- **Association strength** [A25][V]:
  - AS_ij = c_ij/(c_i·c_j), with c_i = Σ_{j≠i} c_ij.
  - It is proportional to observed ÷ expected co-occurrence. Multiplying by 2m, with m = ½Σc_i, gives that ratio exactly (derived).
- **Kleinberg 2002, batched two-state model** [A26][V]:
  - Period t has d_t documents, of which r_t contain the term. p0 = Σr/Σd, and p1 = s·p0 with s = 2 (capped at p1 ≤ 1).
  - State cost σ_i(t) = −ln[C(d_t, r_t)·p_i^(r_t)·(1−p_i)^(d_t−r_t)]. Moving up a state costs γ·ln n (γ = 1); moving down is free.
  - Dynamic programme C_j(t) = σ_j(t) + min_l[C_l(t−1) + τ(l,j)], starting in state 0. Burst weight = Σ over the burst of [σ_0(t) − σ_1(t)].
  - Use s = 8–16 for long series, and validate by shuffling timestamps. Per-period χ² tests (Swan & Allan) split long bursts into fragments.
- **CiteSpace** [A27][2°]: runs Kleinberg bursts on terms (emerging concepts) and on references. Its default γ and minimum burst duration are **UNVERIFIED**.

### 2.13 Track A recommendations as adopted
1. **Landscape stopping:** each scout × channel family is one sampling unit. Compute Chao2 with its log CI, Ĉ, and m_g for g = 0.9. Stop when Ĉ ≥ 0.95 and S_obs/Ŝ ≥ 0.90, or when Q1 = 0. Never project past 2T, and report results as lower bounds. Defaults: `landscape.coverage_target`, `landscape.completeness_target_theta`, `landscape.extrapolation_limit_factor`.
2. **Run-versus-run audits:** Webster–Kemp, because Chapman runs low (`gapscan.py compare`).
3. **Large ranked pools:** the Callaghan test with τ = 0.95 at 95% confidence (`gapscan.py stoptest`; pools over `evidence.stoptest_pool_min` = 200).
4. **Pain themes:** treat records × codes as incidence data and require Ĉ ≥ 0.95. Report Guest–Namey–Chen alongside.
5. **Coding:** Krippendorff's α per code on at least 20% double-coded records. ≥ .80 accept; .667–.80 provisional.
6. **Gap labels and certainty:** label each gap with PICOS, its Robinson reason and its Sandberg–Alvesson mode; rate certainty with CERQual plus the adapted GRADE.
7. **Emerging terms:** Kleinberg with s = 2, γ = 1, plus a shuffle test; association strength for co-word maps.

### 2.14 Track A sources
| Ref | URL |
|---|---|
| A1 | https://experts.mcmaster.ca/scholarly-works/837966 |
| A2 | https://arxiv.org/abs/1205.1150 |
| A3 | https://search.r-project.org/CRAN/refmans/Rcapture/html/closedp.html |
| A4 | https://arxiv.org/abs/2404.01176 |
| A5 | https://gwern.net/doc/statistics/order/capture/2017-chao.pdf |
| A6 | https://metricgate.com/docs/chao2-richness/ ; https://raw.githubusercontent.com/scikit-bio/scikit-bio/main/skbio/diversity/alpha/_chao1.py |
| A7 | https://pmc.ncbi.nlm.nih.gov/articles/PMC7700715/ |
| A8 | https://arxiv.org/html/2311.08597 |
| A9 | https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0232076 |
| A10 | https://discovery.ucl.ac.uk/id/eprint/10091273/1/1609406919899220.pdf |
| A11 | https://www.asc.upenn.edu/sites/default/files/2021-03/Computing%20Krippendorff%27s%20Alpha-Reliability.pdf |
| A12 | https://en.wikipedia.org/wiki/Krippendorff%27s_alpha |
| A13 | https://gdt.gradepro.org/app/handbook/handbook.html |
| A14 | https://www.fhi.no/ku/kunnskaps-og-beslutningsstotte/metodeboka/oppsummering-av-kvalitative-studier/grade-cerqual/ |
| A15 | https://www.nccmt.ca/resources/search/118 |
| A16 | https://e-journal.unair.ac.id/JJU/researchgap |
| A17 | https://aisel.aisnet.org/icis2015/proceedings/ResearchMethods/2 |
| A18 | https://fenix.iseg.ulisboa.pt/downloadFile/281608120804964/RQ%20gap%20or%20problem%20%20Sandberg%20&%20Alvesson%202011.pdf |
| A19 | https://blogs.lse.ac.uk/impactofsocialsciences/2013/10/13/constructing-research-questions |
| A20 | https://arxiv.org/abs/2304.10576 ; https://documents1.worldbank.org/curated/en/212651468163487838/pdf/WPS6725.pdf |
| A21 | https://www.wohlin.eu/ease14.pdf |
| A22 | https://doi.org/10.1136/bmj.n71 (not opened) |
| A23 | https://jmla.pitt.edu/ojs/jmla/article/view/962 |
| A24 | https://www.prisma-statement.org/s/PRISMA-P-checklist.pdf |
| A25 | https://arxiv.org/abs/1003.2551 |
| A26 | https://www.cs.cornell.edu/home/kleinber/bhs.pdf |
| A27 | https://ideas.repec.org/a/bla/jamist/v57y2006i3p359-377.html |

## 3. Track B: market and product methods
Items marked [U] could not be confirmed against a primary or authoritative source.

| # | Framework | Verified content | Caveats | Sources |
|---|---|---|---|---|
| 1 | Outcome-Driven Innovation | Outcome statement = direction + metric + object of control + contextual clarifier (about 5–10 per job step, 100+ per job). I and S = % of respondents rating 4–5 on a 1–5 scale, ÷10. Opp = I + max(I−S, 0). Thresholds: > 15 extreme, > 12 high, > 10 solid, ≤ 10 appropriately served; elsewhere ≥ 10 = underserved; S > I = overserved. | One Strategyn page leaves out the max(…,0) clamp. Sample size: 120–1,200 (Strategyn) vs 180–1,200 (Ulwick). | https://strategyn.com/customer-needs-through-a-jobs-to-be-done-lens/ ; https://customerthink.com/what-unmet-needs-should-be-targeted-for-growth/ ; https://www.productcompass.pm/p/jobs-to-be-done-masterclass-with |
| 2 | Jobs-to-be-Done | Job = "the progress that a person is trying to make in a particular circumstance". Forces: push + pull vs anxiety + habit; people switch when push + pull > anxiety + habit. Timeline: first thought → passive looking → event 1 → active looking → event 2 → deciding → purchase → consumption. Coding schema: {stage, force, trigger, old→new, verbatim}. | Patterns appear within 5–8 interviews per job. | https://jobstobedone.org/the-timeline/ ; https://jobstobedone.org/switch-interview/ |
| 3 | Kano | Functional and dysfunctional question pairs; answers Like, Must-be, Neutral, Live-with, Dislike. Evaluation table rows L → Q A A A O; M, N, W → R I I I M; D → R R R R Q. Category = mode, ties broken M > O > A > I. Better = (A+O)/(A+O+M+I); Worse = −(O+M)/(A+O+M+I) (Berger et al. 1993). | MeasuringU uses 50–300 respondents; Chapman & Callegaro: categories may be unreliable below N = 200. | https://pmc.ncbi.nlm.nih.gov/articles/PMC4769705/ ; https://measuringu.com/kano/ ; https://research.google/pubs/kano-analysis-a-critical-survey-science-review/ |
| 4 | Van Westendorp + Newton–Miller–Smith | "Too cheap" and "cheap" curves descend; the others ascend. OPP = too cheap ∩ too expensive; IPP = cheap ∩ expensive; PMC = too cheap ∩ not cheap; PME = too expensive ∩ not expensive; range PMC–PME; linear interpolation. Drop respondents whose answers violate the price ordering. NMS calibration 70/50/30/10/0% (Sawtooth defaults), 0% at the too-cheap and too-expensive prices; find the trial-maximising and revenue-maximising prices. | Wikipedia uses "expensive"/"cheap" instead of "not cheap"/"not expensive", so pick one convention and document it. n = 100–200 per segment is [U]. | https://en.wikipedia.org/wiki/Van_Westendorp%27s_Price_Sensitivity_Meter ; https://rdrr.io/cran/pricesensitivitymeter/man/psm_analysis.html |
| 5 | PMF survey (Ellis / Vohra) | "How would you feel if you could no longer use [product]?" PMF% = very disappointed ÷ responses excluding N/A; bar ≥ 40%. Survey users who used the core product ≥ 2× and recently (last 2 weeks); about 40 responses are directional. Superhuman went 22% → 33% → 58%. | Post-launch tool only. | https://blog.superhuman.com/how-superhuman-built-an-engine-to-find-product-market-fit/ |
| 6 | Interviews | Mom Test: talk about their life, specifics in the past, listen more; a good meeting ends in commitment or advancement. Blank: discovery → validation → creation → company building. Maurya: problem interviews before solution interviews; "10 'good' interviews any day over a 1,000-person survey" (2024). | Maurya's exit criterion of ≥ 10 interviews is [U] (course slides only). | https://www.ybrikman.com/blog/2023/03/29/the-mom-test/ ; https://steveblank.com/2009/09/17/the-path-of-warriors-and-winners/ ; https://ashmaurya.com/newsletter/2024-03-30 |
| 7 | Testing Business Ideas | Desirability, feasibility, viability. The assumptions map is importance × evidence; test the important, no-evidence quadrant first. Test Card: we believe / to verify / measure / we are right if. Learning Card: we believed / observed / learned / therefore. Evidence is stronger for doing over saying, facts over opinions, real world over lab, deposit over email. | The exact category membership and the book's numeric strength scale are [U]. | https://www.strategyzer.com/library/business-testing-is-your-hypothesis-really-validated ; https://www.strategyzer.com/library/validate-your-ideas-with-the-test-card |
| 8 | Opportunity Solution Tree | Outcome → opportunities → ≥ 3 solutions per target opportunity → assumption tests. Hidden-solution check. Compare sibling opportunities on sizing, market, company and customer factors. | These are comparison lenses, not a formula. | https://www.producttalk.org/opportunity-solution-trees/ |
| 9 | Blue Ocean | Strategy canvas (factors × offering level, one value curve per player); ERRC grid; Six Paths (alternative industries, strategic groups, buyer groups, complementary offerings, functional–emotional, time); three tiers of noncustomers. | — | https://www.blueoceanstrategy.com/tools/ |
| 10 | Canvases | VPC: jobs, pains, gains vs products, pain relievers, gain creators. Lean Canvas: problem (+ existing alternatives), segments (+ early adopters), UVP, solution, channels, revenue, costs, key metrics, unfair advantage. | — | https://www.strategyzer.com/library/the-value-proposition-canvas ; https://leanspark.ai/leancanvas |
| 11 | Sizing, Five Forces, PESTLE | TAM = ICP accounts × realistic annual ARPA; SAM = reachable subset; SOM = reachable × conversion × win rate, never "x% of TAM". Supplier power in SaaS = host platform or marketplace, model/API vendors, a single channel, graded on Rob Walling's 8 platform-risk levels. Substitutes = spreadsheets, agencies, in-house tools, doing nothing. PESTLE as a log (factor, change, date, evidence, job unlocked). Sequoia's "why now". | Common sizing errors are vendor-blog consensus; the Porter mapping is the agent's own. | https://store.hbr.org/product/the-five-competitive-forces-that-shape-strategy/R0801E ; https://www.startupsfortherestofus.com/episodes/episode-735-the-8-levels-of-saas-platform-risk-a-rob-solo-adventure ; https://www.cipd.org/uk/knowledge/factsheets/pestle-analysis-factsheet ; https://sequoiacap.com/article/writing-a-business-plan/ |
| 12 | Smoke tests | Unbounce 2024: median landing-page conversion 6.6%, SaaS 3.8%, industries 3.8–12.3%. Savoia XYZ: "At least X% of Y will Z". Wilson centre = (p̂ + z²/2n)/(1 + z²/n); half-width = z√(p̂(1−p̂)/n + z²/4n²)/(1 + z²/n). Pass if lower ≥ X; fail if upper < X; else inconclusive. n ≈ z²p(1−p)/h², fixed before starting. Ethics: disclose the truth right after the click, offer a waitlist, limit exposure, never charge without consent. | Waitlist conversion figures found online (20–40%, warm 25–45%, cold 10–20%, paid 3–10%) are [U], from vendor blogs with no methodology. The ladder click < email < booked call < LOI < deposit is the agent's synthesis. | https://unbounce.com/conversion-benchmark-report/ ; https://amplitude.com/explore/experiment/fake-door-testing ; https://www.productcompass.pm/p/how-to-build-the-right-product-with ; https://metricgate.com/docs/wilson-score-interval/ |
| 13 | SaaS patterns | Vertical vs horizontal SaaS. Unbundling: Parker, "The Spawn of Craigslist" (Jan 2010); Tunguz, "The Unbundling of Excel" (2017, mostly mid-market SMB). Graham 2012: "live in the future, then build what's missing"; schlep blindness. YC Requests for Startups, Fall 2026 (13 items). | Lower CAC and churn for vertical SaaS is [U]. Freelancer-post, template and integration-request heuristics are [U] (vendor blogs). | https://tomtunguz.com/unbundling-of-excel/ ; https://paulgraham.com/startupideas.html ; https://paulgraham.com/schlep.html ; https://www.ycombinator.com/rfs |
| 14 | RICE / ICE | RICE = Reach × Impact × Confidence / Effort; ICE = Impact × Confidence × Ease (each 1–10). Gilad's Confidence Meter ties confidence to the type of evidence. | The agent's view: ICE for experiment backlogs, RICE for build decisions, neither for choosing opportunities. | https://www.intercom.com/blog/rice-simple-prioritization-for-product-managers/ ; https://itamargilad.com/the-tool-that-will-help-you-choose-better-product-ideas/ |

**Track B recommendations as adopted**
- **(a) Desk discovery:**
  - Forces/timeline coding (D13).
  - A proxy ODI score used to rank only (D16). This is the agent's heuristic and is never compared to 10/12/15.
  - Strategy canvas and ERRC (D15, D18).
  - Bottom-up sizing, platform risk and a PESTLE log (D24, D21, D12).
  - A Wilson CI on every proportion.
  - Desk evidence capped at "weak" (D22).
  - An assumptions map that seeds Test Cards (V02).
- **(b) Validation:**
  - ≥ 10 Mom Test and switch interviews, until nothing new appears (V05).
  - ODI survey with n ≥ 180; Kano only with n ≥ 200; Van Westendorp + NMS with 100–200 per segment (V06).
  - Smoke test with an XYZ threshold and the Wilson rule at about 150–200 targeted visitors per variant, then LOIs or pre-sales (V07, V04).
  - ICE to order the experiment queue (V02).
  - Ellis PMF after launch, with ≥ 40 responses and a Wilson CI (deferred to the monitor stage).

## 4. Track C: data sources, terms of service, prior art, skill authoring
"Live" means the endpoint was called on 2026-10-09. "(2nd)" means secondary reporting only.

### 4.1 Free and public APIs
- **HN Algolia:** `/search`, `/search_by_date`, `/items/ID`, with `tags` and `numericFilters`. No auth (live). About 10k requests/hour per IP (2nd).
- **Stack Exchange 2.3:**
  - No key: 300 requests/day per IP (live: `quota_max:300`). Free key: 10k/day.
  - Cap of 30 requests/s; honour `backoff` (https://api.stackexchange.com/docs/throttle).
  - Content is CC BY-SA 4.0.
- **GitHub (`gh`):**
  - `gh search issues|prs|repos|code|commits`; discussions need `gh api graphql` with `search(type: DISCUSSION)`.
  - 30 requests/min authenticated; 10/min for code search or unauthenticated; 1,000 results per query.
  - Docs: https://docs.github.com/en/rest/search/search
- **Wikimedia Pageviews:** per-article REST endpoint (live). 10 requests/min unidentified, 200/min with a contact User-Agent (https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits, updated 2026-06-03).
- **WordPress.org:** `plugins/info/1.2` returns the star breakdown, support threads and installs. The reviews RSS feed is live. No auth.
- **Apple:** the customer-reviews JSON feed works (live; newest review 2026-10-07). Pages 1–10 hold 50 reviews each and page 11 fails. The feed is undocumented.
- **Google Play:** the official reviews API covers only apps you own. robots.txt disallows `/store/getreviews`, and Google's terms (https://policies.google.com/terms, 2026-07-30) ban automated access that ignores robots.txt.
- **Chrome Web Store:** the API is for publishing only (https://developer.chrome.com/docs/webstore/api); robots.txt disallows review pages.
- **Atlassian Marketplace:** `rest/2/addons` and `/reviews` work without auth (live).
- **Shopify and Slack:** no public read API found.
- **Zapier:** the Partner API needs a registered `client_id` (https://docs.zapier.com/powered-by-zapier/api-reference/apps/get-apps-v2.md).

### 4.2 Keyed or restricted sources
- **Reddit:** the Responsible Builder Policy (https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy, 2025-11-11) requires approval before any API use. Free tier: 100 queries/min per OAuth client (2nd); commercial use needs a contract, and ML training on user content is barred. Unauthenticated `.json` returns 403 (live); RSS still works but ends 2026-11-13. New API requests close 2026-10-31, and unregistered apps are cut off from 2027-01-12 through March 2027 (https://ppc.land/reddit-to-halt-public-data-api-access-in-march-2027-as-14-000-apps-register/, 2nd).
- **Product Hunt v2:** developer token; 6,250 complexity points per 15 minutes; no commercial use without permission (https://api.producthunt.com/v2/docs).
- **X:** pay-per-use or Enterprise. $0.005 per post read, capped at 3M reads/month (https://docs.x.com/x-api/getting-started/pricing).
- **Google Trends API:** alpha, by application (https://developers.google.com/search/apis/trends). pytrends was archived on 2025-04-17 (2nd).
- **Keyword Planner:** needs a Google Ads account and a developer token; Basic access allows 15k operations/day (https://developers.google.com/google-ads/api/docs/access-levels).
- **Paid SEO data:**
  - DataForSEO: pay as you go, $50 minimum, about $0.0006 per results page.
  - SerpApi: 250 free searches/month (https://serpapi.com/pricing).
  - Semrush: Business tier plus API units (https://www.semrush.com/kb/5-api).
  - Ahrefs: API v3 with Enterprise.

### 4.3 Review and directory sites
- **G2:** the terms (https://legal.g2.com/terms-of-use, 2026-07-09) ban scrapers and headless browsers, and ban using content to "train, test… analyze" ML. robots.txt blocks ClaudeBot on review paths. APIs are for partners only.
- **Capterra, GetApp, Software Advice:** G2 agreed to buy them (https://company.g2.com/news/g2-acquires-capterra-software-advice-getapp, announced 2026-01-29). Their terms ban automated extraction (2nd).
- **AlternativeTo:** the terms (https://alternativeto.net/terms/, 2026-10-07) forbid crawling beyond robots.txt and building a competing database.
- **SaaSHub:** free beta API; you must credit SaaSHub (https://www.saashub.com/site/api).
- **Indie Hackers:** robots.txt disallows AI bots.
- **YC:** robots.txt disallows `/companies?*`; the unofficial daily mirror is https://github.com/yc-oss/api.

### 4.4 Job and freelance signals
- **HN "Who is hiring":** `search_by_date?tags=story,author_whoishiring`, then `items/{id}` (live).
- **Upwork:** RSS removed 2024-08-20 (https://support.upwork.com/hc/en-us/articles/52052528243731-RSS-deprecation). API access is by application and the terms ban scrapers. The MCP terms (Aug 2026, 2nd) forbid "continuously monitor" use.
- **Fiverr:** no public API; scraping banned.

### 4.5 Legal and ethical
- **RFC 9309** (https://www.rfc-editor.org/rfc/rfc9309.html): robots rules are "not a form of access authorization". Cache robots.txt for at most 24 h; a 5xx response means assume everything is disallowed.
- **hiQ v. LinkedIn:** ended December 2022 with a $500k consent judgment, an injunction and data destruction (https://newmedialaw.proskauer.com/2022/12/08/hiq-and-linkedin-reach-proposed-settlement-in-landmark-scraping-case/).
- **Meta v. Bright Data:** the court found on 2024-01-23 that logged-out scraping did not breach Meta's terms; Meta dropped the case on 2024-02-23 (https://techcrunch.com/2024/02/26/meta-drops-lawsuit-against-web-scraping-firm-bright-data-that-sold-millions-of-instagram-records). Practical rule: never scrape while logged in.
- **GDPR:** usernames and quotes are personal data, and pseudonymised data stays personal data for whoever holds the key (EDPB Guidelines 01/2025). EDPS v SRB (2025-09-04) softens this for recipients who cannot re-identify anyone (https://www.cliffordchance.com/insights/resources/blogs/talking-tech/en/articles/2025/09/pseudonymized-data-after-edps-v-srb.html). CNIL (2025-06) expects precise collection criteria (https://www.cliffordchance.com/insights/resources/blogs/talking-tech/en/articles/2025/06/web-scraping-for-ai-development--the-cnil-builds-on-edpb-guidanc.html). In practice: store the URL plus a salted author hash, keep quotes short, and set a retention limit.
- **Research-agent practice:** a contact User-Agent, per-site rate limits, honouring `Retry-After`, caching, and no login or CAPTCHA bypass. Cloudflare has blocked AI crawlers by default since 2025-07-01.

### 4.6 Prior art
- **GummySearch** stopped selling on 2025-11-30 because Reddit forbids commercial apps without a licence (https://gummysearch.com/closing-time).
- **last30days-skill** writes cited 30-day briefs. **reddit-research-skills** depends on a third-party Reddit index, which is a compliance risk.
- **marketingskills/customer-research** uses verbatim quotes, confidence labels, ≥ 5 data points per segment and an injection guard.
- **GPT Researcher** pairs a planner with executors over 20+ sources and says it reduces bias rather than removing it.
- **STORM** reviewers saw "source bias transfer and over-association of unrelated facts" (https://arxiv.org/abs/2402.14207).

### 4.7 Skill authoring and portability
- **Anthropic best practices** (https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices): context is a public good (include only what Claude doesn't already know); match the degree of freedom to how fragile the task is; third-person descriptions saying what the skill does and when to use it; body under 500 lines with references one level deep and a table of contents in files over 100 lines; checklists and validate → fix → repeat loops; scripts for deterministic steps ("solve, don't defer") with no unexplained constants; no time-sensitive text; at least 3 evals against a no-skill baseline, tested across models.
- **agentskills.io** (https://agentskills.io/specification): `name` is 1–64 characters from `[a-z0-9-]`, with no leading, trailing or double hyphens, and equals the directory name; `description` ≤ 1024 characters; optional `license`, `compatibility` (≤ 500), `metadata`, `allowed-tools` (experimental); body under 5,000 tokens; check with `skills-ref validate`.
- **Where each tool loads skills:**
  - **Claude Code:** `~/.claude/skills`, `.claude/skills` and plugin `skills/`. Symlinks work; `.agents/skills` is not read. Subagents come from the Agent/Task tool; a skill's own `agents/` folder is not registered (only plugins register agents), so role briefs are plain files that subagents are told to read.
  - **OpenCode** (https://opencode.ai/docs/skills/, https://opencode.ai/docs/agents): `.opencode/skills`, `~/.config/opencode/skills`, `.claude/skills`, `~/.claude/skills`, `.agents/skills`, `~/.agents/skills`. Unknown frontmatter is ignored. Subagents run through the Task tool; whether tasks run in parallel was not confirmed.
  - **Codex** (https://learn.chatgpt.com/docs/build-skills, https://learn.chatgpt.com/docs/agent-configuration/subagents): `.agents/skills` up to the repo root, `~/.agents/skills`, `/etc/codex/skills`, with an optional `agents/openai.yaml`. Subagents start only when the instructions explicitly ask for them. The default sandbox has no network (https://developers.openai.com/codex/agent-approvals-security).
  - Claude Code skill docs: https://code.claude.com/docs/en/skills. Claude Code truncates descriptions at 1,536 characters, so the trigger words go first.

### 4.8 Access table
| Source | Access | Auth / cost | ToS posture | Tier |
|---|---|---|---|---|
| HN + Who is hiring | Algolia API | none | open | 1 |
| Stack Exchange | API 2.3 | none / free key | CC BY-SA | 1 |
| GitHub | `gh`, GraphQL | gh login | OK | 1 |
| Wikimedia Pageviews | REST | none; User-Agent required | open | 1 |
| WordPress.org | API + RSS | none | open | 1 |
| Apple reviews | RSS JSON | none | undocumented | 1 |
| Atlassian Marketplace | REST v2 | none | public | 1 |
| YC | yc-oss JSON | none | unofficial | 1 |
| SaaSHub | API | free key | credit required | 2 |
| Product Hunt | GraphQL | token | non-commercial | 2 |
| Reddit API | OAuth | approval; closing | strict | 2 if already approved, else excluded |
| Reddit .json / RSS | — | — | blocked / ending | excluded |
| X | API | pay per use | paid | 2 |
| Google Trends | alpha API | application | — | 2 (scraping excluded) |
| Keyword Planner | Ads API | account + token | — | 2 |
| DataForSEO / SerpApi | REST | $50 min / 250 free | vendor carries the scraping risk | 2 |
| Semrush / Ahrefs | REST | Business / Enterprise | contract | 2 |
| AlternativeTo, Slack, Shopify, Zapier, BetaList | page fetch | none | robots-limited; Shopify anti-bot | 0 (sparingly) |
| Chrome Web Store / Google Play | page fetch | none | review pages disallowed | 0 for listings; reviews excluded |
| G2, Capterra, GetApp, TrustRadius | — | partner APIs | explicit bans | excluded |
| Indie Hackers | — | — | blocks AI bots | excluded |
| Upwork / Fiverr | — | — | scraping banned | excluded |

### 4.9 Not verified in Track C
- HN's official rate limit.
- Stack Exchange's terms on AI use (the page returned 403).
- Reddit's own announcement posts.
- The actual terms text for Capterra, TrustRadius and BetaList.
- Upwork MCP and API eligibility.
- Whether G2's purchase of Capterra has closed.
- Semrush and Ahrefs prices.
- Whether Slack truly has no public listing API.

### 4.10 Lessons for the skill design
1. Keep a dated source registry with tier, endpoint, limits, ToS and the date it was checked. Implemented as `assets/channels.json` with `verified_on`.
2. Run with no keys by default (tiers 0–1). Turn on a tier-2 source only when its environment variable is set. On 403/429, stop and report; never work around it.
3. Write one deterministic fetch script per source family: contact User-Agent, rate limit, cache, robots.txt check, backoff. Output normalised JSONL with URL, date, metric, hashed author and a quote of at most 280 characters.
4. Triangulate before calling something a gap: pain + demand + supply, ≥ 3 independent sources across ≥ 2 platform types.
5. Run a validator on the final report: every claim has a URL and date, no raw usernames, and single-source or over-12-month-old evidence is flagged.
6. Treat fetched text as untrusted data.
7. Check network access before starting (Codex sandbox, Cloudflare 402/403) and state coverage gaps.
8. Write evals first: at least 3 niches with known outcomes, run across models.

## 5. Unit-test vectors
| Quantity | Inputs | Expected | Source |
|---|---|---|---|
| Chao2 Ŝ | T = 12, Q1 = 9, Q2 = 4, S_obs = 27 | 36.28 | A5 |
| Chao2 SE | same | 8.31 | A5 |
| Chao2 95% CI | same | 29.06–68.77 | A5 |
| Coverage Ĉ | same, U = 102 | 0.918 | A5 |
| Extra units t | C\* = 0.95 | 7 | derived, recomputed |
| m_g | g = 0.9 | 12.1 | A5 |
| x\* (units to reach Ŝ) | same | ≈ 5.27 | A5 |
| Webster–Kemp | A = 177, B = 265, AB = 171 | X̂ = 3.9, σ = 2.5 | A2 |
| Wilson 95% | 20 / 100 | 13.3%–28.9% | Track B §12 |
| Sample size | p = 0.10, h = 0.05 | 139 | Track B §12 |
| Sample size | p = 0.05, h = 0.03 | 203 | Track B §12 |
| ODI opportunity | I = 7.4, S = 2.8 | 12.0 | Track B §1 |
| Krippendorff α | the source's worked examples | .095, .692, .743 | A11; transcribed into tests/test_mgcore_math.py (binary 2 coders, nominal 2 coders, 4 coders with missing values) and passing |
| Snowball yield pattern | Wohlin worked example | 3/13, 7/25, 1/223, 0/33 | A21 (illustrative) |

## 6. Design decisions derived from the research
- **Sampling unit = scout × channel family** (Track A rec. 1). With 3 scouts × 3 families a round has 9 units, so Chao2 is usable after one round.
- **The stop rule uses point-estimate completeness S_obs/Ŝ ≥ 0.90 together with Ĉ ≥ 0.95, and reports the CI.**
  - A rule based on the CI's upper bound was rejected because it practically never stops at small T: in the worked example, 27/68.77 = 0.39.
  - The holdout probe (new-share ≤ 0.10) and marginal yield (≤ 0.05) guard against correlated scouts instead.
- **Snowball finds are excluded from incidence**, because they depend on what was already found.
- **Desk proxies never reuse survey thresholds:** the proxy ODI is used for ranking only.
- **No hardcoded smoke-test benchmarks.** X is derived from unit economics, and the Unbounce medians appear only as context.
- **Minimum samples:** Kano only with n ≥ 200; ODI n ≥ 180; Van Westendorp 100–200 per segment (flagged [U]). Ellis PMF is deferred to after launch.
- **Sources:** G2, Capterra, GetApp, Software Advice, TrustRadius, Indie Hackers, Upwork, Fiverr, LinkedIn and unauthenticated Reddit are excluded. Reddit is allowed only through an approved tier-2 key.
- **Privacy:** quotes ≤ 280 characters, salted author hashes, 180-day retention (a design default).

## 7. Disclosure: User-Agent incident and the MGD_CONTACT rule
During Track C, one test request to the Stack Exchange API sent a User-Agent header containing the user's account email. The research agent reported this itself and left the email out of every later request. Only that single request was affected.

**Design rule adopted:**
- The contact string that scripts send in User-Agent headers (required by Wikimedia, and good practice elsewhere) comes only from the `MGD_CONTACT` environment variable, which the human sets.
- It is never filled in automatically from account identity, git config or anything else.
- If it is unset, sources that require a contact are skipped and recorded as a coverage gap, and a human task asks the human to set it.

## Live verification of the adapters (2026-10-09)
After implementation, every keyless tier-1 adapter was run against the live APIs from a throwaway run folder. No `MGD_CONTACT` was set and no account data was sent.

| Adapter | Result |
|---|---|
| `hn`, `hn-counts`, `hn-hiring` | OK. **Finding:** Algolia's default typo tolerance inflated a one-month count for "invoice" from 152 exact matches to 2,370 (the exact phrase gives 93). The adapters now send `typoTolerance=false`; fuzzy counts would have made the burst analysis measure noise. |
| `se` | OK (300 requests/day without a key; quota reported in the output). |
| `wp-search`, `wp-reviews` | OK (plugin API plus the reviews RSS, robots-checked). |
| `apple-search`, `apple-reviews` | OK (the review JSON feed still works; real 1-star complaints returned). |
| `atl-search`, `atl-reviews` | OK. |
| `yc` | First failed: the 2.2 MB `companies/all.json` was cut off mid-stream (`IncompleteRead`). The adapter now reads `meta.json` and fetches only the matching tag and industry files, falling back to `all.json`. The network layer retries truncated reads, resets and timeouts twice. |
| `wiki-views` | Not run: it needs a contact User-Agent (`MGD_CONTACT`), which only the human may set. |
| `gh-issues`, `gh-repos` | Not run: `gh` was not logged in on this machine; `doctor` creates a human task for it. |

Quote verification was re-checked on a real App Store review snapshot: a verbatim excerpt verified and a paraphrase failed. An excluded source (a G2 review URL) was refused with exit 2 and logged as a coverage gap.

## Live dry run with real subagents (2026-10-09)
**Setup.** Run `gap-runs/dryrun-translators`. Niche: invoicing and payment follow-up for freelance translators. Real general-purpose subagents ran the role briefs; the network was live. Run folders are git-ignored.

| Step | Live result |
|---|---|
| Lexicon (3 scouts, different personas) | 645 terms. Mean overlap 0.07 exact and 0.06–0.12 normalised: the personas really did see different vocabularies. One round, by a logged amendment. |
| PRESS review | Verdict `revise`: 60 terms removed, 31 added. It found that ties broken alphabetically decided what was searched (see the fixes below). |
| Landscape round 1 (3 scouts × 3 units, 7 channel families) | 221 items became 186 unique entities. 31 entities were found by more than one unit. |
| Screening (5 batches for A, 1 blind batch for B) | 111 included, 46 excluded with reason codes, 29 unsure (403, robots.txt, JavaScript-only pages). **Audit: Krippendorff's α = 0.95, κ = 0.95 over 38 double-screened entities, 1 disagreement.** |
| Entity verification | 110 of 111 verified. One blocked by robots.txt. 49 verified from snapshots that screeners had already made, with no refetch. |
| Saturation after round 1 | S_obs 110, T 9, Q1 81, Q2 26. **Chao2 218 (95% CI 170–306), completeness 0.50, coverage 0.485 → EXPAND k=9.** One round found only about half the market. |
| Evidence (3 miners, on a copy of the run) | 205 records submitted, 201 merged (4 duplicates). **201 of 201 quotes found verbatim in their snapshots (100%).** 137 distinct authors, 21 domains, 28% praise or counter-evidence, 19 S4 and 25 S3 records, 7 why-now catalysts (Belgium's 2026 B2B e-invoicing mandate, EU ViDA, UK MTD, FreshBooks price rises, Peppol access costs). |
| Open coding (1 coder, 30-record base) | Codebook v1: 33 codes. 9 jobs on the job map (no evidence for the prepare step), 9 ODI outcomes, 9 pains, 1 gain, 5 segments. With the 17 standard codes, 50 in total. |
| Closed coding (coder A, 4 batches) | 201 of 201 records coded. 53 records carry new-code proposals and 19 fit no code. Both coders independently proposed "let clients pay online" and "track billable time". |
| Reliability, random sample (coder B, 41 records) | Only **3 of 37 codes** had enough positives to be measured, so the verdict read ACCEPT while weak codes went unmeasured (J-TRACK-PAYMENTS α 0.66, F-HABIT α 0.37). |
| Reliability, stratified top-up (+54 records) | 95 double-coded records; **all 38 eligible codes measured: 33 accept, 4 provisional, 1 revise (F-HABIT α 0.58) → REVISE.** J-TRACK-PAYMENTS rose to α 0.90 once it had enough positives. Strength grades, A vs B: α 0.83. Miner vs A: κ 0.88 over 201 records, an upper bound because coders saw the miner's grade. |
| Theme saturation | 64 themes observed, Chao2 80, coverage 0.963, Guest–Namey–Chen test passes → **SATURATED**. |
| Codebook revision (1 reviser, live) | The reviser got 5 codes to revise, 16 disagreement quotes and 40 pooled proposals. **Codebook v2: +3 codes (online payment, billable time, compliance burden, each raised by both coders), 6 sharpened** (F-HABIT, F-PUSH, T-CONSUME and X-LANG as standard codes with their core fields fixed, plus O-TAX-REPORT-TIME and J-COLLECT-FOREIGN-PAYMENT). 46 cited records held out of v2 reliability testing. The live run stops at the v2 recoding assignments (4 batches, 201 records); the simulated run covers the full revision cycle. |

**Defects the live run found, all fixed and covered by regression tests:**
1. **Query blocks.** Alphabetical tie-breaking chose what was searched, reviewer additions never reached a block, words were doubled, and the `other` facet went unused. Ranking is now by consensus, then curated terms, then relevance to the protocol, with seeded tie-breaks; there are new templates.
2. **Lexicon overlap.** Overlap was measured on exact strings. It now uses normalised keys (case, plurals, word order, stop-words).
3. **YC adapter.**
   - Substring matching against tag names ("per" matched "personal-finance").
   - No relevance ranking.
   - A >6 MB file was truncated after decompression.
   - It now matches whole words, ranks by relevance, sets the size limit per call and caches the file within a run.
4. **HTTP reading.** A single `read(n)` can return a short read, which cut off long pages. The fetcher now reads until end of stream. It also follows HTTP 308 redirects on Python < 3.11, and retries truncated, non-JSON or reset responses once or twice.
5. **Entity verification.** Name matching was too strict: 11 false negatives such as "Zap-Bill" vs "Zap Bill". It now tolerates variants, and `entities verify --recheck` re-evaluates from existing snapshots.
6. **Screening at scale.** One screener got all 186 entities. Screening now runs in batches of 40, sorted by name so duplicates share a batch. The rule order is unified with D06, and a reused snapshot is now stated to be valid evidence.
7. **Alias joins.** The landscape merge stores an app and its website as one entity, keeping the second key as an alias. Evidence citing the alias (`dom:freshbooks.com` for the FreshBooks App Store entity) was dropped from the competitor matrix, the satisfaction proxy, praise counts and evidence balancing. Now one resolver (`alias_map`) maps every key to its primary id, both at merge time and at every join.
8. **Silent blocks and empty data.**
   - An HTTP 202 with an empty body (a bot challenge) was being saved as a page. It is now a block and a coverage gap.
   - Apple's review feed went from 50 reviews to an empty feed within an hour, on every URL variant. An empty feed now prints a warning and logs a coverage gap: missing data, never "no complaints".
   - App stores answer 404 for apps not offered in the fetching machine's country. Screeners now retry with a storefront from the protocol's geography before EX-NOT-FOUND.
9. **Limitations the miners cannot see.** `prisma.json` now reports:
   - large evidence pools screened only at the top, without the stopping test (live: 5 Hacker News pools of 210–2,142 hits, 40 read each; the 25-call budget cannot cover the test);
   - products first named in evidence but missing from the landscape (live: 15, including Xero, FreeAgent, Stripe and Quaderno). This independently confirms the round-1 verdict that about half the market was still unseen.
10. **Coding contracts.**
    - Closed and reliability coders were told to grade strength with D10 but were not given D10. They now are.
    - D13 had no intensity anchors. D14 now has them, including the convention for records with no pain.
    - Coders could see the miner's strength grade, which anchors an "independent" re-grade. It is now withheld, and `agreement` reports miner vs coder κ.
    - The codebook-revision assignment lacked the disagreements and proposals that D13 promised. It now lists `codes_to_revise`, `disagreements` (quotes where A and B split) and both coders' pooled `proposals`, each proposal with up to 5 quotes.
    - In the live revision, 4 of the 5 codes to revise were standard codes (F-HABIT, F-PUSH, T-CONSUME, X-LANG), which the rules forbade the reviser to define. Freeze now accepts a sharpened standard code: include, exclude and examples change, while id, type, label and definition stay fixed, and the sharpening carries forward. It refuses a revision that changes none of the listed codes.
    - The 40-code limit was hard-coded and only advisory, and the reviser counted sharpened standard codes toward it. It is now `coding.max_own_codes` in the defaults, it counts own codes only, and freeze enforces it, with `protocol amend` to raise it.
    - The reviser pointed out that examples in the revised codebook would inflate agreement if they were recoded. Records the frozen codebook cites, as examples or in its notes, are now held out of reliability sampling and of α, as Krippendorff advises: never test on the units used to build the instrument.
11. **Reliability sampling.**
    - A random sample measured 3 of 38 eligible codes, and the verdict ignored the rest.
    - Sampling is now a random core plus a stratified top-up, 5 positives and 5 negatives per eligible code, with numbered top-up assignments.
    - The coding merge adds to coder B's codes instead of replacing them.
    - A new verdict, `insufficient`, sends `next` back for a top-up. `agreement` decides this with the same selection function `assign` uses, so the two can't disagree.
    - Constant codes (undefined α, no variation) never block.
12. **The revision loop never ran (found by a simulated revision cycle).**
    - Open coding and revision both wrote `coding/codebook.json`, and `next` judged readiness by whether the file existed. After a `revise` verdict it froze the stale v1 draft as "v2" and never spawned the reviser.
    - Drafts are now versioned (`codebook-draft-vN.json`). Freeze reads the path that version's assignment declares, and refuses a revision that leaves every listed code unchanged.
    - The simulated run now goes through one full revision cycle: v1 fails on a code, the reviser gets the disagreements, and v2 is recoded and accepted.
13. **Contract wording.**
   - `--by` now uses the assignment id everywhere.
   - `validate --file` lets an agent self-check one file.
   - The scout brief now separates policy blocks from transient failures.
   - The `results` field is defined.
   - Scouts must not use AlternativeTo as an entity URL, because it returns HTTP 403.

**Source limits seen live:**
- AlternativeTo returns 403 to automated fetches.
- Apple's review feed was empty for 9 of 10 apps tested.
- Some vendor sites block AI agents in robots.txt.
- The built-in web search is US-indexed.
- Translator-specific evidence is scarce in general channels: most records are indirect, which is correctly penalised in certainty.

## Full live run and critique: indie-dev-tools (2026-10-09)
A complete discovery run on "low-touch SaaS tools for indie developers and solo founders" (`gap-runs/indie-dev-tools`, report in `reports/indie-dev-tools/`). Operator cost reported by the user: about $250, every subagent on the session model (Opus 5.5), about 4 hours.

### What it produced
| Measure | Value |
|---|---|
| Assignments (subagents) | 91: screening 30, landscape 12, coding 19, snowball 9, lexicon 7, evidence 6, other 8 |
| Verified competitors | 395 (Chao2 ~281, coverage 0.69, STOP_UNSATURATED) |
| Screening reliability | alpha 0.90 over 162 double-screened entities |
| Evidence | 289 quotes, 100% verified verbatim; round 1 drew 158 of 165 from two sites |
| Coding | codebook v3, all 22 eligible codes measured, provisional (none weak) |
| Gap cards | 12; 1 passed after round 1, 3 after a targeted round; red team killed 2, weakened 1 |

### Strengths worth keeping (and amplifying)
- Script-side integrity held under load: 100% of quotes verified, schema-checked merges, rejected bad snapshot references instead of trusting them.
- Independence and agreement statistics worked as designed: screening alpha 0.90; the coding revision loop raised a weak code to accepted.
- The red team was honest: it killed two near-miss cards with dated, verified competitors (crxpay, ExtensionPay; Pulsetic, OnePageStatus).
- Every human directive (saturation targets, targeted round, budget) became a hashed amendment that the dossier reports.

### Weaknesses found, and what changed
| # | Weakness | Fix |
|---|---|---|
| 1 | Cost: every subagent ran on the session model | Model tier per role (`models` in defaults, `cost_profile` in the protocol); machine-checked roles on the fast tier (Haiku 5.5 lists at $0.10/$0.50 per MTok against Opus 5.5's $4/$20), escalation on failed checks |
| 2 | Screening was a third of all spend | Batches of 60; B audit after every merge and retired once alpha is accepted over 50 units |
| 3 | Snowball never converged on a broad topic (67/80/82 new) | `snowball.max_iterations` 1; red team does per-gap existence searches |
| 4 | Landscape round 4 bought +0.09 coverage; 12 units per scout | Stop when a round adds < 0.05 coverage; cap 4 units per scout; per-round history in `saturation.json` |
| 5 | Lexicon round 2 added 650 terms, ~4% used; overlap read 0.02 by construction | One round by default; overlap computed on cumulative per-scout vocabularies |
| 6 | Evidence concentrated in two domains; 11 of 12 cards failed on domains; the targeted round needed a human decision | Miners get a diversity rule with ledger domain shares; `cards check` records structured shortfalls; `next` runs one targeted round for near-miss cards automatically |
| 7 | Broad topic (7 jobs) was the root cause of thin evidence | `protocol check` and freeze warn at >= 5 jobs; SKILL.md tells the orchestrator to narrow first |
| 8 | Truncated snapshot ids rejected 39 records with no way to re-merge | Unique-prefix resolution and `merge --phase evidence --retry` |
| 9 | Supply map stale after a codebook revision (license keys would have looked unserved; 24 products serve it) | Supply records its codebook version; `next` re-maps in update mode |
| 10 | Gap cards stale after new evidence; flow went straight to red team | Synthesis is stale when the gap map is newer than the card check; update mode keeps previous cards |
| 11 | Canonicalisation: Honeybadger keyed `dom:google.com`, Userback `dom:mozilla.org` | Redirect unwrapping, Firefox/Edge add-on keys, shared hosts never become product keys |
| 12 | Writer lacked analysis/, amendments and events; sizer snapshotted a robots-blocked API | Writer inputs widened; sizer told to use the API adapters |
| 13 | 300-line dossier hard to read | `viz`: `summary.md` and a dashboard (PNG charts + offline HTML) from the run's files |
| 14 | Subagent replies (20-40 lines) bloated the orchestrator's context | Replies capped at three lines (assignment rule and SKILL.md); orchestrator may run on Sonnet and resume in a fresh session |

### Expected effect on the same run (estimate, not measured)
Replaying the live run's numbers through the new defaults: lexicon 4 (was 7), landscape 9 (12), screening about 12 (30), snowball 3 (9), coding about 9 (12) and the rest unchanged, so about 55 assignments instead of 91. With about 45 of them on the fast tier, subagent token cost falls by roughly an order of magnitude at list prices, if fast-tier quality holds; the scripts' checks (verify, merge rejections, screening and coding alpha) detect it when it does not and escalate the role. The orchestrator's own context is the other large cost, addressed by short replies and a cheaper orchestrator model. Re-run a narrow topic to measure the real numbers.
