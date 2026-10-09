# V03 · Experiment library and selection

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Experiment library (Bland & Osterwalder, *Testing Business Ideas*: discovery vs validation experiments); Customer Development (Blank); smoke tests and concierge MVPs (Ries, *The Lean Startup*); pretotyping (Savoia); The Mom Test (Fitzpatrick); ODI (Ulwick); Kano; Van Westendorp | V2 Design | designer | core |

**Use when:** after assumptions are ranked. Choose at least one experiment for each selected assumption.

**Why:** The right experiment is the **cheapest one whose result could change your mind**. Evidence comes in strengths. People *saying* things (interviews, surveys) is weak. People *doing* things (signing up, booking a call, signing a letter of intent) is stronger. People *paying* (a deposit or pre-sale) is strongest. Start cheap and weak to learn fast, then climb the ladder as confidence grows: click < email < booked call < LOI < deposit/pre-sale.

**Inputs:** `validation/assumptions-ranked.json`, `validation/ost.json`, `validation/opportunity.json`, defaults under `surveys.*`, `interviews.*`, `stats.*`, `evidence_ladder` and `verdict.*`.

**The library** (values for `type`, `evidence_level` and `decision_rule` in the Test Card)

| `type` | Best for | `evidence_level` | `decision_rule` | Minimum sample | Cost and time | Human operations |
|---|---|---|---|---|---|---|
| `problem-interviews` | desirability: the problem is real, frequent and costly | interview | themes | ≥ `interviews.min_interviews` (10) good interviews, plus saturation | low $; 1–3 weeks | recruit, schedule, consent, conduct |
| `switch-interviews` | desirability and viability: why people changed tools, and what they paid | interview | themes | ≥ 10 recent switchers | low $; 1–3 weeks | recruit switchers, conduct |
| `odi-survey` | desirability: which outcomes are underserved | survey | odi | n ≥ `surveys.odi_min_n` (180) | panel or community posts | distribute, possibly pay a panel |
| `kano-survey` | which features delight, are expected, or don't matter | survey | kano | n ≥ `surveys.kano_min_n` (200) | as above | distribute |
| `pricing-survey` | viability: acceptable price range | survey | van-westendorp | n ≥ `surveys.vw_min_n` (100) per segment | as above | distribute |
| `smoke-test` | desirability: will the ICP act on the promise? | email | wilson | `gapval.py samplesize`, never below `stats.min_visitors_floor` (100) | hosting + traffic; 1–3 weeks | deploy, form, analytics, posts or ads |
| `fake-door` | desirability of one plan or feature inside a page | click | wilson | as smoke-test | as smoke-test | as smoke-test |
| `loi` | viability for B2B: a signed, non-binding intent to buy | loi | wilson | every qualified prospect you can reach; expect wide intervals | outreach time | outreach from the human's account |
| `presale` | viability: money with explicit consent and a refund promise | presale | wilson | as loi | payment link | payment account, refunds |
| `concierge` | desirability + viability of the service done by hand | call (deposit when they pay) | wilson | 5–20 customers | human time | delivery by the human |
| `tech-spike` | feasibility: can agents build and run the riskiest technical piece? | prototype | criteria | every pre-registered acceptance test has a result | agent time; days | none, unless the spike needs keys or accounts |
| `search-demand` | a pre-check: is anyone searching for the job's words? | desk | criteria | the acceptance tests you pre-register | free signals, or a keyword-data key | tier-2 key if paid keyword data is used |

Each type's export (CSV columns) is listed under `ingest` in `references/cli.md`. Concierge results use the `presale` format (count, contacted); spikes and search-demand checks use `spike` (test, passed).

**Selection rules**
1. Desirability first. A "no" on desirability makes every viability and feasibility test moot. Problem interviews come before a smoke test when the problem itself is in doubt; a smoke test comes first when the problem is well evidenced and the promise is in doubt.
2. Never validate willingness to pay with opinions alone. A viability assumption counts as validated only with evidence at LOI level or stronger (`verdict.viability_min_level` = 4), or with a Van Westendorp range that contains the planned price at n ≥ `surveys.vw_min_n`.
3. Desirability needs at least email-level behaviour (`verdict.desirability_min_level` = 2). Clicks and opinions inform, but they do not validate.
4. Respect the survey minimums. Below `odi_min_n`, `kano_min_n` or `vw_min_n` a survey is directional only. Plan for the full sample, or choose another test.
5. Test a feasibility assumption with a `tech-spike`: agents build the smallest prototype of the riskiest technical piece and record pass or fail per acceptance test (`criteria` rule, evidence level `prototype`). A spike is internal work, so it needs no outward human operations unless it requires keys or accounts.
6. Run at most `assumptions.experiments_per_round` (3) experiments at once. Running more splits your traffic and attention.

**Procedure**
1. For each selected assumption, pick a type with the selection rules. Write the reason in one line of the draft card's `hypothesis.to_verify`.
2. Create the draft with `gapval.py prereg new RUN --experiment EXP-NN --type TYPE --assumption A1[,A2]`, numbering experiments EXP-01, EXP-02 and so on. Then fill it in with card V04.
3. Run `gapval.py prereg check RUN EXP-NN` until it passes. The orchestrator freezes the cards; you never do.

**Output:** draft Test Cards `validation/prereg/EXP-NN.json` (schema `test-card`), one or more for each selected assumption.

**Metrics and checks:** `gapval.py prereg check` enforces the sample-size floor, the typed `criteria` each rule needs and the other methodology rules. Survey samples below the minimums pass with a warning, and their results are labelled directional. Card V04 has the details.

**Pitfalls**
- **Picking by excitement.** A smoke test is fun to build, but an interview may be the cheapest falsifier.
- **Asking "would you buy?"** That is the weakest evidence there is. It never validates viability.
- **Pricing before desirability.** A pricing survey of people who do not want the product measures nothing.
- **Kano with 30 respondents.** Categories flip at small n; report the result as directional or skip it.
- **LOIs for consumer products.** Letters of intent are a B2B instrument. For consumers, use deposits with consent and a refund.
- **Treating search-demand as validation.** Search volume is desk evidence (`desk`, the bottom of the ladder). Use it to choose channels and a realistic `planning_p`. A search-demand PASS never validates desirability or viability; at best it marks the assumption *supported*.

**Done when:** every selected assumption has at least one draft card that passes `gapval.py prereg check`.
