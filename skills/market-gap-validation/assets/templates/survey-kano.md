# Kano feature survey — {{PRODUCT_NAME}} ({{EXPERIMENT_ID}})

Kano model with Better/Worse coefficients (Berger et al. 1993). It separates features customers **expect** (Must-be), features where **more is better** (One-dimensional), features that **delight** (Attractive), and features they **don't care about** (Indifferent). It needs **n ≥ 200** ICP respondents (`surveys.kano_min_n`); below that, categories are unreliable and results are directional.

## Intro (shown to respondents)
"This 5-minute survey asks how you would feel about possible features of a tool for {{JOB}}. Nothing exists yet, and we don't ask for your name or email."

## 1. Screener
1. "In the last 3 months, have you {{JOB}}?" Yes / No → if No, end.
2. "Which best describes you?" {{SEGMENT_OPTIONS}} → keep only the card's segment.

## 2. Feature pairs (repeat for 5–12 features in the MVP scope; randomise the order)
For feature **{{FEATURE_DESCRIPTION}}** ({{FEATURE_ID}}), described as a benefit in plain words:
- **Functional:** "If the tool **had** {{FEATURE_DESCRIPTION}}, how would you feel?"
- **Dysfunctional:** "If the tool **did not have** {{FEATURE_DESCRIPTION}}, how would you feel?"

Answer options for both questions, with the code exported in the CSV:
| Option shown | Code |
|---|---|
| I like it | L |
| I expect it | M |
| I am neutral | N |
| I can live with it | W |
| I dislike it | D |

## Scoring (done by `gapval.py stats`)
Evaluation table (rows = functional answer; columns = dysfunctional L, M, N, W, D):

| | L | M | N | W | D |
|---|---|---|---|---|---|
| L | Q | A | A | A | O |
| M | R | I | I | I | M |
| N | R | I | I | I | M |
| W | R | I | I | I | M |
| D | R | R | R | R | Q |

- Category = the most frequent answer, with ties broken M > O > A > I.
- Better = (A+O)/(A+O+M+I); Worse = −(O+M)/(A+O+M+I).
- The full category distribution is reported for every feature.
- The card's `criteria.features` and `criteria.pass_categories` decide: PASS when every target feature falls in those categories without a tie; FAIL when every target feature is Indifferent or Reverse. Below n = 200 the result is labelled directional.

## CSV export expected by `gapval.py ingest --kind survey-kano`
Saved by the human at `validation/data/{{EXPERIMENT_ID}}/survey-kano.csv`. One row per respondent × feature. Pseudonymous ids only; exports with email, name, phone, address or ip columns are rejected.
```
respondent,feature,functional,dysfunctional
R001,F-MULTICURRENCY,L,D
R001,F-BANK-SYNC,M,D
R002,F-MULTICURRENCY,L,W
```
- `feature`: the feature id used in the survey mapping.
- `functional` and `dysfunctional`: one of L, M, N, W, D. The words like, must-be, expect, neutral, live-with, tolerate and dislike, or the digits 1–5 in that order, are accepted too.
