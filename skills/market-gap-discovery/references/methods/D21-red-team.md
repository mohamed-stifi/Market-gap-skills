# D21 · Red team and pre-mortem

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Peer review and the doctoral check "is the gap real?"; failed-startup analysis; Porter's Five Forces adapted to SaaS; platform risk; pre-mortem (Klein 2007) | P6 Appraisal | red-team, orchestrator | core |

**Use when:** `next` issues `SPAWN red-team` with assignments covering the cards that passed `cards check`.

**Why:** Researchers confirm a gap by trying to show it isn't one: searching harder, in other languages and in grey literature. The red team does the same for a market gap, and its job is to kill the card. Cards that survive an honest attempt are worth validating; cards that die save the human time and money. The red team also records the judgments that scoring needs (gates, platform risk, right to win, reach channels), each with a written rationale, so nothing in the ranking is an unexplained opinion.

**Inputs**
- Your assignment: the cards to attack and your output paths.
- `gaps/cards.jsonl`, `landscape/entities.jsonl`, and `landscape/screening.jsonl` (entities screened `EX-DEAD`).
- `evidence/ledger.jsonl`, `analysis/competitor_matrix.csv`, `analysis/price_ladder.csv`.
- `lexicon/lexicon.json` (synonyms and tool names) and the protocol's `founder_fit`, `languages` and `geography`.

**Procedure** (for each card)
1. **Search for an existing solution, adversarially.** Restate the card's job and population as queries, using lexicon synonyms, in the protocol languages and in the other main languages of the segment's markets. Use the tier-1 sources (`gapscan.py fetch RUN gh-repos --query Q`, `wp-search`, `apple-search`, `atl-search`, `yc`, `hn --tags show_hn`), plus marketplace listings and recent launches through your web-search tool.
   - Log each web search with `gapscan.py log-query RUN --source web --query Q --count N`; `fetch` logs its own queries.
   - Record at least three searches in `searches`, across at least two channel families.
2. **Snapshot every candidate solution** with `gapscan.py snapshot RUN URL`. Record it in `existing_solutions` with `covers`:
   - full: same job, same population, same setting, comparable price
   - partial: covers part of the job, or another segment, price or language
   - none
3. **Look for failed attempts:** entities screened `EX-DEAD`, shutdown announcements, post-mortems, abandoned repositories, "we're closing" posts. Record each in `failed_attempts` with its lesson (timing, market too small, distribution, platform rules).
4. **Write `why_empty`** by testing the card's explanation against what you found. Common answers: market too small, hard problem, regulated, only recently possible (why-now), overlooked, blocked by a platform, served well enough by a substitute.
5. **Rate the SaaS Five Forces** as low, medium or high, and add `notes`:
   - `rivalry`
   - `new_entrants`: how easily another small, agent-built product could copy it
   - `substitutes`: spreadsheets, agencies, in-house tools, doing nothing
   - `buyer_power`: switching costs and the segment's price sensitivity
   - `supplier_power`: host platforms, marketplaces, model or API vendors, a single acquisition channel
6. **Run a pre-mortem.** Imagine the product launched and failed a year later, and write at least three specific reasons in `premortem`. Each reason should point to something checkable.
7. **Decide `verdict`:**
   - killed: an existing solution covers the gap fully for the card's population and setting, and the supporting evidence doesn't show it failing them
   - weakened: partial coverage, a strong incumbent, a good-enough substitute, or failed attempts whose cause is still unaddressed
   - survives: no full or partial coverage after at least three logged searches across two channel families, and `why_empty` is explained
8. **Fill `judgment`** (judgment.schema.json), with a rationale for each judged value:
   - `regulatory_load`: low, medium or high (licences, data-protection exposure, sector rules)
   - `human_ops_burden`: low, medium or high (how much a human must do each week: sales calls, compliance, support)
   - `agent_buildability`: yes, partial or no (could a coding agent build and maintain the MVP?)
   - `platform_risk`:
     - 0: no single-platform dependence
     - 1: integrates with platforms but runs and sells independently
     - 2: distributed mainly through one marketplace, or depends on one platform's API for its core value
     - 3: lives inside one host platform that can change its rules, copy the product or cut access
   - `tos_feasible`: can it be built and marketed without breaking any platform's terms?
   - `right_to_win`, judged against the protocol's `founder_fit` (skills, budget, hours, unfair advantages):
     - 0: none
     - 1: generic
     - 2: relevant skills or access
     - 3: a specific advantage (an audience, data, domain expertise)
   - `reach_channels`: where the ICP gathers (community, marketplace, keyword, directory, integration, newsletter, other), each with a URL, its size when known, and evidence (EV ids or snapshot hashes)
9. Write `gaps/redteam/GAP-NNN.json`. The orchestrator then runs `gapscan.py merge RUN --phase redteam`, which validates the files and collects the judgments into `gaps/judgments.jsonl`.

**Output:** one `gaps/redteam/GAP-NNN.json` per card (redteam.schema.json, with `judgment` embedded).

**Metrics and checks**
- The schema requires at least three `searches` and at least three `premortem` reasons.
- Killed cards are excluded from scoring. The dossier lists them with the evidence that killed them.
- A judgment without a rationale fails the schema check.

**Pitfalls**
- **Searching only in English, or only with the card's own words.** Use the lexicon's synonyms and competitor names, and the segment's languages.
- **Going easy on the card.** Your role is adversarial. "Survives" should cost effort; if three quick searches found nothing, try two more channels before deciding.
- **Judging right to win on optimism.** Use the protocol's `founder_fit` as it is, not what a founder could learn.
- **Missing platform rules.** A gap that exists only because a platform forbids something is not feasible. Set `tos_feasible` to false and explain why.

**Done when:** every assigned card has a valid `gaps/redteam/GAP-NNN.json`, and `merge --phase redteam` has run.
