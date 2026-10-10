# D20 · Gap card

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Characterising research gaps with PICOS and a reason (Robinson et al. 2011); the gap-statement template from the research-gap method; the market gap taxonomy; methodological triangulation (Denzin) | P5 Gaps | synthesizer, orchestrator | core |

**Use when:** every lead from D17, D18 or D19 that has verified supporting evidence becomes a card.

**Why:** The gap card is the unit everything later works on: the red team, certainty, scoring, the dossier and validation. A fixed structure forces each claim to say who is under-served, for which job, compared with what, measured how and in which setting (PICOS), and why the hole exists (the Robinson reason). Systematic reviewers characterise research gaps the same way, which keeps cards comparable with each other and checkable by a script.

**Inputs:** leads from D17–D19, coded evidence (`coding/codes-A.jsonl`, `evidence/ledger.jsonl`), `analysis/gapmap.json`, `evidence/why-now.jsonl`, `evidence/signals/`, `analysis/competitor_matrix.csv` and `gaps/variants.jsonl`.

**Procedure** (fill every field of gap-card.schema.json, one card per line)
1. Set the basics:
   - `gap_id`: GAP-NNN, sequential in your output
   - `title`: at most 100 characters, naming the job and the segment, with no product name
   - `status: candidate`
2. Write `statement` with the template: "Although [what is known: the incumbents and what they do], [what is missing, contradictory or untested] remains [unserved/unclear] for [segment], because [why existing supply can't answer it]. This matters because [the consequence, backed by evidence]."
3. Fill `picos`:
   - `population`: the segment
   - `intervention`: the job or category
   - `comparator`: incumbents and workarounds
   - `outcomes`: desired-outcome statements or O- codes
   - `setting`: platform, geography, language, company size
4. Fill `gap_type`:
   - `primary`: one of segment, non-consumption, price, quality, feature, integration, access, language, trust, synthesis
   - `secondary`: optional
   - `catalyst`: technology, regulation, behavior, platform, economic or none. Any catalyst other than none needs `why_now` ids.
5. Classify the gap:
   - `robinson_reason`: insufficient, biased, inconsistent or wrong-information
   - `sa_mode`: confusion, neglect, application or problematization
   - `egm_type`: absolute, synthesis or none, copied from the gap-map cell
   - `noncustomer_tier`: when one applies
6. List the links:
   - `codes`: the J-, O- and P- codes the gap rests on
   - `segment_codes`
   - `incumbents`: entity ids
   - `demand_signals`: series ids from `evidence/signals/`, when relevant
7. List the evidence:
   - `supporting_evidence`: verified EV ids that show this population's pain or demand for this job
   - `counter_evidence`: verified EV ids that argue against it (praise, contra records, products that serve it)
   
   An empty counter list usually means you didn't look. If the ledger truly holds none, say so in `why_empty`.
8. Write `why_empty`: your best evidence-based explanation of why no one serves this (too small, too hard, regulated, only recently possible, overlooked, blocked by a platform). The red team will test it.
9. Write `assumptions`: 1–5 entries, each typed desirability, viability or feasibility. Phrase each `riskiest_test` as an XYZ hypothesis ("At least X% of Y will Z") that the validation skill can pre-register.
10. Record provenance:
    - `origin_methods`: the cards that produced it (D16, D17, D18, D19)
    - `variant_of`: when it came from a variant
    - `errc`: when D18 applied
11. **Orchestrator:** run `gapscan.py cards check RUN`.

**Output:** `gaps/cards.jsonl` (from the synthesizer) and `gaps/card-check.json` (from the script).

**Metrics and checks** (`cards check`, with thresholds from `gap_card.*`)
- At least `min_records` (5) verified supporting records, from at least `min_domains` (3) domains, `min_source_types` (2) source types and `min_authors` (2) distinct authors.
- Triangulation (`require_triangulation`). A card needs all three:
  - pain: verified pain, wish, workaround or switch records
  - demand: a demand-signal series, a wtp or S4 record, or a job-post record
  - supply: incumbents with snapshots, or a gap-map cell that documents absence
- Every referenced EV id exists and is verified, and every WN id exists.
- Cards that fail are treated as `insufficient` downstream and counted in the PRISMA flow. Cards that pass go to the red team. Variants with no card are reported as discarded.

**Lenses (D26):** a card can claim any lens in `protocol.lenses`. Set `lens` (missing means gap), `opportunity_id` when it builds on a scan option, `base_entities` (the proven products) and `wedge` (what differs and why users would switch). For lenses other than gap, `cards check` accepts proven base products (top traction third, D27) as the demand leg and requires the base products to be verified for the supply leg; pain still needs verified records, and `why_empty` explains why the wedge or target is still open.

**Pitfalls**
- **Padding the evidence** with loosely related records. Each id must show this population's pain with this job.
- **Writing the solution into the statement.** The card describes the hole. Solutions belong to the validation skill's Opportunity Solution Tree.
- **Overlapping cards.** When two cards share most of their evidence, merge them, or make the difference (segment, setting) explicit in PICOS.

**Done when:** every lead with verified evidence is a card, and `cards check` has run on the current `gaps/cards.jsonl`.
