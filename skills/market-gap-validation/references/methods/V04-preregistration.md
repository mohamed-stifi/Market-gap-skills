# V04 · Pre-registration (Test Card, XYZ, sample size, decision rule)

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Pre-registration and registered reports (research practice); Test Card (Strategyzer); XYZ hypothesis (Savoia, *The Right It*); normal-approximation sample size; Wilson score interval (Wilson 1927) | V2 Design | designer (drafts), orchestrator (freezes) | core |

**Use when:** before any data is collected, for every experiment.

**Why:** Thresholds chosen after you see the data move with your hopes ("12% is pretty good, actually"). Pre-registration writes down, before launch, exactly what you believe, whom you will measure, what number makes you right, how many observations you need, and what you will do in each outcome. Then a hash freezes it. The result becomes binding: a PASS earned this way means something, and so does a FAIL.

**Inputs:** the draft card from `gapval.py prereg new`, `validation/opportunity.json` (pricing hypothesis, sizing, ICP, channels), `validation/ost.json`, and defaults `stats.*` and `surveys.*`.

**Procedure**
1. **Hypothesis.** Fill the four Test Card lines: `we_believe` (the assumption), `to_verify` (what you will do), `measure` (the metric), `right_if` (the success condition in words).
2. **XYZ.** Write "At least **X**% of **Y** will **Z**":
   - **Y** is a specific population you can actually reach. For example: "freelance translators who arrive from our post in the translators' community".
   - **Z** is a specific behaviour. For example: "submit the waitlist form with the consent box ticked".
   
   Copy them into `xyz.x`, `xyz.y` and `xyz.z`, and mirror Z in `metric` (`name`, `numerator`, `denominator`). For the `wilson`, `themes` and `ellis` rules, `xyz.x` must equal `success_threshold`; `prereg check` rejects a mismatch.
3. **Derive X from unit economics** in `x_derivation`, never from benchmarks. A worked example:
   - Year-1 goal from sizing: 20 paying customers in the first quarter.
   - The planned channels reach about 2,000 ICP visitors in that quarter.
   - The pricing hypothesis assumes 10% of waitlist sign-ups convert to paid. This is an assumption, and it gets its own card later.
   - Sign-ups needed: 20 ÷ 0.10 = 200. So X = 200 ÷ 2,000 = **10%**.
   - Set `success_threshold` = 0.10 and `xyz.x` = 0.10.
   
   Unbounce's 2024 landing-page medians (6.6% across industries, 3.8% for SaaS) are context only: they describe other people's pages and traffic, not your break-even point.
4. **Kill threshold.** Set `kill_threshold` (≤ `success_threshold`; `prereg check` rejects a higher one) to the rate below which the model cannot work even with optimistic assumptions. For example, half of X. For proportion metrics (`decision_rule: wilson`, `themes`, `ellis`):
   - **PASS** if the Wilson 95% lower bound ≥ `success_threshold`.
   - **FAIL** if the upper bound < `kill_threshold`.
   - **INCONCLUSIVE** otherwise, and whenever n is below `min_n`.
   
   Setting both thresholds to X gives Savoia's single-bar test.
5. **Sample size.** Run `gapval.py samplesize --p P --h H`, where `planning_p` is the rate you expect and `half_width` the precision you need (default `stats.planning_half_width` 0.05). The formula is n = ⌈z²·p(1−p)/h²⌉: 10% ± 5 points needs 139; 5% ± 3 points needs 203. Then set `min_n`:
   - web experiments (evidence level `click` or `email`): fill `planning_p` and `half_width`; `min_n` must be at least the computed n and at least `stats.min_visitors_floor` (100)
   - interviews (`themes`): at least `interviews.min_interviews` (10)
   - surveys: the survey minimum (`odi_min_n` 180, `kano_min_n` 200, `vw_min_n` 100). A smaller `min_n` passes with a warning, and the result is labelled directional.
6. **Check that you can win.** With n = 139, an observed 10% gives a Wilson interval of 6.0–16.1%, so a true rate *at* X ends INCONCLUSIVE. Clearing a 10% bar at n = 139 needs about 21 sign-ups (15.1%). If your honest expectation sits near X, raise `min_n`, or accept that INCONCLUSIVE is the likely outcome and say so in `right_if`.
7. **Typed criteria for the other rules.** Rules whose metric is not a 0–1 share read the `criteria` object; restate the same criteria in words in `right_if`:
   - `odi`: `criteria.outcomes` (outcome codes to test) and `criteria.min_opportunity` (default 10). PASS when every target outcome reaches it.
   - `kano`: `criteria.features` and `criteria.pass_categories` (for example `["A", "O", "M"]`). PASS when every target feature falls in those categories without a tie.
   - `van-westendorp`: `criteria.price_point_month_usd`, the planned price (the card-level `price_point_month_usd` is the fallback). PASS when it lies within PMC–PME.
   - `themes`: `criteria.problem_codes`, the codes that count as "has the problem". The thresholds are shares of coded interviews, judged by the Wilson rule (step 4).
   - `criteria` (`tech-spike`, `search-demand`): `criteria.acceptance_tests`, each one checkable as pass or fail.
   
   The `odi`, `kano`, `van-westendorp` and `criteria` rules do not use `success_threshold` or `kill_threshold`; leave both at 0.
8. **Logistics.** Fill these fields:
   - `duration_days`
   - `budget_usd` (0 if nothing is spent)
   - `channels`: one entry per traffic or respondent source; each gets its own UTM link.
   - `ethics`: every flag true, plus an `exposure_limit` such as "at most 500 visitors or 14 days, whichever comes first".
   - `required_ht`: short slugs for the human operations the test needs, in the order the human should do them, for example `deploy-landing`, `form-backend`, `analytics`, `post:translators-forum`, `ad-budget-50usd`. For landing-page tests the deploy slug comes first, so the UTM links exist before anything is posted. `gapval.py next` turns each slug into a blocking human task, typed by its words (V08), and adds an "export results" task. Money-taking cards (`presale`, `deposit`) and any `budget_usd` above 0 need a payment slug (containing `stripe`, `payment`, `presale`, `deposit`, `ads` or `budget`).
9. **Pre-commit the actions.** Set `on_pass` (continue, go, scale-test), `on_fail` (kill, pivot, iterate) and `on_inconclusive` (extend, iterate, kill). When `on_fail` is `pivot`, write `pivot_hypothesis`, for example "same job, agencies instead of freelancers".
10. **Freeze.** The orchestrator runs `gapval.py prereg check RUN EXP-NN`, fixes any issues with you, then runs `gapval.py prereg freeze RUN EXP-NN`. Any later edit makes `gapval.py prereg verify RUN` fail, and the experiment is reported as TAMPERED. Once every card is frozen, `gapval.py next` asks the human to approve the whole plan (V08).

**Output:** a frozen `validation/prereg/EXP-NN.json` plus `validation/prereg/EXP-NN.lock.json`.

**Metrics and checks**
- `prereg check` requires:
  - assumption and solution ids that exist in `validation/ost.json`
  - `kill_threshold` ≤ `success_threshold`, both between 0 and 1, and `xyz.x` = `success_threshold` for `wilson`, `themes` and `ellis`
  - for web experiments: `planning_p` and `half_width`, and `min_n` ≥ the computed sample size and ≥ 100
  - for `themes`: `min_n` ≥ 10 and `criteria.problem_codes`; for the other rules, the `criteria` fields in step 7
  - channels for smoke tests and fake doors, a payment slug for money or budget, and a `pivot_hypothesis` when `on_fail` is `pivot`
  - an `x_derivation` of at least 20 characters, every ethics flag true, and all three actions defined
- Survey sizes below the minimums produce a warning, not an error, and the results are labelled directional.
- No peeking. Do not run `gapval.py stats` before `min_n` is reached or `duration_days` has passed. The only allowed interim look is a stop for harm or budget, recorded as a human task.

**Pitfalls**
- **X from a blog post.** A benchmark is not your break-even point.
- **A vague Y or Z.** "People" and "show interest" cannot fail.
- **Editing after the freeze.** It voids the experiment. Write a new card (EXP-NN+1) instead.
- **One pooled channel.** Without a UTM per channel, a great community and a dead ad campaign average into "meh".
- **An undersized test.** It produces INCONCLUSIVE, then a temptation to "extend a little". Size it right before launch.

**Done when:** every selected experiment's card is frozen and `gapval.py prereg verify RUN` passes.
