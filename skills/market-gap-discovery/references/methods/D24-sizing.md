# D24 · Bottom-up sizing

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Bottom-up TAM / SAM / SOM for SaaS (target accounts × annual revenue per account); the "right size" test from the research-gap method | P6 Appraisal | synthesizer (inputs), orchestrator (runs) | core |

**Use when:** after the red team, when `next` issues `assign --phase sizing` and then `SPAWN synthesizer`.

**Why:** Top-down market sizes ("the invoicing market is worth $X billion") say nothing about whether a small product can reach enough paying accounts. Bottom-up sizing multiplies counts you can source by prices you have observed. It also turns the uncertain parts (how many accounts you can reach, convert and win) into explicit assumptions that validation can test.

**Inputs**
- `gaps/sizing-assign.json`: the cards to size, which are the survivors and weakened cards that passed the gates.
- `analysis/price_ladder.csv` and `analysis/competitor_matrix.csv`.
- `gaps/judgments.jsonl` (reach channels).
- The protocol's `geography`, `languages` and `ambition`.

**Procedure**
1. **`accounts`** (low, base, high): estimate the number of target accounts in the card's population and setting.
   - Source each count from something you can snapshot: official business statistics or registers, professional-association membership counts, marketplace install counts (WordPress active installs, Atlassian installs), community sizes, job-post counts.
   - For marketplace counts, use the API adapters, which return installs, ratings and totals and log the query: `gapscan.py fetch RUN wp-plugin --slug S`, `wp-search --query Q`, `apple-search --query Q`, `atl-search --query Q`; `hn-counts` and `se-counts` give mention and question volumes. Do not `snapshot` API URLs: robots.txt blocks several of them (a live sizer was blocked on api.wordpress.org, while `fetch wp-plugin` returned the same install counts).
   - For a web page, snapshot it with `gapscan.py snapshot RUN URL`. Put the URL and a description in `source`, and the hash (printed by fetch or snapshot) in `snapshot`.
2. **`arpa_year_usd`** (annual revenue per account), from the price ladder:
   - low: the cheapest relevant paid tier × 12
   - base: the median relevant tier × 12
   - high: the highest tier this segment would plausibly buy, × 12
   
   Name the tiers you used in `source` or `note`.
3. **`reachable_share`** (SAM ÷ TAM), from the reach channels and the scope: geography, language and channel coverage. Explain it in `rationale`.
4. **`conversion`** and **`win_rate`** are funnel assumptions, not facts. Set `assumption: true` and give a rationale for each. They become Test Card candidates for validation.
5. Write `gaps/sizing-inputs.json` (sizing-inputs.schema.json), with one entry per gap id under `gaps`. The orchestrator then runs `gapscan.py size RUN`.

**Output:** `gaps/sizing.json`. Per gap: TAM, SAM and SOM (low, base, high), the inputs, the sources, and the list of assumptions to validate.

**Metrics and checks**
- TAM = accounts × ARPA; SAM = TAM × reachable share; SOM = SAM × conversion × win rate. Each is computed low × low, base × base and high × high, so the range is deliberately wide.
- `size` rejects accounts or ARPA without a source, shares outside 0–1, and any range where low ≤ base ≤ high does not hold.
- SOM is never "x% of TAM". It is built from funnel steps that each have a rationale, and conversion and win rate are listed as assumptions.

**Lenses (D26):** for clone-wedge, port, down-market, replace and hosted-oss cards, count accounts bottom-up from the base products' users where a source gives them (installs and rating counts in `landscape/traction.jsonl`, with their snapshots), then apply a switching share as an assumption. The scan's ambition math (customers needed at the incumbents' median price) is a reach check, not a size.

**Pitfalls**
- **Counting the whole category instead of the card's population**: all freelancers, when the card is about freelance translators who invoice foreign clients.
- **Aspirational ARPA.** Use prices you observed. A premium tier nobody in the segment buys is not ARPA.
- **Precision theatre.** Report ranges and their sources; a single number hides the uncertainty the dossier must show.
- **Sizing killed or gated cards.** Size only the cards in the assignment.
- **Mixing currencies.** `arpa_year_usd` is in US dollars. When the price ladder shows another currency, convert at a rate you snapshot, and name the rate in `note`.

**Done when:** `gaps/sizing.json` covers every card in the sizing assignment, and `next` has moved on to `score`.
