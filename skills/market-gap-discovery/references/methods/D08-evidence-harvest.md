# D08 · Evidence harvest by stance

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Harvesting "limitations" and "future work" sections in research ↔ low-star reviews, public roadmaps and feature requests in markets; review and forum mining; workaround hunting; switching stories (JTBD); balancing with praise and contrary evidence; statistical stopping for ranked screening (Callaghan & Müller-Hansen 2020) | P3 Evidence | miner | core |

**Use when:** in every evidence round. That means after mapping for round 1, and again whenever theme saturation (D14) asks for more.

**Why:** A gap is a claim about people's experience. It needs what people said and did, in their own words, traceable to a page.

Researchers find gaps by reading what authors admit they could not do. Vendors admit limitations too, on roadmaps, feature-request boards, changelogs and "not supported" pages. Users describe the same limitations in low-star reviews, forum threads and Q&A.

Mining by stance (pain, wish, switch, workaround, wtp, praise, contra) prevents the classic bias of desk research, which is collecting only complaints:
- **Praise** shows which incumbents already satisfy a job; it is what the satisfaction side of the gap map is computed from (D16).
- **Contra** evidence shows where a supposed pain is rare or already solved; it feeds honest certainty (D22).

Large result pools are screened in rank order and stopped by a statistical test. That way the miner neither stops arbitrarily nor spends the budget on the long tail.

**Inputs**
- Your evidence assignment: the channel group, the entities and communities to cover, the stances to prioritise, the output path and limits.
- `lexicon/query-blocks.json` and `lexicon/lexicon.json`.
- Canonical entity keys (provided in your assignment) for `entity_ids`.
- D09 (integrity rules) and D10 (strength grading). Both apply to every record you write.

**Procedure**
1. Read your assignment. Cover its entities, communities and stances in the order listed. The default `evidence.miners` (3) split the work three ways: marketplaces and vendor pages; communities and Q&A; and signals plus why-now (D11, D12).
2. Build queries from the lexicon using these stance templates. Fill `<tool>`, `<job>` and `<category>` with lexicon terms; the examples are illustrative.
   - pain: `"<tool>" too slow|expensive|complicated`, `<job> nightmare`, `problem with <tool> <job>`
   - wish: `I wish <tool>`, `is there a tool that <job>`, `feature request <job>`
   - switch: `switched from <tool>`, `alternative to <tool>`, `cancelled <tool> because`
   - workaround: `spreadsheet for <job>`, `template <job>`, `script to <job>`, `zapier <job>`, `hired someone to <job>`
   - wtp: `<tool> pricing worth it`, `paying for <tool>`, `would pay for <job>`, plus explicit budget or price talk
   - praise: `love <tool>`, `<tool> saved us`
   - contra: `<tool> works fine for <job>`, `don't need <category>`
3. Mine through the scripts, so that every record has a snapshot:
   - **Reviews:** `gapscan.py fetch RUN apple-reviews --id ID`, `fetch RUN wp-reviews --slug S`, `fetch RUN atl-reviews --key K`. Read the low ratings first, but sample 4–5★ reviews too.
   - **Communities and Q&A:** `fetch RUN hn --query Q --tags comment` (or `ask_hn`), `fetch RUN se --query Q`, and `fetch RUN gh-issues --query "<tool> feature request"`.
   - **Vendor admissions** (the market's "limitations sections"): public roadmaps, feature-request boards, changelogs, "not supported" doc pages and pricing pages, via `gapscan.py snapshot RUN URL`.
   - **People hired to do the job by hand:** `fetch RUN hn-hiring --query Q`.
   - **Pages found with your own search tool:** log the search with `log-query`, then `snapshot` each page you quote.
   - Add `--unit <your miner id>` and `--by <assignment_id>` to fetch and log calls so every query traces back to you.
4. For each relevant passage, write one record (schema `evidence`). Leave out `id` and `verification`; the scripts add them.
   - `url` (the permalink of the post or review), `source` (the adapter name, or `web`), `source_type`, `platform`, `domain`, and `snapshot` (the hash printed by fetch or snapshot).
   - `quote`: verbatim, at most `evidence.quote_max_chars` (280) characters, cut at sentence boundaries.
   - `stance`; `strength` with its `strength_note` (D10); `credibility`; and `indirect` where it applies.
   - `entity_ids`: the canonical keys of the products the quote is about, if any.
   - `author_hash` (from the fetch item, or from `gapscan.py hash-author RUN <platform> <handle>`), `posted_at`, `retrieved_at`, `language`, `rating` (for reviews), `miner` and `round`.
   
   Illustrative line: `{"url": "https://news.ycombinator.com/item?id=…", "source": "hn", "source_type": "forum", "snapshot": "3f9a…", "quote": "We export every invoice to a sheet and fix the VAT lines by hand each month.", "stance": "workaround", "strength": "S3", "credibility": "independent", "author_hash": "ah_…", …}`
5. Write one record per distinct claim. If one post contains both a pain and a workaround, write two records with two different quotes.
6. Collect praise and contra on purpose. For every incumbent you mine, also run its praise and contra templates. Record what you find; if a search returns nothing, the query log shows that it was run.
7. Use the stopping test for large ranked pools. When a query's result pool exceeds `evidence.stoptest_pool_min` (200) items, as shown by the total hits the source reports:
   1. Screen results in the source's rank order and count the relevant ones (R).
   2. Draw a random sample of n results from the N you have not screened, and count the relevant ones in it (k).
   3. Run `gapscan.py stoptest --unseen N --sample-n n --sample-k k --found R`. It uses recall `evidence.stoptest_recall` (0.95) and confidence `evidence.stoptest_confidence` (0.95).
   4. On STOP, leave that pool. On CONTINUE, keep screening in rank order and test again.

   If your tool budget cannot cover the test, screen the top of the pool and move on: the fetch log already holds total hits and items read, and `prisma` reports each untested large pool as a limitation. Spend the test on the pool closest to the protocol's segment.
   
   Record the numbers in the search log: `gapscan.py log-query RUN --source hn --query "…" --count TOTAL --filters "stoptest N=… n=… k=… R=… STOP" --by <assignment_id>`.
8. Stop when your list is covered or at `budget.miner_tool_calls` (25) tool calls. Write all records as JSONL to the output path in your assignment (`evidence/round-NN/miner-X.jsonl`).
9. **Orchestrator:** run `gapscan.py merge RUN --phase evidence`. It validates, de-duplicates on URL and quote, assigns `EV-` ids and appends to `evidence/ledger.jsonl`. Then run `gapscan.py verify RUN` (D09).

**Output:** `evidence/round-NN/miner-X.jsonl` (schema `evidence`), merged into `evidence/ledger.jsonl`.

**Metrics and checks**
- Only verified records count. `verify` reports the verified share, and so does the PRISMA flow.
- A gap card needs at least `gap_card.min_records` (5) verified records, from at least `gap_card.min_domains` (3) domains, `gap_card.min_source_types` (2) source types and `gap_card.min_authors` (2) authors (D20). So mine across sources rather than deep inside one thread. Your assignment's `inputs.diversity` lists the ledger's domain shares and the domains to avoid. In a live run, 158 of the first 165 records came from two sites, and 11 of 12 gap cards then failed on domain count alone.
- Theme saturation, not the miner, decides whether another evidence round is needed (`gapscan.py themes RUN`, D14).
- **Targeted round.** After `cards check`, if fewer than `evidence.target_candidates` (3) cards pass and some insufficient cards fail only on evidence counts (domains, source types, records, authors, missing demand), `next` runs one targeted round (`evidence.max_targeted_rounds`, 1). Each miner gets one such card (`mode` = `evidence:targeted`): its codes, shortfall and current domains. Mine those jobs only, from domains the card does not have, and record praise and contra as honestly as pain. In the live run this lifted passing cards from 1 to 3, and the red team then killed two of them: the targeted round tests near-misses, it does not rescue them.

**Pitfalls**
- **Paraphrasing.** A paraphrase fails verification and counts for nothing.
- **One loud thread.** Many records from one author on one domain add almost nothing.
- **Reading only 1★ reviews.** You lose the praise that measures satisfaction and the contra that keeps certainty honest.
- **Stopping because "the last 50 results were irrelevant".** In screening studies, that rule missed its recall target far more often than the statistical test did.
- **Using vendor marketing as user evidence.** Mark it `credibility` = `vendor` (D10).

**Done when:** your assigned entities, communities and stances are covered (or the budget is spent) and every line validates against `evidence`.
