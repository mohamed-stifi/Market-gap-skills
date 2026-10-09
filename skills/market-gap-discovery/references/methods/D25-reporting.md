# D25 · Dossier, handoff and PRISMA report

| Origin | Phase | Roles | Status |
|---|---|---|---|
| PRISMA 2020 flow and reporting; bottom-line-up-front reports (deep-research precedent); Value Proposition Canvas; Lean Canvas; positioning statement (Moore); Test Cards (Testing Business Ideas) | P7 Report | writer, orchestrator | core |

**Use when:** after scoring (and, in gated runs, after the shortlist approval), when `next` issues `RUN gapscan.py prisma RUN` and then `SPAWN writer`.

**Why:** The dossier is what a human reads, and the handoff is what the next skills build on. Both must carry the evidence trail, the uncertainty and the limits of the search, not only the conclusions. PRISMA-style flow counts show how much was searched and discarded. The handoff turns each opportunity into machine-readable inputs for validation, building, launch and monitoring.

**Inputs**
- `output/writer-assign.json`.
- `gaps/ranking.json`, `gaps/scores.csv`, `gaps/certainty.json`, `gaps/sizing.json`, `gaps/cards.jsonl`, `gaps/redteam/*.json`, `gaps/judgments.jsonl`.
- The `analysis/` files, `evidence/ledger.jsonl` and `evidence/why-now.jsonl`.
- `landscape/saturation.json`, `coding/agreement.json` and `coding/themes.json`.
- `output/prisma.json` and `output/prisma.md`.
- `coverage-gaps.jsonl`, `doctor.json`, `protocol.json` and `protocol.lock.json`.

**Procedure**
1. **Orchestrator:** run `gapscan.py prisma RUN`. It counts identified → de-duplicated → screened → verified → included, for entities, evidence and gaps, per source.
2. **Writer:** write `output/dossier.md` in this order:
   1. **BLUF.** For each top opportunity, one paragraph with:
      - the gap statement
      - score and p_top3
      - pain and demand certainty
      - demand strength (weak until validated)
      - the single riskiest assumption
   2. **Ranked opportunities.** For each one:
      - the gap statement and PICOS
      - 3–5 top verified quotes, with EV ids, URLs and strength
      - a Value Proposition Canvas: customer jobs, pains and gains (from the codes) against what incumbents offer
      - Lean Canvas fields: problem and existing alternatives, segments and early adopters, unique value proposition, solution (as a hypothesis), channels, revenue streams, cost structure, key metrics, unfair advantage
      - the strategy-canvas summary and the ERRC grid
      - sizing ranges, with their sources and assumptions
      - why-now entries, with dates
      - the red-team result: verdict, existing solutions, failed attempts, Five Forces, pre-mortem
      - certainty (pain and demand) and demand strength, with the downgrade reasons
      - assumptions turned into Test Card candidates in XYZ form ("At least X% of Y will Z")
      - go-to-market channels where the ICP gathers, with sizes
      - kill criteria: observable results that would stop work
   3. **Excluded and killed gaps**, with the gate or evidence that removed each.
   4. **Coverage and limitations:**
      - saturation numbers as lower bounds ("at least about N products, 95% CI a–b")
      - STOP_UNSATURATED, if it applies
      - independence
      - theme saturation
      - reliability, including any provisional codes
      - coverage gaps, excluded sources, and tier-2 sources not used
      - evidence pools screened only at the top without a stopping test, and products first seen in evidence (`prisma.json` → `evidence.large_pools` and `evidence.post_landscape_discoveries`)
   5. **PRISMA flow**, from `output/prisma.md`.
   6. **Watchlist:** what to monitor, and how often.
3. **Writer:** write `output/handoff.json` (handoff.schema.json):
   - `schema_version` "1.0", `run_id`, `generated_at`, `protocol_sha256` (from `protocol.lock.json`)
   - `coverage`: landscape, themes, independence, coverage_gaps
   - `opportunities`, each with:
     - rank, gap_id, title, statement, score, p_top3
     - certainty: pain, demand, demand_strength
     - icp: description, segment_codes, where_they_gather
     - jtbd: job, outcomes
     - top_quotes: at least 3
     - competitors
     - pricing_hypothesis: model, range_month_usd, basis
     - mvp: in_scope, out_of_scope, agent_buildability, notes
     - experiments: at least 1, each with id, assumption_id, type, hypothesis_xyz, metric, requires_ht
     - gtm_channels, metrics, kill_criteria (at least 1), risks, sizing, why_now, assumptions, open_questions
   - `watchlist` and `limitations`
4. **Writer:** write `output/watchlist.json` for the future monitor skill:
   - incumbents to recheck (pricing, changelog and roadmap pages, with their URLs)
   - queries to re-run, with their sources
   - signal series to extend
   - a re-check cadence
5. **Copy every number from the script outputs** (ranking, certainty, sizing, saturation, agreement). Never recompute a number, round it differently, or describe a number no script produced.
6. **Orchestrator:** run `gapscan.py validate RUN --report`. It checks every artifact against its schema. In the dossier and handoff it also checks that every cited EV id exists and is verified, that no raw usernames appear, and it flags single-source or stale evidence (older than `evidence.stale_months`). If the check fails, `next` creates a writer fix assignment listing the failures. Repeat until it passes.

**Output:** `output/dossier.md`, `output/handoff.json`, `output/watchlist.json`, `output/prisma.json`, `output/prisma.md` and `output/report-check.json`.

**Metrics and checks**
- `validate --report` passes.
- The handoff validates against handoff.schema.json.
- Every opportunity has at least three verified quotes, and every experiment links to an assumption id.

**Pitfalls**
- **Hiding the limits.** A dossier without its coverage section overstates what was found.
- **Inflated language.** Never write "validated", "proven demand" or "underserved (ODI)" about desk-only results. Write "the evidence suggests", with the certainty label.
- **Unverifiable quotes:** quotes without EV ids, or paraphrases presented as quotes.
- **Personal data.** Use hashed authors only, and never name people from forums or reviews.

**Done when:** `validate --report` passes and `next` prints DONE.
