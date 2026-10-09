# D22 · Certainty of evidence

| Origin | Phase | Roles | Status |
|---|---|---|---|
| GRADE certainty of evidence (risk of bias, inconsistency, indirectness, imprecision, publication bias; upgrades for large effect and dose–response); GRADE-CERQual for qualitative findings (methodological limitations, coherence, adequacy, relevance); evidence strength from Testing Business Ideas | P6 Appraisal | orchestrator | core |

**Use when:** after `merge --phase redteam`, when `next` issues `RUN gapscan.py certainty RUN`.

**Why:** Systematic reviews never report a finding without saying how far to trust it. A gap claim has two parts, backed by different evidence:
- "This pain exists and looks like X" is a qualitative claim, rated with CERQual.
- "Enough people will pay to fix it" is a claim about prevalence and willingness to pay. It is rated GRADE-style starting at Low, like observational evidence.

Rating them separately, and capping desk-only demand strength at weak, stops a vivid set of complaints from being read as proof that a market exists.

**Inputs**
- `gaps/cards.jsonl`, `gaps/card-check.json`, `gaps/redteam/*.json`.
- `evidence/ledger.jsonl` (credibility, stance, indirect, strength, author_hash, domain) and `coding/codes-A.jsonl`.
- `coding/agreement.json` (provisional codes), `landscape/saturation.json` (Ĉ and verdict), and `state.json` (independence).
- The `certainty.*` defaults.

**Procedure**
1. Run `gapscan.py certainty RUN`. For each card that passed `cards check` and wasn't killed, it rates concerns from the card's supporting and counter evidence:
   - **Risk of bias:** the share of supporting records whose credibility is vendor, incentivized or affiliate. Moderate above `bias_moderate` (0.15); serious above `bias_serious` (0.3).
   - **Inconsistency (coherence):** contra ÷ (supporting + contra). Moderate above `inconsistency_moderate` (0.15); serious above `inconsistency_serious` (0.3).
   - **Indirectness (relevance):** the share of supporting records flagged `indirect` (an adjacent persona, or a stated rather than revealed preference). Moderate above `indirect_moderate` (0.5); serious above `indirect_serious` (0.75).
   - **Imprecision (adequacy):**
     - distinct supporting authors below `authors_serious_below` (5) is serious; below `authors_moderate_below` (10) is moderate
     - take the prevalence proportion: records coded with the card's pain codes ÷ records coded with its job codes. A 95% Wilson interval on it wider than `ci_width_moderate` (0.3) is moderate.
   - **Methodological limitations** (pain claims): the card rests on provisional codes (D14). Moderate.
   - **Publication bias / coverage** (demand claims):
     - landscape Ĉ below `coverage_moderate_below` (0.9), or the verdict STOP_UNSATURATED: moderate
     - independence degraded: moderate
     - both of the above: serious
2. **Pain certainty** (CERQual-style). Start at High. Score 2 points per serious concern and 1 per moderate concern, across methodological limitations, coherence, adequacy and relevance:
   - 0 points: High
   - 1 point: Moderate
   - 2–3 points: Low
   - 4 or more: Very low
3. **Demand certainty** (GRADE-style). Start at Low.
   - Downgrade one level per serious concern and one level per two moderate concerns, across risk of bias, inconsistency, indirectness, imprecision and publication bias. The floor is Very low.
   - Upgrade one level for **magnitude**: S4 records (money spent, or a paid tool switched) from at least `magnitude_min_authors` (3) distinct authors in at least two domains.
   - Upgrade one level for **dose–response**: X-SCALE coded for at least `dose_response_min_authors` (3) authors.
   - Desk-only demand certainty is capped at Moderate.
4. **Demand strength** is weak for every desk-only card. Only the validation skill's experiments (sign-ups, letters of intent, pre-sales) can raise it to moderate or strong.
5. Copy the labels from `gaps/certainty.json` into the dossier exactly. Don't soften or upgrade them in prose.

**Output:** `gaps/certainty.json`. Per gap: every concern with its numbers, the upgrade checks, pain certainty, demand certainty, demand strength, and a one-line reason for each downgrade.

**Metrics and checks**
- GRADE and CERQual are judgment frameworks with no fixed numeric thresholds. The operationalisation above is this skill's own adaptation; its thresholds live in `defaults.json`, and changing one requires a protocol amendment.
- The ranking (D23) uses certainty to break ties, and the dossier (D25) shows both labels beside each score.

**Pitfalls**
- **Treating many posts as precision.** Imprecision counts distinct authors: 50 posts by 4 people are 4 authors.
- **An empty counter-evidence list.** No coherence concern can arise if nobody looked. Existing solutions found by the red team belong in the card's `counter_evidence` before you rate it.
- **Promoting desk evidence to "validated".** Desk-only demand strength is weak, whatever the certainty label says.

**Done when:** every scorable card has pain certainty, demand certainty and demand strength in `gaps/certainty.json`.
