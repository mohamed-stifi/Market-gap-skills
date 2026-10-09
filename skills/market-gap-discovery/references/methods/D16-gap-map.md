# D16 · Demand-supply gap map

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Evidence Gap Maps (Snilstveit et al. 2016, 3ie) ↔ demand–supply grid; co-word association strength (van Eck & Waltman 2009); Outcome-Driven Innovation opportunity score (Ulwick), used here only as a desk proxy | P4 Coding and synthesis | orchestrator (runs), synthesizer (reads) | core |

**Use when:** `matrix` has run and `next` issues `RUN gapscan.py gapmap RUN`.

**Why:** An evidence gap map lays interventions against outcomes. It shows where studies are missing (absolute gaps) and where many studies exist but nobody has brought them together (synthesis gaps). Laying jobs against solution approaches does the same for a market: it shows where people complain and nothing serves them, and where many point tools exist but users still juggle them. Demand counts distinct authors with strength weights, not posts, so one loud user or one viral thread can't create a gap.

**Inputs**
- `coding/codes-A.jsonl`: primary codes of verified records.
- `evidence/ledger.jsonl`: stance, strength, author_hash, domain and entity_ids.
- `analysis/supply.jsonl` and `landscape/entity-attributes.jsonl` (approach).
- The frozen `coding/codebook.vN.json` (version in `coding/codebook.lock.json`).

**Procedure**
1. Run `gapscan.py gapmap RUN`. For each job and outcome code it computes:
   - **Demand D:** for each distinct author, take the highest strength weight among their verified records that carry the code and have stance pain, wish, workaround, switch or wtp; D is the sum over authors. The weights are `evidence.strength_weights`: S0 0.25, S1 0.5, S2 1.0, S3 1.5, S4 2.0. The script also counts distinct authors and distinct domains.
   - **Supply per solution approach:** included entities of that approach whose `jobs_served` contains the code.
   - **Satisfaction proxy:** S_p = 10 × praise ÷ (praise + pain), counted in distinct authors, over verified records about incumbents that serve the code.
   - **Cell type:**
     - absolute gap: total supply ≤ `gapmap.absolute_supply_max` (1), and at least `gapmap.min_demand_authors` (5) distinct demand authors
     - synthesis gap: supply ≥ `gapmap.synthesis_supply_min` (5), and at least `gapmap.synthesis_fragmentation_share` (0.2) of the job's demand records are coded X-FRAG or X-INTEG
     - otherwise none
2. It also measures, for each segment code × pain code pair over verified records, how much more often they appear together than chance would predict:
   - c_ij = the number of records carrying both codes
   - c_i = Σ_{j≠i} c_ij
   - association strength AS_ij = c_ij / (c_i·c_j)
   - observed ÷ expected = 2m·AS_ij, where m = ½ Σ c_i
   
   Pairs with c_ij ≥ `gapmap.assoc_min_cooccurrence` (3) and a ratio above 1 are segment-specific pains, written to `analysis/association.csv`.
3. It computes a proxy opportunity score per job and outcome code:
   - I_p = 10 × D ÷ (max D over all codes)
   - Opp_p = I_p + max(I_p − S_p, 0)
   - When no evidence about incumbents exists, S_p = 0 and the cell is flagged `no_satisfaction_data`.
4. **Synthesizer:** read `analysis/gapmap.json` in this order: absolute gaps, synthesis gaps, the highest Opp_p codes, then the strongest segment-specific pains. Each is a lead for D17–D19, not yet a gap.

**Output**
- `analysis/gapmap.json`: per cell, demand, distinct authors, distinct domains, supply by approach, S_p, I_p, Opp_p, cell type and flags.
- `analysis/association.csv`.

**Metrics and checks**
- Every number comes from verified records only. Records that failed `verify` don't exist here.
- Opp_p ranks codes within this run. It is not an ODI survey result, so never compare it with the survey thresholds 10, 12 or 15, and never write "underserved (ODI ≥ 10)" from desk data. Only the validation skill's ODI survey can establish that.
- Demand counts authors. Records with `author_hash: unknown` count as one author per domain, which deliberately lowers the estimate when authorship is unclear.

**Pitfalls**
- **Reading an empty cell as an opportunity.** A cell can be empty of supply because nobody needs the job. The `min_demand_authors` condition guards against this; never lower it to manufacture gaps.
- **Over-weighting one platform.** Check distinct domains: 30 authors from one forum thread is still one source.
- **Forgetting substitutes.** A job no SaaS serves but templates or agencies do is a price, quality or access gap, not an absolute one.
- **Reading association as cause.** A pain linked to a segment means "mentioned together more than chance would predict". It is a lead for the segment-split check in D17.

**Done when:** `analysis/gapmap.json` reflects the current supply and coding, and `next` has moved on to P5 (`variants`).
