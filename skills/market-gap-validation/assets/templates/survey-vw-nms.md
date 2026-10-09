# Pricing survey (Van Westendorp + Newton–Miller–Smith) — {{PRODUCT_NAME}} ({{EXPERIMENT_ID}})

Price Sensitivity Meter (Van Westendorp 1976) with the purchase-likelihood extension (Newton, Miller & Smith 1993). It finds the price range buyers find acceptable, and the prices that maximise trial and revenue. It needs **at least 100 respondents per segment** (`surveys.vw_min_n`; 100–200 is the practitioner range). Run **one survey and one Test Card per segment**: each card ingests a single `survey-vw.csv`, and the script never splits by segment, so ranges are never pooled across segments.

## Intro (shown to respondents)
"This 4-minute survey asks what you would expect to pay for a tool for {{JOB}}. Nothing is for sale, and we don't ask for your name or email."

## 1. Screener
1. "In the last 3 months, have you {{JOB}}?" Yes / No → if No, end.
2. "Which best describes you?" {{SEGMENT_OPTIONS}} → keep only the card's segment.
3. "What do you pay today for this, if anything?" Free text (context only).

## 2. Concept (show before the price questions)
A neutral, factual description of what the product does, built from the MVP scope. No hype, no fake social proof:
> {{CONCEPT_DESCRIPTION}}
> Price would be per month, in {{CURRENCY}}.

## 3. The four price questions (open numeric answers, per month, in {{CURRENCY}})
1. **Too expensive:** "At what price would this be **so expensive** that you would not consider buying it?"
2. **Too cheap:** "At what price would it be **so cheap** that you would doubt its quality?"
3. **Expensive:** "At what price would it start to get **expensive**, so that you would have to think twice, but would still consider it?"
4. **Bargain:** "At what price would it be **a bargain**, a great buy for the money?"

## 4. Purchase likelihood (NMS extension)
Show each respondent's own answers back to them:
5. "At {{THEIR_BARGAIN_PRICE}} per month, how likely would you be to buy it?" 5 Very likely · 4 Likely · 3 Not sure · 2 Unlikely · 1 Very unlikely
6. "At {{THEIR_EXPENSIVE_PRICE}} per month, how likely would you be to buy it?" Same scale.

## Scoring (done by `gapval.py stats`)
- Drop respondents whose answers break too cheap ≤ cheap ≤ expensive ≤ too expensive.
- Curves:
  - "too cheap" and "cheap" descend: the share with an answer ≥ the price.
  - "expensive" and "too expensive" ascend: the share with an answer ≤ the price.
  - not cheap = 1 − cheap; not expensive = 1 − expensive.
- Crossing points:
  - OPP = too cheap ∩ too expensive
  - IPP = cheap ∩ expensive
  - PMC = too cheap ∩ not cheap
  - PME = too expensive ∩ not expensive
  - Acceptable range = PMC to PME.
- NMS calibration: 5→70%, 4→50%, 3→30%, 2→10%, 1→0%, with 0% at the respondent's too-cheap and too-expensive prices. Reports the trial-maximising and revenue-maximising prices.
- The card's `criteria.price_point_month_usd` (the planned price) decides: PASS when it lies within PMC–PME, FAIL when outside. Viability counts only for a non-directional PASS, with n ≥ `surveys.vw_min_n`.

## CSV export expected by `gapval.py ingest --kind survey-vw`
Saved by the human at `validation/data/{{EXPERIMENT_ID}}/survey-vw.csv`. One row per respondent. Prices are numbers in one currency per file, and pseudonymous ids only; exports with email, name, phone, address or ip columns are rejected.
```
respondent,too_cheap,cheap,expensive,too_expensive,likely_cheap,likely_expensive
R001,5,12,29,49,5,3
R002,8,15,25,40,4,2
```
- `cheap` holds the **bargain** answer (question 4); `expensive` holds the **getting expensive** answer (question 3).
- `likely_cheap` and `likely_expensive` are the 1–5 answers to questions 5 and 6. They are optional: if you skip the NMS extension, drop both columns from the export. Never leave them empty, because the NMS calculation needs a 1–5 value for every row once the columns exist.
