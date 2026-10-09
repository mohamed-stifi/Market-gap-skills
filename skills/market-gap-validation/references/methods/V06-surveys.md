# V06 · ODI, Kano and Van Westendorp surveys

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Outcome-Driven Innovation (Ulwick / Strategyn); Kano model with Better/Worse coefficients (Berger et al. 1993) and its reliability limits (Chapman & Callegaro); Price Sensitivity Meter (Van Westendorp 1976) with the Newton–Miller–Smith extension (1993) | V3 assets, V5 collect | builder (survey), analyst (reading), human (distribution) | conditional: a survey card is frozen |

**Use when:** a frozen card has `type: odi-survey`, `kano-survey` or `pricing-survey`.

**Why:** Surveys put numbers on things interviews only hint at: which outcomes are underserved, which features customers expect versus which delight them, and which price range feels acceptable. They are still *saying*, not *doing*. So a survey can rank and narrow, but it validates willingness to pay only in the narrow case defined below. Each method has a published scoring rule and a sample-size floor. Below the floor, results are directional, and the report says so.

**Inputs:** the frozen card; `validation/opportunity.json` (outcome statements, features in the MVP scope, pricing hypothesis); `assets/templates/survey-odi.md`, `survey-kano.md`, `survey-vw-nms.md`; defaults `surveys.*`.

**Procedure**
1. **Build (builder).** Copy the matching template to `validation/assets/EXP-NN/survey.md`.
   - Put the screening questions first, so non-ICP respondents are routed out.
   - Fill in outcomes, features or the price context.
   - Keep the exact answer scales.
   - Every respondent gets a pseudonymous id; never ask for names or emails inside the survey.
2. **Distribute (human).** Through human tasks (card V08), and only to the channels on the card.
3. **Ingest.** The human saves the export where the experiment's "export results" task says: `validation/data/EXP-NN/survey-odi.csv`, `survey-kano.csv` or `survey-vw.csv`, with the columns listed in the template and pseudonymous respondent ids only (exports with email, name, phone, address or ip columns are rejected). `gapval.py next` then runs `gapval.py ingest RUN --experiment EXP-NN --kind survey-odi|survey-kano|survey-vw --file PATH.csv` and `gapval.py stats RUN --experiment EXP-NN`.
4. **Pre-registered criteria.** Each rule reads the card's `criteria` object (V04). `success_threshold` and `kill_threshold` are not used by these rules. A card whose `min_n` is below the method's minimum passes `prereg check` with a warning, and its results are labelled directional.

**ODI** (`decision_rule: odi`)
- For each desired outcome, ask importance (1–5) and satisfaction with the current solution (1–5).
- I = 10 × the share answering 4 or 5 on importance (`surveys.odi_top_two_box`). S = the same for satisfaction.
- **Opportunity = I + max(I − S, 0).**
  - ≥ `surveys.odi_underserved` (10): underserved.
  - > `surveys.odi_high` (12): high.
  - > `surveys.odi_extreme` (15): extreme.
  - S > I: overserved, a candidate for "reduce" in an ERRC grid.
- Worked example: I = 7.4 and S = 2.8 give 7.4 + 4.6 = **12.0**, a high opportunity.
- Needs n ≥ `surveys.odi_min_n` (180). Below that, report directional scores with Wilson intervals on the top-two-box shares.
- Criteria to pre-register: `criteria.outcomes` (the outcome codes) and `criteria.min_opportunity` (default 10, the underserved level).
  - PASS: every target outcome reaches `min_opportunity`.
  - FAIL: no target outcome reaches it, or they are overserved.
  - INCONCLUSIVE: mixed outcomes, or n below the card's `min_n`.

**Kano** (`decision_rule: kano`)
- Ask each feature as a pair:
  - functional: "If the product had X, how would you feel?"
  - dysfunctional: "If the product did not have X, how would you feel?"
  
  Answers: L = I like it, M = I expect it, N = I am neutral, W = I can live with it, D = I dislike it.
- Evaluation table (rows = functional answer; columns = dysfunctional L, M, N, W, D):

  | Functional \ Dysfunctional | L | M | N | W | D |
  |---|---|---|---|---|---|
  | L | Q | A | A | A | O |
  | M | R | I | I | I | M |
  | N | R | I | I | I | M |
  | W | R | I | I | I | M |
  | D | R | R | R | R | Q |

  A = Attractive, O = One-dimensional, M = Must-be, I = Indifferent, R = Reverse, Q = Questionable.
- Category = the most frequent answer, with ties broken in the order `surveys.kano_tie_order` (M > O > A > I).
- **Better = (A+O)/(A+O+M+I)**; **Worse = −(O+M)/(A+O+M+I)**.
- Report the full distribution, not only the winning category.
- Needs n ≥ `surveys.kano_min_n` (200). Below that, categories flip easily, so label the result directional.
- Criteria to pre-register: `criteria.features` (the feature ids) and `criteria.pass_categories` (for example `["A", "O", "M"]`).
  - PASS: every target feature falls in the pass categories, without a tie.
  - FAIL: every target feature is Indifferent or Reverse.
  - INCONCLUSIVE: mixed or tied categories, or n below the card's `min_n`.

**Van Westendorp + Newton–Miller–Smith** (`decision_rule: van-westendorp`)
- Four questions:
  - At what price would it be **so expensive** you would not consider it?
  - …**so cheap** you would doubt its quality?
  - …**getting expensive**, but you would still consider it?
  - …**a bargain**?
- Drop respondents whose answers break too cheap ≤ cheap ≤ expensive ≤ too expensive.
- Cumulative curves:
  - "too cheap" and "cheap" descend: the share whose answer is ≥ the price.
  - "expensive" and "too expensive" ascend: the share whose answer is ≤ the price.
  - not cheap = 1 − cheap; not expensive = 1 − expensive.
- Crossing points, found by linear interpolation:
  - **OPP** = too cheap ∩ too expensive
  - **IPP** = cheap ∩ expensive
  - **PMC** = too cheap ∩ not cheap
  - **PME** = too expensive ∩ not expensive
  - **Acceptable range = PMC to PME.**
- NMS extension: ask purchase likelihood (1–5) at each respondent's own "bargain" and "getting expensive" prices. Calibrate 5→70%, 4→50%, 3→30%, 2→10%, 1→0% (`surveys.nms_calibration`), with 0% at their too-cheap and too-expensive prices. Report the trial-maximising and revenue-maximising prices. The export carries the answers as `likely_cheap` and `likely_expensive`; when you skip NMS, drop both columns rather than leaving them empty.
- Needs `surveys.vw_min_n` (100) or more per segment; 100–200 is the practitioner range. Each card ingests one `survey-vw.csv` and the script does not split by segment, so write one card per segment.
- Criteria to pre-register: `criteria.price_point_month_usd`, the planned price (the card-level `price_point_month_usd` is the fallback).
  - PASS: the planned price lies within PMC–PME.
  - FAIL: it lies outside the range.
  - INCONCLUSIVE: n below the card's `min_n`, or the range is undefined.
- **Viability rule:** a PASS validates viability only when it is not directional (n ≥ `vw_min_n`). Otherwise a pricing survey informs, and the assumption is at most *supported*.

**Output:** `validation/assets/EXP-NN/survey.md`, ingested data in `validation/data/EXP-NN/`, and `validation/results/EXP-NN.json`.

**Metrics and checks:** the formulas above, computed only by `gapval.py stats`. Results are labelled directional whenever n is below the method's minimum.

**Pitfalls**
- **Outcomes that are really features.** "Has a dashboard" is a solution. "Minimize the time it takes to see unpaid invoices" is an outcome.
- **Mixed segments.** Agencies and freelancers in one Van Westendorp pool give a meaningless range. Screen and segment.
- **Incentives that attract non-buyers.** A gift-card raffle fills the survey with people outside the ICP.
- **Stated price taken as proof of payment.** It is survey-level evidence. It only counts under the viability rule above.

**Done when:** each survey card has an ingested dataset of at least its `min_n` (or a documented shortfall), and `gapval.py stats` has written the result.
