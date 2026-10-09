# V10 · Decision, Learning Cards and validated handoff

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Learning Card (Strategyzer); evidence strength (Bland & Osterwalder); pre-registered decision rules; product-market-fit survey (Sean Ellis) and the PMF engine (Vohra, Superhuman) for the post-launch watchlist | V6 Decide | orchestrator (verdict), analyst (cards, report, handoff) | core |

**Use when:** every frozen experiment of the round is analysed or closed.

**Why:** A verdict that depends on mood is not a verdict. The rules were fixed in advance: each card's thresholds and its `on_pass`, `on_fail` and `on_inconclusive` actions. Now `gapval.py verdict` applies them deterministically. The analyst then records what was learned, so that a build, launch or monitor agent can continue without re-reading the whole run.

**Inputs:** `validation/results/EXP-NN.json`, the frozen cards, `validation/ost.json`, `validation/assumptions-ranked.json`, `validation/opportunity.json`, and defaults `verdict.*`, `evidence_ladder`, `demand_strength` and `surveys.ellis_*`.

**Procedure**
1. **Verdict (orchestrator).** Run `gapval.py verdict RUN`. It writes `validation/verdict.json`. Each assumption of the target solution gets one status:
   - **validated**: an experiment passed at a strong enough evidence level, and none failed:
     - desirability needs at least `verdict.desirability_min_level` (email)
     - viability needs at least `verdict.viability_min_level` (LOI), or a non-directional Van Westendorp pass (the planned price inside PMC–PME, n ≥ `surveys.vw_min_n`)
     - feasibility: any pass, such as a tech spike
   - **supported**: it passed, but only with weaker evidence (clicks, interviews, surveys, desk). Escalate to a stronger test.
   - **invalidated**: an experiment failed.
   - **inconclusive**: only inconclusive results, or conflicting PASS and FAIL, or a TAMPERED card.
   - **untested**: no experiment ran.
   
   An assumption is critical when its importance is at least `assumptions.critical_importance_min` (4). The round verdict:
   - Each invalidated critical assumption contributes its failing card's `on_fail` action: kill → **KILL**, pivot → **PIVOT** (the next round uses the card's `pivot_hypothesis` and the other solutions in the tree), iterate → **ITERATE**. When they disagree, the most conservative wins: KILL > PIVOT > ITERATE.
   - Otherwise **GO** when every critical desirability and viability assumption is validated (at least one of each must be critical).
   - Otherwise **ITERATE**: critical assumptions are still supported, inconclusive or untested.
2. **Never override the verdict.** If you disagree, the disagreement goes into the report's limitations and becomes a new card for the next round.
3. **Learning Cards (analyst).** Write one per experiment in `validation/learning-cards/EXP-NN.json` (schema `learning-card`):
   - `we_believed`: from the card's `we_believe`
   - `we_observed`: the numbers with their intervals
   - `we_learned`: what this says about the assumption
   - `therefore`: the pre-registered action, made concrete
   - `result` and `evidence_level`, plus the key figures in `numbers`
4. **Report (analyst).** Write `validation/report.md`:
   - the verdict and its reasons in one paragraph
   - a table of assumptions and their statuses
   - a table of experiments with their intervals and results
   - what we learned
   - limitations: sample sizes, channel bias, directional surveys, and discovery evidence capped at weak
   - next steps
5. **Demand strength.** `gapval.py verdict` computes it from the strongest evidence level among passing experiments; copy it from `verdict.json`, never upgrade it:
   - **strong**: a deposit or pre-sale experiment passed
   - **moderate**: an email, booked-call or LOI experiment passed
   - **weak**: otherwise (desk, prototype, interviews, surveys, clicks)
6. **Validated handoff (analyst).** Write `validation/validated-handoff.json` (schema `validated-handoff`):
   - verdict and reasons, exactly as in `verdict.json`
   - assumption statuses
   - experiment results with their stats, exactly as in `verdict.json` (an experiment still PENDING there is written as NOT_RUN)
   - `demand_strength`
   - `validated_icp`: who actually converted, and through which channels
   - `price`: the planned price, the Van Westendorp range and the NMS optimum if measured
   - `channels`: per-channel conversion with intervals
   - `mvp`: scope plus the feasibility assumptions not yet validated by a tech spike, as build spikes
   - `next_steps`
   - `watchlist`
   
   Then the orchestrator runs `gapval.py validate RUN`.
7. **Post-launch PMF watchlist.** Add a Sean Ellis survey plan to `watchlist` for the future monitor skill. It runs after launch, not during validation:
   - Question: "How would you feel if you could no longer use [product]?" Answers: very disappointed / somewhat disappointed / not disappointed / N/A – no longer use.
   - PMF% = very ÷ (responses − N/A), compared with `surveys.ellis_threshold` (40%), with a Wilson interval and at least `surveys.ellis_min_n` (40) responses.
   - Survey users who have used the core product at least twice, including in the last two weeks.
   - Vohra's segmentation:
     1. Build the high-expectation customer profile from the "very disappointed" respondents.
     2. Among the "somewhat disappointed", keep those whose main benefit matches yours, and fix what holds them back.
     3. Politely ignore the rest.

**Output:** `validation/verdict.json`, `validation/learning-cards/EXP-NN.json`, `validation/report.md`, `validation/validated-handoff.json`.

**Metrics and checks:** `gapval.py validate RUN` checks:
- every artifact against its schema, and every frozen card against its hash
- that the validated handoff's verdict, demand strength and experiment results equal `verdict.json`
- that every analysed experiment has a Learning Card
- that `report.md` states the verdict and contains no email address

Every number in the report and the handoff must also match a results file; that part is your responsibility.

**Pitfalls**
- **GO on opinions.** Interviews, ODI and Kano surveys never validate viability. Only LOI-level evidence or a non-directional Van Westendorp pass does.
- **Hiding failures.** Every experiment appears in the report, including FAIL, INCONCLUSIVE and TAMPERED results.
- **Forgetting the pivot material.** A PIVOT names the next target (segment, channel or solution) and the cards to write next.
- **Leaking personal data into the handoff.** Only aggregates and pseudonymous ids belong there.

**Done when:** `gapval.py validate RUN` passes and `gapval.py next RUN` returns `DONE`.
