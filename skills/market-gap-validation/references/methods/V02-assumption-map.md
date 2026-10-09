# V02 · Assumption mapping

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Assumptions Map (Bland & Osterwalder, *Testing Business Ideas*: desirability, viability, feasibility on importance × evidence); ICE scoring (Sean Ellis); confidence tied to evidence type (Gilad's Confidence Meter) | V1 Frame | orchestrator (rank), designer (ratings) | core |

**Use when:** after `gapval.py ost check RUN` passes, and again whenever new evidence changes a rating.

**Why:** You cannot test everything, and you should not test what you already know. The assumptions that deserve a test are the ones that would sink the solution if false *and* that you have little behavioural evidence for. That is the top-left quadrant of the map. A script computes the ranking so that the order does not depend on which test feels most fun to run. Builders, human or agent, are drawn to feasibility tests because building is comfortable. That is the build trap: proving you *can* make something nobody asked for.

**Inputs**
- `validation/ost.json`: ratings for the target solution's assumptions.
- Defaults: `assumptions.critical_importance_min` (4), `assumptions.experiments_per_round` (3), `assumptions.evidence_scale` (0–5).

**Procedure**
1. Orchestrator: run `gapval.py assumptions rank RUN`. For each assumption of the target solution it computes:
   - risk = importance × (5 − evidence). The maximum is 25, for importance 5 with no evidence.
   - ties broken by ICE = impact × confidence × ease.
   
   It marks the top `assumptions.experiments_per_round` assumptions as selected (never one with risk 0) and writes `validation/assumptions-ranked.json`.
2. Read the ranking and place each assumption in a quadrant for the report:

   | Quadrant | Rule | Action |
   |---|---|---|
   | Test now | importance ≥ 4 and evidence below LOI level | design an experiment (V03) |
   | Monitor | importance ≥ 4 and evidence at LOI level or stronger | cite the evidence; re-check at launch |
   | Park | importance ≤ 3 | record; revisit after the critical ones |

3. Check that every selected assumption is **critical**, meaning importance ≥ `assumptions.critical_importance_min`. If the ranking selects a non-critical one, the tree has fewer critical risks than slots; that is fine, and the report says so.
4. If you think a rating is wrong, change it in `validation/ost.json`, give the reason in `notes`, then run `gapval.py ost check RUN` and `gapval.py assumptions rank RUN` again. Never reorder the ranked file by hand: the ranking must stay reproducible from the ratings.
5. When a selected assumption depends on another one, keep both in the ranking but test the upstream one first. For example, "they will pay €29 a month" depends on "they want this at all". The Test Card's `on_fail` for the upstream test should stop the downstream test.

**Output:** `validation/assumptions-ranked.json`, listing assumptions with risk, ICE, quadrant and the selected flags.

**Metrics and checks**
- Risk is computed only from the ratings in `ost.json`. Two runs over the same file must give the same order.
- Every selected assumption needs an experiment in V03. A feasibility assumption gets a `tech-spike`: the smallest prototype of the riskiest technical piece, judged by pre-registered acceptance tests (`criteria` rule, evidence level `prototype`).
- GO depends only on the critical desirability and viability assumptions. An invalidated critical feasibility assumption still triggers its card's `on_fail` action (V10).

**Pitfalls**
- **Evidence inflation.** Rating evidence 3+ because the discovery dossier "felt convincing". Only behaviour toward *this* solution moves an assumption above 1.
- **Importance deflation.** Rating a scary assumption as unimportant to avoid a hard test, such as willingness to pay.
- **Testing in comfort order.** Feasibility first because it means building; pricing last because it means asking for money.
- **Ignoring dependencies.** Running a pricing test while desirability is unknown wastes the traffic you will need later.

**Done when:** `validation/assumptions-ranked.json` exists, the selected assumptions are critical (or the shortfall is explained), and `gapval.py next RUN` moves on to experiment design.
