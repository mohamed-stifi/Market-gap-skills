# D14 · Double coding and reliability

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Doctoral practice of independent double screening and coding; inter-rater reliability in qualitative research (O'Connor & Joffe 2020); Krippendorff's alpha (Krippendorff 2004); Cohen's kappa with Landis & Koch bands; thematic saturation (Guest, Namey & Chen 2020) | P4 Coding | coder (A and B), orchestrator | core |

**Use when:**
- after `codebook freeze`: close-code all verified records
- after every later evidence round: code the new records
- after each codebook revision: recode the reliability sample

**Why:** One reader's labels are opinions. When two independent coders reach the same labels, that shows the codebook produced them, not the coder. It's the same reason doctoral teams code in pairs. Reliability is measured per code because a single pooled number hides weak codes, and a gap built on a code nobody can apply consistently is not evidence. Theme saturation then answers the second question: have we heard all the distinct needs, or would more evidence reveal new ones?

**Inputs**
- The frozen `coding/codebook.vN.json`. Its version and hash are in `coding/codebook.lock.json`.
- Closed-coding assignments `coding/closed-assign-*.json`, listing verified record ids.
- `coding/reliability-assign-vN.json` (and top-ups `-t1`, `-t2`, …), made in two steps:
  1. A random core of `coding.reliability_fraction` (20%) of coded records, at least `coding.reliability_min_units` (30).
  2. A stratified top-up. Every **eligible code** (one coder A applied at least `coding.min_positives_per_code` (5) times) gets 5 positives and 5 negatives in the double-coded set, rarest codes first.
  
  A random sample alone measures only common codes: in a live run it covered 3 of 38 eligible codes. Krippendorff sizes reliability data by the least frequent category.
- The miner's strength grade is withheld from both coders, so the coders' grades are independent ratings.
- Records the frozen codebook cites, as examples or in its notes, are held out of the reliability sample and the α computation. A coder recognises them, so agreement on them would be inflated. Reliability is measured on units not used to build the instrument.
- The records in `evidence/ledger.jsonl`. Open a record's snapshot text when its quote is ambiguous.

**Procedure**
1. **Coder A (closed coding).** For every record id in your assignment, write one line to the output file named in the assignment, following code-assignment.schema.json:
   - `evidence_id`, `coder` "A", `codebook_version`
   - `codes`: every code that applies (multi-label)
   - `strength`: S0–S4, re-graded from the quote itself per D10
   - `outcome_statement`: when the record implies a desired outcome
   - `intensity`, by these anchors:
     - 1: a minor annoyance, or no pain at all (praise, contra and vendor or pricing records)
     - 2: a recurring cost in time or money
     - 3: severe, meaning lost money or clients, or blocked work
   - `new_code_proposals`: label + definition, for anything the codebook can't hold
2. Apply only the frozen version. If a record fits no code, leave its codes empty and add a proposal, rather than forcing the nearest code.
3. **Coder B (reliability).** Code only the records in your assignment, with the same codebook and the same fields, without opening `coding/codes-A.jsonl` or any other coder's file. Independence is the whole point: if B has seen A's codes, α measures copying.
4. **Orchestrator.** After `gapscan.py merge RUN --phase coding`, run `gapscan.py agreement RUN`. It builds a records × codes 0/1 matrix for each coder over the overlap, then computes:
   - Krippendorff's α (nominal) per code
   - Cohen's κ with its Landis–Koch band
   - α on the strength grades, coder A vs B
   - α and κ on strength, miner vs coder A, over every coded record
5. Read the verdict in `coding/agreement.json`:
   - **insufficient**: some eligible codes still lack 5 double-coded positives. `next` issues `assign --phase coding-reliability` again, and coder B codes only the records the top-up adds.
   - **accept**: every eligible code has α ≥ 0.80 (`coding.alpha_accept`).
   - **provisional**: no code is below 0.667 (`coding.alpha_provisional`), but some are between 0.667 and 0.80. Continue; D22 downgrades gap cards that rest on provisional codes.
   - **revise**: at least one code is below 0.667. `next` issues `assign --phase coding-open --revise`. Coder A revises (D13 step 10), the orchestrator re-freezes, and both coders recode the sample. Allow at most `coding.max_revisions` (3) cycles; after that, weak codes are carried as provisional and flagged.
6. A code with fewer than 5 positives in the whole ledger is **not assessable**: α is unstable for rare codes, and such a code cannot meet the gap-card thresholds anyway. Report it but don't judge it.
   - A **constant code**, applied to every record, has undefined α (no variation) and cannot separate records. It is listed but never blocks the verdict.
   - An eligible code that still can't be measured is **provisional**, never silently accepted.
7. Run `gapscan.py themes RUN` after every coding merge. Records are the sampling units and the run's own codes, plus accepted proposals, are the species (incidence data). The standard X-, F- and T- codes are left out because they exist by construction. Themes are saturated when both checks hold:
   - theme coverage Ĉ over records × codes reaches `coding.theme_coverage_target` (0.95)
   - the Guest–Namey–Chen run test, in collection order, passes. The base is the first `coding.gnc_base` (20) records and the run is the next `coding.gnc_run` (10). The new-information share (new themes in the run ÷ themes in the base) must be ≤ `coding.gnc_threshold` (0.05). These sizes adapt Guest et al.'s interview defaults (base 4, run 2) to short desk posts; report them as an adaptation.
8. If themes are unsaturated and evidence rounds remain (`evidence.max_rounds`), `next` returns to P3. The new round targets the channels and segments that produced singleton codes. New records are coded with the current frozen codebook, and new-code proposals from that round count as new themes.

**Output**
- `coding/codes-A.jsonl` and `coding/codes-B.jsonl`
- `coding/agreement.json`: per-code α, κ, band, positives and the verdict
- `coding/themes.json`: Ĉ, an estimate of the total number of themes, the Guest–Namey–Chen base, run and share, and saturated yes/no

**Metrics and checks** (formulas in `references/metrics.md`)
- α for one binary code with two coders: α = 1 − (n − 1)·o₀₁ / (n₀·n₁), where o₀₁ counts disagreeing pairs and n₀, n₁ are the pooled counts of 0 and 1 values.
- κ = (p_o − p_e) / (1 − p_e). Landis–Koch bands: below 0 none, .00–.20 slight, .21–.40 fair, .41–.60 moderate, .61–.80 substantial, .81–1 almost perfect.
- Theme coverage uses the same Ĉ formula as landscape saturation (D04), with records as the units.

**Pitfalls**
- **Coder B reading A's codes, or the orchestrator "fixing" disagreements by hand.** Disagreements are data for the revision; never overwrite either file.
- **Lowering thresholds to pass.** Thresholds are protocol constants. Change one only with `protocol amend` and a reason; the change then appears in the dossier.
- **Judging rare codes.** A code with 2 positives can show α = 0 or 1 by chance.
- **Treating saturation as truth.** Coverage says how unlikely new themes are in the channels you sampled. It says nothing about segments no channel reaches.

**Done when:**
- agreement is accept or provisional (or max revisions were reached, with the weak codes flagged), and
- themes are saturated, or evidence rounds are exhausted and that is recorded as a limitation, and
- `next` has moved on to supply mapping.
