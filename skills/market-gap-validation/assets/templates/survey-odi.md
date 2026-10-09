# ODI outcome survey — {{JOB}} ({{EXPERIMENT_ID}})

Outcome-Driven Innovation (Ulwick). It finds which desired outcomes are important but poorly satisfied today. It needs **n ≥ 180** ICP respondents (`surveys.odi_min_n`); below that, results are directional.

## Intro (shown to respondents)
"This 6–8 minute survey is about how you handle {{JOB}}. There are no right answers, and we don't ask for your name or email. Your answers help us understand what matters most."

## 1. Screener (route out non-ICP respondents)
1. "In the last 3 months, have you {{JOB}}?" Yes / No → if No, end with thanks.
2. "Which best describes you?" {{SEGMENT_OPTIONS}} → keep only the segments named in the card's Y.
3. "What do you use today for {{JOB}}?" Free text (it names the comparator).

## 2. Outcome questions (repeat for every outcome)
Write each outcome as **direction + metric + object + clarifier**, for example "Minimize the time it takes to match a payment to its invoice". Use 8–20 outcomes from `opportunity.json` and the codebook (O- codes), in random order for each respondent.

For outcome **{{OUTCOME_STATEMENT}}** ({{OUTCOME_CODE}}):
- **Importance:** "When you {{JOB}}, how important is it to you to {{OUTCOME_STATEMENT_LOWERCASE}}?"
  1 Not at all important · 2 Slightly · 3 Moderately · 4 Very · 5 Extremely important
- **Satisfaction:** "How satisfied are you with how your current way of working lets you {{OUTCOME_STATEMENT_LOWERCASE}}?"
  1 Not at all satisfied · 2 Slightly · 3 Moderately · 4 Very · 5 Extremely satisfied

## 3. Closing
"Thank you." No email request inside the survey. If you want to offer a waitlist, link to the landing page *after* submission, with its own consent.

## Scoring (done by `gapval.py stats`)
- I = 10 × the share answering 4 or 5 on importance. S = the same for satisfaction.
- Opportunity = I + max(I − S, 0).
  - ≥ 10: underserved
  - > 12: high
  - > 15: extreme
  - S > I: overserved
- Example: I = 7.4 and S = 2.8 give 12.0.
- The card's `criteria.outcomes` and `criteria.min_opportunity` (default 10) decide: PASS when every target outcome reaches it; FAIL when none does, or they are overserved. Below n = 180 the result is labelled directional.

## CSV export expected by `gapval.py ingest --kind survey-odi`
Saved by the human at `validation/data/{{EXPERIMENT_ID}}/survey-odi.csv`. Long format: one row per respondent × outcome. Pseudonymous ids only; exports with email, name, phone, address or ip columns are rejected.
```
respondent,outcome,importance,satisfaction
R001,O-MATCH-TIME,5,2
R001,O-UNPAID-VISIBILITY,4,3
R002,O-MATCH-TIME,4,1
```
- `outcome`: the outcome code (O-…) used in the survey mapping.
- `importance` and `satisfaction`: integers 1–5.
- Leave out respondents who failed the screener.
