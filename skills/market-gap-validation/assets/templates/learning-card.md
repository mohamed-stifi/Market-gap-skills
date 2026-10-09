# Learning Card — {{EXPERIMENT_ID}}

Human-readable mirror of `validation/learning-cards/{{EXPERIMENT_ID}}.json` (schema `learning-card`, card V10). Every number must come from `validation/results/{{EXPERIMENT_ID}}.json`.

| Field | Value |
|---|---|
| Result (`result`) | {{RESULT}}: PASS / FAIL / INCONCLUSIVE / TAMPERED |
| Evidence level (`evidence_level`) | {{EVIDENCE_LEVEL}} |

- **We believed that** (`we_believed`): {{WE_BELIEVED}}
- **We observed** (`we_observed`): {{WE_OBSERVED}}
  Example: "31 consented sign-ups from 196 visitors (15.8%, Wilson 95% 11.4–21.6%) against a 10% threshold."
- **From that we learned that** (`we_learned`): {{WE_LEARNED}}
- **Therefore, we will** (`therefore`): {{THEREFORE}}. This is the card's pre-registered action, made concrete.

## Key numbers (`numbers`)
| n | k | observed | lower | upper | threshold(s) |
|---|---|---|---|---|---|
| {{N}} | {{K}} | {{OBSERVED}} | {{LOWER}} | {{UPPER}} | {{THRESHOLDS}} |

For survey and spike experiments, record the figures the rule used instead: the target outcomes' opportunity scores (odi), the target features' categories with Better and Worse (kano), PMC–PME and the planned price (van-westendorp), or each acceptance test's pass or fail (criteria). Note whether the result is directional.

## Per channel (if the card had several)
| Channel | n | k | observed | 95% interval |
|---|---|---|---|---|
| {{CHANNEL}} | {{N}} | {{K}} | {{OBSERVED}} | {{INTERVAL}} |

Channel differences are hypotheses for the next card, not results of this one.
