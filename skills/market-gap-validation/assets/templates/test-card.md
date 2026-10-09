# Test Card — {{EXPERIMENT_ID}}

Human-readable mirror of `validation/prereg/{{EXPERIMENT_ID}}.json` (schema `test-card`, cards V03–V04). The JSON file is the source of truth: fill it with `gapval.py prereg new` and check it with `gapval.py prereg check`. Use this page to review the card with the human before `gapval.py prereg freeze`. After the freeze, nothing changes; a new idea becomes a new card.

| Field | Value |
|---|---|
| Experiment (`id`) | {{EXPERIMENT_ID}} |
| Tests assumption(s) (`assumption_ids`) | {{ASSUMPTION_IDS}} |
| Solution (`solution_id`) | {{SOLUTION_ID}} |
| Type (`type`) | {{TYPE}} |
| Evidence level (`evidence_level`) | {{EVIDENCE_LEVEL}} |

## Hypothesis (Strategyzer Test Card)
- **We believe that** (`hypothesis.we_believe`): {{WE_BELIEVE}}
- **To verify that, we will** (`hypothesis.to_verify`): {{TO_VERIFY}}
- **And measure** (`hypothesis.measure`): {{MEASURE}}
- **We are right if** (`hypothesis.right_if`): {{RIGHT_IF}}

## XYZ (Savoia)
**At least {{X_PERCENT}}% of {{Y}} will {{Z}}.**
- X derivation from unit economics (`x_derivation`): {{X_DERIVATION}}
- Metric (`metric`): {{METRIC_NAME}} = {{NUMERATOR}} ÷ {{DENOMINATOR}}

## Decision rule (frozen)
| Field | Value |
|---|---|
| `decision_rule` | {{DECISION_RULE}} |
| `success_threshold` | {{SUCCESS_THRESHOLD}} |
| `kill_threshold` | {{KILL_THRESHOLD}} |
| `planning_p` / `half_width` | {{PLANNING_P}} / {{HALF_WIDTH}} |
| `min_n` (from `gapval.py samplesize`, floors applied) | {{MIN_N}} |
| `criteria` (odi, kano, van-westendorp, themes, criteria rules) | {{CRITERIA}} |

For the `wilson`, `themes` and `ellis` rules (`xyz.x` = `success_threshold`, `kill_threshold` ≤ `success_threshold`):
- PASS if the 95% lower bound ≥ success threshold.
- FAIL if the upper bound < kill threshold.
- INCONCLUSIVE otherwise, and whenever n is below `min_n`.

For the other rules, `criteria` decides (card V04 step 7):
- `odi`: `outcomes` and `min_opportunity`
- `kano`: `features` and `pass_categories`
- `van-westendorp`: `price_point_month_usd`
- `criteria` (tech-spike, search-demand): `acceptance_tests`

## Logistics
- Duration (`duration_days`): {{DURATION_DAYS}} · Budget (`budget_usd`): {{BUDGET_USD}}
- Channels, one UTM link each (`channels`): {{CHANNELS}}
- Human operations (`required_ht`, in order; deploy first for landing pages): {{REQUIRED_HT}}. `gapval.py next` turns each slug into a blocking human task and adds an "export results" task.

## Ethics (`ethics`, all must be true)
- [ ] Disclosure right after the click (`disclosure`)
- [ ] Consent for any email collected (`consent`)
- [ ] No charge without explicit consent (`no_charge_without_consent`)
- [ ] Privacy notice linked (`privacy_notice`)
- Exposure limit (`exposure_limit`): {{EXPOSURE_LIMIT}}

## Pre-committed actions
- On PASS (`on_pass`): {{ON_PASS}}
- On FAIL (`on_fail`): {{ON_FAIL}} · Pivot hypothesis (`pivot_hypothesis`): {{PIVOT_HYPOTHESIS}}
- On INCONCLUSIVE (`on_inconclusive`): {{ON_INCONCLUSIVE}}
