# D04 · Search saturation and stopping

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Doctoral teams' "~90% intersection" rule; capture–recapture stopping for literature searches (Kastner et al. 2009); Chao2 richness (Chao & Colwell 2017); sample coverage (Chao & Jost 2012) | P2 Landscape | orchestrator, scout (probe) | core |

**Use when:** after every `merge --phase landscape`, and again after the probe is merged.

**Why:** Independent searchers who keep finding the same products have probably found most of them. That is the doctoral rule. Raw overlap overstates completeness in two ways: famous products are easy for everyone to find, and copies of the same model search alike. So the overlap is turned into an estimate of how many products exist in total, including unseen ones (Chao2). That estimate is checked from two more angles (sample coverage and marginal yield), and then tested directly with a fresh holdout searcher (the probe). Every number is a lower bound, and the dossier reports it as one.

**Inputs**
- `landscape/incidence.json`: for each verified, included entity, the sampling units that found it. Snowball-only finds are excluded.
- `assets/channels.json`: which entity kinds each channel family can surface.
- Protocol thresholds (defaults under `landscape.*` in `assets/defaults.json`).

**Procedure**
1. Run `gapscan.py saturation RUN`. It computes everything below overall and per entity kind. For each kind it uses only the units whose channel can surface that kind.
2. Read the verdict in `landscape/saturation.json`, then call `next`. It turns the verdict into the next action:
   - **EXPAND k**: run another landscape round with k new units. k is the estimated number of extra units needed to reach the coverage target. It is at least one unit per scout and at most T, because estimates are not extrapolated beyond twice the current sample.
   - **NEEDS_PROBE**: the estimator conditions pass. Run one holdout scout through `assign --phase probe`. It gets a persona and query blocks that no scout has used yet, on the channel family with the fewest units so far.
   - **SATURATED**: every condition holds, including the probe. Move on to snowballing (D05).
   - **STOP_UNSATURATED**: the round limit was reached without saturating. Continue to snowballing, but the run carries this as a limitation and certainty is downgraded (D22).
3. As the probe scout, follow D03 exactly, with these additions: use only your assigned persona and blocks; do not search for products you already know; report everything you find.
4. Never edit `saturation.json` or the incidence by hand. If a number looks wrong, check the inputs (screening decisions, entity verification) and re-run the scripts.

**Output:** `landscape/saturation.json` with these fields, overall and per kind:
- S_obs, T, Q1, Q2, U
- Chao2 estimate, SE and 95% CI
- completeness S_obs/Ŝ
- coverage Ĉ
- marginal yield
- probe new-share
- extra units needed (t for the coverage target, m_g for the completeness target)
- verdict and reasons

**Metrics and checks** (formulas and worked examples in `references/metrics.md` §1)
- Chao2: Ŝ = S_obs + ((T−1)/T)·Q1²/(2·Q2), or S_obs + ((T−1)/T)·Q1(Q1−1)/2 when Q2 = 0. The 95% interval is log-normal.
- Coverage: Ĉ = 1 − (Q1/U)·B, where B = (T−1)Q1 / ((T−1)Q1 + 2Q2).
- **SATURATED** requires all of:
  - Q1 = 0, or (Ĉ ≥ `coverage_target` (0.95) and S_obs/Ŝ ≥ θ (0.90))
  - marginal yield ≤ 0.05 in round 2 or later
  - probe new-share ≤ 0.10
  - T ≥ 6
  - at least 3 entities of every kind that a unit can surface

**Pitfalls**
- **Correlated scouts.** If mean pairwise Jaccard is above 0.85 while S_obs is below 15, the script adds a `correlated_scouts` flag. The scouts were not independent: diversify the personas and channels in the next round, and expect the probe to fail.
- **Counting what you snowballed.** Snowball finds depend on what was already found. Counting them would inflate overlap, so they stay out of the incidence.
- **Unverified entities.** An entity counts only after screening includes it and `entities verify` confirms the page exists and names it. Unverified or hallucinated products would distort Q1.
- **Reading a lower bound as a fact.** Write "at least about N products (95% CI a–b)", never "there are N products".

**Done when:** the verdict is SATURATED, or STOP_UNSATURATED with the limitation recorded, and `next` has moved on to snowballing.
