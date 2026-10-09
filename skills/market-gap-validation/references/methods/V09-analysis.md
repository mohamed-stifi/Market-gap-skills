# V09 · Analysis

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Wilson score interval (Wilson 1927); ODI scoring (Ulwick); Kano coefficients (Berger et al. 1993); Van Westendorp + Newton–Miller–Smith; thematic saturation (Guest, Namey & Chen 2020); pre-registration practice (no peeking, no post-hoc thresholds) | V5 Collect | orchestrator (ingest, stats), analyst (interpretation) | core |

**Use when:** a running experiment has reached its `min_n` or its `duration_days`, or was stopped at its `exposure_limit`, and the human has delivered the data exports.

**Why:** The decision was made before the data arrived, so analysis means *applying* the frozen rule, not finding a story. Scripts compute every number. The analyst explains what the numbers mean and what they do not mean: which channels behaved differently, which results are directional because of a small n, and what the next test should be.

**Inputs:**
- frozen cards and their lock files in `validation/prereg/`
- data exports in `validation/data/EXP-NN/` (pseudonymous)
- for interviews: coded files plus `validation/agreement.json` and `validation/themes.json`

**Procedure**
1. **Data hygiene (human, then orchestrator).** Exports must hold pseudonymous respondent ids and counts only. `gapval.py ingest` rejects personal-data columns (email, name, phone, address, ip), any email address, negative or fractional counts, and successes above their denominator; transcripts with emails or phone numbers are rejected too. Keep the original exports in the human's tools; the run folder holds only the files named in the export task.
2. **Ingest.** When the export sits at the path named in the experiment's export task, `gapval.py next` runs `gapval.py ingest RUN --experiment EXP-NN --kind KIND --file PATH`. The kinds and columns are listed in `references/cli.md`:
   - `visits`, `signups`, `clicks`, `loi`, `presale`
   - `survey-odi`, `survey-kano`, `survey-vw`
   - `ellis` (answers very, somewhat, not or na)
   - `spike` (test, passed), for tech spikes and search-demand checks
   - `interviews` (a folder of `.txt` transcripts)
3. **Tamper check.** Run `gapval.py prereg verify RUN`. A card that fails verification is analysed as TAMPERED and cannot validate anything.
4. **Compute.** Run `gapval.py stats RUN --experiment EXP-NN`. It writes `validation/results/EXP-NN.json`:
   - Wilson PASS/FAIL/INCONCLUSIVE per channel and pooled
   - or the ODI table
   - or Kano categories with Better and Worse
   - or Van Westendorp PMC, OPP, IPP, PME and the NMS optimum
   - or the interview-share result
   - or the acceptance-test results of a spike (`criteria`: PASS when every test passed, FAIL when one failed, INCONCLUSIVE when one has no result)
   
   Samples below `min_n` come back INCONCLUSIVE, and that is the correct answer.
5. **Interpret (analyst).** For each result, write down:
   - the frozen rule
   - the observed numbers with their intervals
   - the result
   - one sentence on what it means for the assumption
   
   Use the worked reading as a model: 20 sign-ups from 100 visitors gives Wilson 13.3–28.9%. That is a PASS against X = 10%, because the lower bound is above 10%. Against X = 15% it is INCONCLUSIVE, because the interval straddles 15%.
6. **Channels and subgroups.** Report per-channel intervals side by side. A channel that clearly beats the pool is a **hypothesis** for the next card (a possible PIVOT to that segment or channel), not a retroactive PASS. The same goes for any segment you only defined after seeing the data.
7. **Directional labels.** `stats` sets `directional` on survey results when n is below `surveys.odi_min_n`, `surveys.kano_min_n` or `surveys.vw_min_n`; report that label with the result. Mark interview results as unsaturated when the Guest–Namey–Chen test in the result has not passed.

**Output:** `validation/results/EXP-NN.json` from the scripts, plus the analyst's interpretation notes. Those notes go into the Learning Cards in V10; they are not a separate file.

**Metrics and checks**
- The Wilson formula and the survey formulas are computed only by `gapval.py stats`. Never recompute them by hand or in another tool.
- Every number quoted in the report must appear in a results file.

**Pitfalls**
- **Peeking.** Running `stats` daily and stopping at the first PASS inflates false positives. Wait for `min_n` or `duration_days`.
- **Subgroup fishing.** Slicing the data until something passes. Post-hoc segments are hypotheses.
- **Reading INCONCLUSIVE as "almost passed".** It means the data cannot tell. The card's `on_inconclusive` action decides what happens next.
- **Silent exclusions.** Dropping respondents or traffic without a rule. Apply only the consistency filters the methods define (Van Westendorp ordering, bot filtering noted in the export) and note them.

**Done when:** every experiment that ran has a results file. Its status is analysed, or closed with the reason recorded.
