# D11 · Demand signals and bursts

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Bibliometric trend analysis and burst detection (Kleinberg 2002; used by CiteSpace to flag emerging research fronts) ↔ monthly mention counts and interest series for market terms; Wilson score intervals for every reported proportion | P3 Evidence | miner | conditional |

**Use when:** in evidence round 1, and in later rounds if the orchestrator asks. It only applies when `doctor` found at least one tier-1 signal source reachable.

**Why:** Quotes show that a pain exists. Signals show whether attention to it is growing. Research spots emerging fronts through bursts: periods when a term's share of publications jumps above its own baseline. The same test works on the share of Hacker News items or Stack Exchange questions that mention a market term each month.

A recent burst supports a why-now catalyst (D12), but the absence of a burst does not disprove demand. A short, noisy series can look like a burst by chance, so each burst is compared against shuffled timelines.

**Inputs**
- Your assignment.
- `lexicon/lexicon.json`: category names, the strongest pain and workaround terms, incumbent names.
- The protocol: `as_of`, `recency_days`, `languages`.
- `doctor.json`.

**Procedure**
1. Pick a handful of terms from the lexicon that name the job, the category or the pain. Prefer multi-word phrases over single words that have other meanings.
2. Choose a monthly window that ends at `as_of`. It should be long enough that the baseline is not dominated by the last few months; two to three years of monthly points works well.
3. Fetch **proportion series**. For each month, r is the number of items that mention the term and d is the number of all items, so platform growth cancels out.
   - `gapscan.py fetch RUN hn-counts --query "<term>" --from YYYY-MM --to YYYY-MM [--tags story|comment] --by <assignment_id>`
   - `gapscan.py fetch RUN se-counts --query "<term>" --from YYYY-MM --to YYYY-MM --site <site> --by <assignment_id>`. Use the Stack Exchange site where your segment actually asks questions.
   
   Each command writes a `signal` file to `evidence/signals/` with `kind` = `proportion`.
4. Fetch an **absolute series** for the category's Wikipedia article: `gapscan.py fetch RUN wiki-views --article "<Article title>" --from YYYY-MM --to YYYY-MM --by <assignment_id>` (`kind` = `absolute`). This needs `MGD_CONTACT`. If it exits with code 2, note it in your summary instead of retrying; the orchestrator decides whether to raise a human task.
5. Use **tier-2 search volume** (Keyword Planner, DataForSEO, SerpApi, Google Trends alpha) only when it appears in `protocol.sources.tier2_enabled`. Otherwise mention in your summary that it would help.
6. Collect **job demand**. Run `gapscan.py fetch RUN hn-hiring --query "<job or tool>" --by <assignment_id>`. Posts hiring people to do the job by hand become evidence records under D08: `source_type` `job-post`, usually stance `wtp` and strength S4 (D10).
7. Do not compute shares, trends or bursts yourself, and never write a bare percentage in a record. The orchestrator runs `gapscan.py bursts RUN`.

**Output:** `evidence/signals/SIG-*.json` (schema `signal`), written by `fetch`, and `evidence/bursts.json`, written by `bursts`.

**Metrics and checks**
- **Kleinberg two-state model on proportion series.**
  - The burst state's rate is `bursts.s` (2) × the baseline share.
  - Moving up into the burst state costs `bursts.gamma` (1) × ln(number of periods); moving down is free.
  - A burst's weight is the cost the burst state saves over its duration.
- **Shuffle test.** The test reorders the months at random `bursts.shuffles` (200) times. A burst is significant when p < `bursts.alpha` (0.05).
- **Absolute series** (pageviews) have no denominator. Treat them as context about interest levels, not as burst evidence.
- **Shares.** Any share reported anywhere ("x% of reviews mention…") carries a 95% Wilson interval computed by the scripts.

**Pitfalls**
- **Terms that are also common words** (a product named after an everyday noun). The counts then measure the word, not the market.
- **Mistaking platform growth for topic growth.** This is why proportion series divide by all items in the month.
- **Reading one viral thread as a trend.** The shuffle test and the burst's duration guard against this.
- **Assuming no burst means no demand.** Stable demand is common in boring, profitable niches.

**Done when:** each selected term has a valid signal file (or a coverage gap recorded by the script), and `bursts` has run on the proportion series.
