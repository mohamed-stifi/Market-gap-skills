# D23 · Gates, scoring and sensitivity

| Origin | Phase | Roles | Status |
|---|---|---|---|
| The validation tests from the market-gap method (Pain, Pay, Size, Why empty, Why now, Reach, Right to win) and from the research-gap method (real, matters, feasible, right size); anchored rubrics; Monte Carlo weight sensitivity | P6 Appraisal | orchestrator | core |

**Use when:** after `certainty` and `size`, when `next` issues `RUN gapscan.py score RUN`.

**Why:** A ranking is only as good as the reasons behind each number.
- **Gates** remove opportunities a small, agent-run business can't pursue, however attractive they look.
- **Anchored 0–3 scores** are computed from evidence counts, red-team verdicts and the why-now log. They replace gut feeling with rules anyone can recompute.
- **Sensitivity testing** stress-tests the ranking, because weights are a choice: p_top3 says how often each gap stays in the top three when the weights shift.

**Inputs**
- Cards that passed `cards check`; `gaps/redteam/*.json` and `gaps/judgments.jsonl`.
- `gaps/certainty.json` and `gaps/sizing.json`.
- `evidence/why-now.jsonl` and `evidence/bursts.json`.
- `analysis/price_ladder.csv`, `analysis/supply.jsonl` and `analysis/gapmap.json`.
- The protocol: `ambition.min_arr_usd`, `founder_fit` and any `overrides`.

**Procedure**
1. **Gates first** (`scoring.gates`). A card is excluded from the ranking, and listed with the gate it failed, when any of these holds:
   - the red-team verdict is killed
   - `regulatory_load` is above medium
   - `human_ops_burden` is above medium
   - `agent_buildability` is below partial
   - `platform_risk` is above 2
   - `tos_feasible` is false
2. **Score each remaining card 0–3 per criterion.** The script computes the anchors and records the inputs it used:
   - **pain** (is it real?):
     - 0: fails the D20 thresholds
     - 1: meets them
     - 2: also has S3-or-stronger workaround or switch records from at least 2 distinct authors
     - 3: also has S4 records from at least 2 distinct authors, or at least 20 distinct supporting authors
   - **pay** (will they pay?):
     - 0: no wtp or S4 records, and no paid incumbent serving the job
     - 1: incumbents serving the card's job codes charge for it (paid tiers on the price ladder)
     - 2: at least one S4 or wtp record
     - 3: S4 or wtp records from at least 3 distinct authors in at least 2 domains
   - **size** (right size?): SOM base from `gaps/sizing.json`, compared with `protocol.ambition.min_arr_usd`:
     - 0: below a quarter of the target, or sizing missing
     - 1: below the target
     - 2: at least the target
     - 3: at least three times the target
   - **competition** (why is it empty?):
     - 0: full coverage found (killed, so already gated out)
     - 1: weakened
     - 2: survives, but the gap-map cell has supply
     - 3: survives, and the cell is an absolute or synthesis gap
   - **why_now**:
     - 0: no why-now ids
     - 1: only weak entries
     - 2: at least one moderate or strong entry
     - 3: two or more moderate or strong entries, or a significant burst (p < `bursts.alpha`) in one of the card's `demand_signals`
   - **reach**:
     - 0: no reach channels
     - 1: one channel
     - 2: two or more channels with a known size
     - 3: two or more channels, including a marketplace, integration or keyword channel backed by evidence
   - **right_to_win**: the red team's judged 0–3 value. Its rationale is required.
3. **Total** = 100 × Σ (weight × score) ÷ 3. The weights are `scoring.weights` unless the protocol overrides them: pain 0.22, pay 0.18, size 0.12, competition 0.14, why_now 0.10, reach 0.14, right_to_win 0.10.
4. **Sensitivity.** Draw `scoring.draws` (2,000) weight vectors from a Dirichlet distribution with concentration `scoring.dirichlet_concentration` (50) × the default weights, and re-rank each time. Report:
   - p_top3: the share of draws in which the card ranks within the top `scoring.top_n` (3)
   - its median rank
5. **Ties:** higher pain certainty first, then higher demand certainty, then more distinct supporting authors.

**Output**
- `gaps/scores.csv`: one row per gap and criterion, with score, weight, the inputs used and the rationale or evidence ids.
- `gaps/ranking.json`: rank, total, p_top3, median rank and gate results, plus excluded cards and their reasons.

**How the criteria map to the earlier validation tests**
- Pain → pain. "Does it matter?" → pain and pay together.
- Pay → pay.
- Size and "right size" → size.
- "Why empty" and "is it real" → competition, plus the red team.
- "Why now" → why_now.
- Reach → reach.
- "Right to win" and "feasible" → right_to_win, plus the agent-buildability and human-ops gates.

**Pitfalls**
- **Hand-adjusting scores.** Change the inputs (evidence, judgments) and re-run, or change the weights with `protocol amend` and a reason.
- **Reading totals as precise.** Report the rank together with p_top3. A card with p_top3 of 0.4 is a coin flip, not a winner.
- **A missing size target.** If `ambition.min_arr_usd` is absent, size scores 0 for every card. The dossier must say so; set the target in the protocol.

**Done when:** `gaps/ranking.json` reflects the current inputs and, in gated runs, the shortlist approval task is open.
