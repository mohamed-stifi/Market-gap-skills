# Metrics and decision rules

`scripts/gapval.py` computes everything here; this page explains what the numbers mean. Defaults are in `assets/defaults.json`, each with its source. The worked examples are unit-test vectors.

Contents
1. Wilson interval and the pre-registered decision rule
2. Sample size
3. Interviews: saturation and agreement
4. ODI opportunity scores
5. Kano
6. Van Westendorp and Newton–Miller–Smith
7. Product–market-fit survey (after launch)
8. Assumption ranking
9. Verdict and demand strength

## 1. Wilson interval and the pre-registered decision rule
For k successes in n trials, with p̂ = k/n and z = 1.96:
- center = (p̂ + z²/(2n)) / (1 + z²/n)
- half-width = z·√(p̂(1−p̂)/n + z²/(4n²)) / (1 + z²/n)

Worked example: 20/100 → 13.3%–28.9%.

The decision rule, frozen in each Test Card (X = `success_threshold`, K = `kill_threshold`, K ≤ X):
- **PASS:** the lower bound ≥ X.
- **FAIL:** the upper bound < K.
- **INCONCLUSIVE:** everything else, including any n below the pre-registered `min_n`.

Results are reported per channel and pooled; only the pooled result decides.

**Setting X.** Derive X from economics and write the derivation in `x_derivation`. Example:
- You need 40 paying customers in the first quarter.
- The channels can bring about 1,000 targeted visitors.
- About half of the waitlist converts to paid.
- So X ≈ 40 ÷ 1,000 ÷ 0.5 = 8%.

Published landing-page medians (Unbounce 2024: 6.6% overall, 3.8% for SaaS) are context, never the threshold.

## 2. Sample size
n = ⌈z²·p(1−p)/h²⌉, where p is the planning rate and h the half-width. Examples: 10% ± 5 pp → 139; 5% ± 3 pp → 203.

Web experiments also need at least `stats.min_visitors_floor` (100) visitors. Fix n before starting and do not peek: a decision is valid only at the pre-registered n.

## 3. Interviews: saturation and agreement
- **Minimum:** `interviews.min_interviews` (10) good problem interviews (Maurya).
- **Saturation** (Guest, Namey & Chen 2020): the base is the codes from the first 4 interviews. Runs of 2 slide forward one interview at a time. Saturation is reached when new codes in a run ÷ base codes ≤ 5%, reported as "k+2".
- **Decision:** the share of coded interviews that carry a pre-registered problem code, judged by the Wilson rule in §1.
- **Agreement:** coder B codes all transcripts when there are 15 or fewer, otherwise a 20% sample (minimum 5). Krippendorff's α per code: ≥ .80 accept, .667–.80 provisional, below that revise. Codes with fewer than 3 positives are not assessable.

## 4. ODI opportunity scores
Importance and satisfaction are each 10 × the share of respondents rating 4 or 5 on a 1–5 scale. Then:
- Opportunity = I + max(I − S, 0). Worked example: I = 7.4, S = 2.8 → 12.0.
- **Labels:** ≥ 10 underserved, > 12 high, > 15 extreme; S > I is overserved.
- **PASS:** every target outcome reaches `criteria.min_opportunity` (default 10).
- **Sample:** n ≥ 180. Below that, results are directional.

## 5. Kano
Each feature gets a functional question ("if it has…") and a dysfunctional one ("if it lacks…"), both answered Like (L), Must-be (M), Neutral (N), Live-with (W) or Dislike (D). The answer pair gives the category:

| functional \ dysfunctional | L | M | N | W | D |
|---|---|---|---|---|---|
| L | Q | A | A | A | O |
| M | R | I | I | I | M |
| N | R | I | I | I | M |
| W | R | I | I | I | M |
| D | R | R | R | R | Q |

- **Categories:** A attractive, O one-dimensional, M must-be, I indifferent, R reverse, Q questionable.
- **Feature category:** the most frequent; ties go M > O > A > I.
- **Coefficients:** Better = (A+O)/(A+O+M+I); Worse = −(O+M)/(A+O+M+I).
- **PASS:** every target feature falls in `criteria.pass_categories`, without a tie.
- **Sample:** n ≥ 200; below that, directional.

## 6. Van Westendorp and Newton–Miller–Smith
Four questions: too cheap, cheap (a bargain), expensive (getting expensive), too expensive. Respondents who violate too cheap ≤ cheap ≤ expensive ≤ too expensive are dropped.

**Cumulative curves:**
- "Too cheap" and "cheap" are the share answering ≥ the price, so they fall as the price rises.
- "Expensive" and "too expensive" are the share answering ≤ the price, so they rise.
- Not cheap = 1 − cheap; not expensive = 1 − expensive.

**Crossings** (linear interpolation):
- PMC = too cheap × not cheap
- OPP = too cheap × too expensive
- IPP = cheap × expensive
- PME = too expensive × not expensive
- The acceptable range is PMC–PME.

Hand-checked example: four respondents (5/10/20/30, 8/12/25/35, 10/15/30/40, 12/20/35/50) → PMC 12, OPP 15, IPP 20, PME 30.

**Newton–Miller–Smith:**
- Purchase likelihood (1–5) at each respondent's cheap and expensive price is calibrated to 5→70%, 4→50%, 3→30%, 2→10%, 1→0%, with 0% at the too-cheap and too-expensive prices.
- Trial is interpolated across prices and averaged over respondents. The output is the trial-maximising price and the revenue-maximising price (price × trial).

**Decision:** PASS when the planned price is within PMC–PME. Sample: 100–200 per segment; below that, directional.

## 7. Product–market-fit survey (after launch)
Ask: "How would you feel if you could no longer use the product?" The score is very disappointed ÷ (responses − N/A), compared to 40% with the Wilson rule.
- Minimum 40 responses, from users who have used the core product at least twice, including within the last two weeks.
- Then use Vohra's segmentation: build the high-expectation customer profile from the "very disappointed" users.

This survey goes into the watchlist for the monitor stage.

## 8. Assumption ranking
- **Risk** = importance (1–5) × (5 − evidence (0–5)). Ties are broken by ICE = impact × confidence × ease (1–10 each).
- **Selected:** the top `assumptions.experiments_per_round` (3) assumptions with risk above 0.
- **Critical:** importance ≥ `assumptions.critical_importance_min` (4).

## 9. Verdict and demand strength
**Evidence ladder:** desk 0 < prototype 1 = interview 1 = survey 1 = click 1 < email 2 < call 3 < LOI 4 < deposit 5 = pre-sale 5.

**Assumption status:**
- **validated:**
  - desirability: a pass at evidence level ≥ 2 (email)
  - viability: a pass at level ≥ 4 (LOI), or a non-directional Van Westendorp pass
  - feasibility: any pass
- **supported:** a pass, but only with weaker evidence; escalate.
- **invalidated:** a fail.
- **inconclusive:** inconclusive, conflicting or tampered results.
- **untested.**

**Verdict:**
- Each invalidated **critical** assumption contributes its failing card's `on_fail` action: kill → KILL, pivot → PIVOT, iterate → ITERATE.
- The most conservative action wins (KILL > PIVOT > ITERATE).
- Otherwise **GO** if every critical desirability and viability assumption is validated, else **ITERATE**.

**Demand strength:**
- strong: a deposit or pre-sale experiment passed
- moderate: an email, call or LOI experiment passed
- weak: otherwise
