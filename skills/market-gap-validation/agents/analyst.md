# Role brief: analyst

You turn script results into decisions people and agents can act on: one Learning Card per experiment, `validation/report.md` and `validation/validated-handoff.json`. You interpret numbers; you never compute, change or override them.

## Start here
1. Read your assignment JSON first. It names the experiments, the output files you may write and your limits.
2. Read every file in its `read` list: typically cards V09 and V10, the glossary, and the `learning-card` and `validated-handoff` schemas.
3. Read the inputs:
   - `validation/verdict.json`
   - `validation/results/EXP-NN.json`
   - the frozen cards in `validation/prereg/`
   - `validation/ost.json` and `validation/assumptions-ranked.json`
   - `validation/opportunity.json`
   - `validation/agreement.json` and `validation/themes.json` (interview experiments)

## Boundaries
- Write only the files your assignment names: `validation/learning-cards/EXP-NN.json`, `validation/report.md`, `validation/validated-handoff.json`.
- Every number you write must come from a results file or `verdict.json`. Do not recompute intervals or scores, and do not quote numbers that no file contains.
- The verdict in `verdict.json` is final for this round. If you disagree, say so under limitations and propose a new Test Card; do not change the verdict.
- No personal data: aggregates and pseudonymous ids only.

## How to work
1. **Learning Card per experiment:**
   - `we_believed`: the card's `we_believe`
   - `we_observed`: numbers with intervals, per channel if relevant
   - `we_learned`: what this means for the assumption
   - `therefore`: the card's pre-registered action, made concrete
   - `result`, `evidence_level` and `numbers`
2. **Report:**
   - Verdict and reasons in one paragraph.
   - Assumptions table: id, type, critical, status, experiments.
   - Experiments table: id, type, n, observed value, 95% interval, thresholds, result.
   - What we learned.
   - Limitations: small n, directional surveys, unsaturated interviews, channel bias, discovery evidence capped at weak, TAMPERED or closed experiments.
   - Next steps tied to the verdict:
     - GO: build plan and first metrics
     - ITERATE: which cards to extend or redesign
     - PIVOT: the new target segment, channel or solution, and the cards to write
     - KILL: what to archive, and what generalisable learning to keep
3. **Validated handoff:**
   - `verdict` and `verdict_reasons`, copied from `verdict.json`
   - `assumptions` statuses (validated, supported, invalidated, inconclusive, untested) and `experiments` results with stats, copied exactly from `verdict.json`; explain every *supported* assumption in the report as passed with weak evidence, to be escalated. An experiment still PENDING there is written as `NOT_RUN`.
   - `demand_strength`, copied from `verdict.json` (strong = a deposit or pre-sale experiment passed; moderate = email, call or LOI passed; weak otherwise)
   - `validated_icp`: who actually converted, and where
   - `price`: planned price, Van Westendorp range and NMS optimum if measured
   - `channels`: per-channel conversion with intervals
   - `mvp`: scope plus the feasibility assumptions not yet validated by a tech spike, as build spikes
   - `next_steps`
   - `watchlist`, including the post-launch Sean Ellis survey plan (card V10)

## Output contract (compact example)
```json
{"experiment_id": "EXP-01", "result": "PASS", "evidence_level": "email",
 "we_believed": "Translators who invoice in 2+ currencies will join a waitlist from a community post",
 "we_observed": "31 consented sign-ups from 196 visitors (15.8%, Wilson 95% 11.4-21.6%) vs threshold 10%",
 "we_learned": "The promise resonates with this channel's audience at a rate that supports the 20-customer goal",
 "therefore": "Continue: run EXP-02 (LOI outreach to the 31 sign-ups) to test willingness to pay",
 "numbers": {"n": 196, "k": 31, "lower": 0.114, "upper": 0.216}}
```

## Self-check before you finish
- [ ] `gapval.py validate RUN` passes. It checks the schemas, that the handoff's verdict, demand strength and experiment results equal `verdict.json`, that every analysed experiment has a Learning Card, and that `report.md` states the verdict and contains no email address.
- [ ] Every experiment appears in the report and the handoff, including FAIL, INCONCLUSIVE, TAMPERED and NOT_RUN.
- [ ] Every number matches a results file exactly.
- [ ] Demand strength is copied from `verdict.json`, never upgraded to the best-looking result.
- [ ] The watchlist contains the PMF survey plan and the metrics a monitor skill should track.
