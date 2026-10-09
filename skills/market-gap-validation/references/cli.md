# gapval.py command reference

Contents
1. Conventions
2. The `next` loop
3. Pipeline steps
4. Commands
5. Validation folder layout

## 1. Conventions
- **How to run:** `python3 SKILL_DIR/scripts/gapval.py <command> ...`. SKILL_DIR is the folder holding this skill's SKILL.md.
- **RUN:** a run folder. It is normally the discovery run, and validation files live in `RUN/validation/`. For a standalone idea, `init RUN --idea TEXT` creates the folder.
- **Dependencies:** standard-library Python only.
- **Exit codes:** 0 ok, 1 usage or validation error, 2 blocked, 3 budget.
- **Who writes what:** agents write only the output paths named in their assignment. Scripts own everything else.

## 2. The `next` loop
`gapval.py next RUN` prints one action:
- `RUN gapval.py ...`
- `SPAWN <role> <n> <assignments>`
- `DO <card> <task>`
- `BLOCKED <HT-id>`
- `DONE`

NOTE lines give the phase, the reason and the full command. Outward actions (publishing pages, posting, emailing, ads, payments, recruiting, data exports) are always blocking human tasks, whatever the autonomy setting.

## 3. Pipeline steps
- **V1 Frame:** `assign --phase ost` → SPAWN designer → `ost check` (if it fails: `DO V01`) → `assumptions rank`.
- **V2 Design:**
  - `assign --phase design` → SPAWN designer (one draft Test Card per selected assumption).
  - `prereg freeze` for each card. If its checks fail: `DO V04`.
  - Then the experiment-plan approval: a blocking human task.
- **V3 Assets:** `assign --phase assets` → SPAWN builder → `assets check` for each experiment (if it fails: `DO V07`).
- **V4 Launch:**
  - `next` creates one blocking human task per `required_ht` slug of each frozen card, plus an "export results" task.
  - Landing-page experiments: once the deploy task is done, `DO V07` asks for `gapval.py utm` with the deployed URL.
  - A declined launch task closes the experiment as NOT_RUN.
- **V5 Collect:**
  - `ingest` each export the human saves at the path in the export task.
  - Interviews: `assign --phase interview-coding` → SPAWN coder A → `assign --phase interview-reliability` → SPAWN coder B → `agreement` → `themes`.
  - Then `stats --experiment EXP-NN`.
- **V6 Decide:** `verdict` → `assign --phase report` → SPAWN analyst → `validate`. Up to two analyst fix passes, then `DONE`.

## 4. Commands
**Setup and control**
- `init RUN [--handoff PATH] [--gap GAP-NNN] [--idea TEXT] [--autonomy autonomous|gated]`:
  - Default: read `RUN/output/handoff.json` and select the top-ranked opportunity, or the one given with `--gap`.
  - `--idea`: a standalone validation. Certainty starts at "Very low".
  - If the discovery codebook exists, it is copied to `validation/codebook.json`.
- `next RUN [--json]`, `status RUN [--json]`.
- `hq list|add|done|decline RUN ...`: the same human-task queue as discovery (`RUN/human-tasks.json`).

**Framing**
- `assign RUN --phase ost|design|assets|interview-coding|interview-reliability|report`
- `ost check RUN`:
  - schema check
  - at least 3 genuinely different solutions
  - assumption ids unique across the tree
  - the target solution has at least one desirability and one viability assumption
- `assumptions rank RUN`:
  - risk = importance × (5 − evidence); ties broken by ICE.
  - The top `assumptions.experiments_per_round` assumptions are selected.
  - Assumptions with importance ≥ `assumptions.critical_importance_min` are critical.

**Pre-registration**
- `samplesize --p P --h H [--z 1.96]`: n = ⌈z²·p(1−p)/h²⌉. For example, p 0.10 with h 0.05 gives 139.
- `prereg new RUN --experiment EXP-NN --type TYPE --assumption A1[,A2]`: draft card with the default rule and evidence level for TYPE:

  | TYPE | Rule | Evidence level |
  |---|---|---|
  | smoke-test | wilson | email |
  | fake-door | wilson | click |
  | loi | wilson | loi |
  | presale | wilson | presale |
  | concierge | wilson | call |
  | problem-interviews, switch-interviews | themes | interview |
  | odi-survey | odi | survey |
  | kano-survey | kano | survey |
  | pricing-survey | van-westendorp | survey |
  | tech-spike, search-demand | criteria | prototype or desk |

- `prereg check RUN EXP-NN`: the schema plus these methodology rules:
  - kill_threshold ≤ success_threshold.
  - xyz.x = success_threshold for the wilson, themes and ellis rules.
  - Web experiments: min_n ≥ the sample size computed from planning_p and half_width, and ≥ `stats.min_visitors_floor`.
  - Interviews: min_n ≥ `interviews.min_interviews` and `criteria.problem_codes` is set.
  - The criteria that the odi, kano, van-westendorp and criteria rules require are present.
  - Survey sizes below the minimums are allowed with a warning (labelled directional).
  - Money or a budget requires a payment human task.
  - A pivot action requires a `pivot_hypothesis`.
- `prereg freeze RUN EXP-NN`: run the checks, then sha256-lock the card. Its status field is excluded from the hash.
- `prereg verify RUN`: re-hash every frozen card. Edited cards are reported as TAMPERED.

**Assets**
- `utm RUN --experiment EXP-NN --base-url URL --channels a,b,c`: one tagged link per channel, written to `validation/assets/EXP-NN/utm.json`.
- `assets check RUN EXP-NN`: the required files exist (landing.html, privacy.md, posts.md, survey.md, interview-guide.md or plan.md, depending on type). `landing.html` must have:
  - `id="disclosure"`, `id="consent"`, a privacy link and `data-experiment="EXP-NN"`
  - no unfilled `{{placeholders}}`
  - no fabricated social proof (testimonials, "trusted by", "join 1,000", star ratings)
  - no payment fields unless the evidence level is presale or deposit, in which case explicit charge, authorisation or refund wording is required

**Data and analysis**
- `ingest RUN --experiment EXP-NN --kind KIND --file PATH`. KIND and its CSV columns:
  - `visits`: channel, visitors
  - `signups`: channel, signups
  - `clicks`: channel, clicks, visitors
  - `loi` or `presale`: count, contacted
  - `survey-odi`: respondent, outcome, importance, satisfaction (1–5)
  - `survey-kano`: respondent, feature, functional, dysfunctional (L/M/N/W/D or like/must-be/neutral/live-with/dislike)
  - `survey-vw`: respondent, too_cheap, cheap, expensive, too_expensive, and optionally likely_cheap and likely_expensive (1–5)
  - `ellis`: respondent, answer (very / somewhat / not / na)
  - `spike`: test, passed (true/false)
  - `interviews`: a folder of `.txt` transcripts, which become `IV-NNNNNN` records
  
  Rejected exports:
  - columns with personal data (email, name, phone, address, ip)
  - email addresses or phone numbers anywhere in the data
  - negative or fractional counts
  - more successes than the denominator
- `stats RUN --experiment EXP-NN`: apply the frozen rule and write `validation/results/EXP-NN.json`.
  - **wilson:** PASS if the lower bound ≥ success_threshold; FAIL if the upper bound < kill_threshold; otherwise INCONCLUSIVE, which includes any n below min_n. Reported per channel and pooled.
  - **themes:** the share of coded interviews that carry a problem code, judged by the Wilson rule. Guest–Namey–Chen saturation is also reported.
  - **odi:** PASS if every target outcome reaches `criteria.min_opportunity` (default 10).
  - **kano:** PASS if every target feature falls in `criteria.pass_categories`.
  - **van-westendorp:** PASS if the planned price is within PMC–PME.
  - **ellis:** the very-disappointed share against 0.40, with a Wilson interval.
  - **criteria:** every acceptance test passed.
  - Survey results below the configured minimum sizes are marked directional.
- `agreement RUN`: Krippendorff's α per code on interview coding. `themes RUN`: interview saturation (base 4, run 2, ≤5% new).
- `verdict RUN`: computed deterministically.
  - **Assumption status:**
    - validated: desirability at evidence level ≥ email; viability at ≥ loi, or a non-directional Van Westendorp pass; feasibility by any pass
    - supported: passed, but only with weaker evidence
    - invalidated
    - inconclusive (includes conflicting or tampered results)
    - untested
  - **Verdict:** each invalidated critical assumption contributes its card's pre-registered `on_fail` action. The most conservative wins: KILL > PIVOT > ITERATE.
  - **GO:** requires every critical desirability and viability assumption to be validated.
  - **Otherwise:** ITERATE.
  - **Demand strength:** strong for a deposit or pre-sale pass; moderate for email, call or LOI; otherwise weak.
- `validate RUN`: schema checks for the OST, Test Cards, Learning Cards and validated handoff, plus the tamper check. Also checks that the validated handoff and report agree with `verdict.json`, and that every analysed experiment has a Learning Card.

## 5. Validation folder layout
```
RUN/human-tasks.json  (shared with discovery)
RUN/validation/
  state.json  events.jsonl  opportunity.json  codebook.json  ost-assign.json  ost.json  assumptions-ranked.json
  design-assign-NN.json  prereg/EXP-NN.json  prereg/EXP-NN.lock.json
  assets-assign-NN.json  assets/EXP-NN/{landing.html, privacy.md, posts.md, survey.md, interview-guide.md, plan.md, utm.json, assets-check.json}
  data/EXP-NN/{visits.csv, signups.csv, ..., interviews/, interviews.jsonl, coding-assign-A.json, codes-A.jsonl,
                reliability-sample.jsonl, coding-assign-B.json, codes-B.jsonl, <kind>.json}
  results/EXP-NN.json  agreement.json  themes.json  verdict.json  validate-check.json
  report-assign-NN.json  learning-cards/EXP-NN.json  report.md  validated-handoff.json
```
