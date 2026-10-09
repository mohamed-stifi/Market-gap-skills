# D17 · Gap spotting (confusion, neglect, application)

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Gap-spotting modes (Sandberg & Alvesson 2011); research-gap reasons and PICOS (Robinson et al. 2011); seven research-gap types (Miles 2017) mapped to market gap types; noncustomer tiers (Kim & Mauborgne) | P5 Gaps | synthesizer | core |

**Use when:** you are working the synthesis assignment (`gaps/synth-assign.json`), after `gapmap` and `variants` have run.

**Why:** Doctoral researchers construct gaps in three recognisable ways. They find contradictions (confusion), overlooked areas (neglect), or settings where a known idea hasn't been applied (application). Running all three as explicit scans over the gap map and the coded evidence makes gap construction systematic. Every candidate can then say which scan produced it and which cells and records it rests on, instead of being a brainstormed idea.

**Inputs**
- `analysis/gapmap.json`, `analysis/association.csv`, `analysis/competitor_matrix.csv`, `analysis/price_ladder.csv`, `analysis/pain_by_entity.csv`.
- The frozen `coding/codebook.vN.json`, `coding/codes-A.jsonl`, `evidence/ledger.jsonl`, `evidence/why-now.jsonl`.
- `gaps/variants.jsonl` and `landscape/screening.jsonl`.

**Procedure** (run every scan and note each lead before judging it)
1. **Confusion scan.** For each job, pain and feature code, compare the majority stance (pain vs. praise) across segment codes and across platforms. When one segment's majority is praise and another's is pain, and each is backed by at least `gapmap.min_demand_authors` distinct authors, you have a segment split: the product fits one group and fails another. Also check `analysis/association.csv` for pains tied to a single segment.
   - Set sa_mode `confusion`.
   - Set robinson_reason `inconsistent`, or `biased` when the incumbent clearly targets the other group.
2. **Neglect scan.** Take every absolute gap, every synthesis gap and the highest Opp_p codes from the gap map. Add job-map steps that have demand but no serving product (D13). Classify noncustomers when the evidence shows them:
   - tier 1, soon-to-be: current users talking about leaving ("about to cancel", "looking for something else")
   - tier 2, refusing: people who considered a product and rejected it for a stated reason (price, complexity, language)
   - tier 3, unexplored: a segment that never mentions any product, only workarounds
   
   Set sa_mode `neglect`. Set robinson_reason `insufficient` (little or no supply) or `wrong-information` (supply serves a different job or outcome). Set `noncustomer_tier` when one applies.
3. **Application scan.** Take the variants in `gaps/variants.jsonl` (D19), plus products that are strong in one segment, language or platform but absent in another (competitor matrix). Set sa_mode `application`.
4. For each lead, map the research-gap type to a market gap type, so the card is explicit about the kind of hole:
   - evidence gap (contradictory findings) → confusion; a segment or quality gap
   - knowledge gap (nothing exists) → absolute gap; a feature, segment or non-consumption gap
   - practical-knowledge gap (practice differs from what tools assume) → workaround evidence; a quality or feature gap
   - methodological gap (everyone solves it the same way) → problematization (D18)
   - empirical gap (claims never tested) → vendor claims without user evidence; a trust gap
   - theoretical gap (behaviour nobody explains) → an open question for the dossier, not a card
   - population gap (a group under-served) → a segment or language gap
5. Write each lead that has at least one verified supporting record as a gap card (D20) with `status: candidate`. Set `origin_methods` to include D17, plus D16 and D19 when they produced the lead. Drop leads with no verified record. Without evidence a lead is an idea, not a candidate.
6. Collect counter-evidence for every lead: praise of incumbents for the same job, contra records, products that already serve the segment. A lead you can't argue against has not been examined.

**Output:** gap cards in your synthesis output file (`gaps/cards.jsonl`). Each card names its scan in `sa_mode` and `origin_methods`.

**Metrics and checks**
- `gapscan.py cards check RUN` applies the D20 thresholds. Cards that fail are treated as `insufficient` downstream and are counted in the PRISMA flow.
- Every lead cites cells (gap map), codes and EV ids. If you can't name them, the lead isn't ready.

**Pitfalls**
- **Brainstorming.** An idea with no scan origin and no evidence ids is not a candidate, however plausible it sounds.
- **Mistaking volume for neglect.** Noisy complaints about a market leader usually signal a quality gap with strong supply, not neglect.
- **Ignoring dead products.** Entities screened `EX-DEAD` in `landscape/screening.jsonl` are past attempts. Mention them in `why_empty`; the red team (D21) needs them.
- **Discarding contradictions as noise.** Check the segment codes first: contradiction is often a hidden segment split, which is a gap in its own right.

**Done when:** all three scans have run, and every lead with verified evidence is a card in `gaps/cards.jsonl`.
