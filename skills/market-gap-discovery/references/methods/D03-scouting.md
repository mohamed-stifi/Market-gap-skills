# D03 · Independent scouting in sampling units

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Doctoral teams' independent searching, each researcher in their own sheet; PRISMA-S search reporting (Rethlefsen et al. 2021); sampling occasions in capture–recapture (Kastner et al. 2009; Chao & Colwell 2017) | P2 Landscape | scout | core |

**Use when:** for every scout assignment in every landscape round. The probe scout (D04) follows the same rules.

**Why:** The saturation estimate (D04) treats each **sampling unit** as an independent capture occasion. A sampling unit is one scout searching one channel family in one round. The estimate counts which units found each product: products found by only one unit (Q1) are the signal that more remain unseen.

That logic fails as soon as units stop being independent. It happens when a scout searches for products it saw earlier, reads another scout's list, or files a find under the wrong unit. In each case overlap rises without the search becoming more complete, and the run stops too early.

The rules below keep units independent. Logging every search (PRISMA-S) makes the search reproducible, and it lets the PRISMA flow report what was identified, and where.

**Inputs**
- Your assignment:
  - `persona`
  - one `channels` entry per unit, each with `unit_id`, `family` and `kinds`
  - your share of the `query_blocks`
  - output path and limits
- `assets/channels.json` for each family's tier, adapters, access notes and the entity kinds it can surface.

**Procedure**
1. Read your assignment and the files in its `read` list, and nothing else in the run folder. Never open other scouts' outputs, `landscape/entities.jsonl` or files from earlier rounds.
2. Work through your units one at a time. Search each unit's channel family only, and only with your assignment's query blocks. You may adapt a block to the channel's syntax (quotes, `site:` filters, Hacker News tags), but do not add terms.
3. Run each search through the right path:
   - **Tier-1 families** (`hn`, `se`, `gh`, `wp`, `apple`, `atl`, `yc`): `gapscan.py fetch RUN <adapter> --query "<block>" --unit <unit_id> --by <assignment_id>`, with the adapter listed for that family in `assets/channels.json` (for example `hn`, `se`, `gh-repos`, `wp-search`, `apple-search`, `atl-search`, `yc`). Fetch saves the raw response and logs the query for you.
   - **`web`**: use your web-search tool, then immediately run `gapscan.py log-query RUN --source web --query "<exact query as run>" --count <results seen> --unit <unit_id> --by <assignment_id>`.
   - **`directories`**: run a web search restricted to the directory site (illustrative: `site:zapier.com/apps <block>`) and log it the same way. Read listing pages only, never reviews.
4. Let your persona decide which results to open and how deeply to read: a buyer opens comparison lists, a builder opens repositories and integration pages. The persona shapes your judgement; the query words come from the blocks.
5. Record one item for every in-scope entity you saw in that unit's results:
   - `name`.
   - `url`: the product's own homepage if you can see it, otherwise its marketplace listing (an app store, WordPress, Atlassian or Shopify page). Never use a general directory such as AlternativeTo as `url`: it refuses automated fetches (HTTP 403), so the entity could never be screened. If a directory shows no homepage, leave the product out and name it in `notes`.
   - `kind`: `product` (software, plugin, extension, app), `community` (a forum, Q&A tag or group where the segment gathers) or `directory` (a site listing many products).
   - `listing_url` when the item came from a marketplace or directory, and `evidence_url` for the page where you saw it.
   - `query_index`: the position of the query in that unit's `queries` list.
   - A short `note`, if useful.
   
   Record only what the results showed. Never add a product from memory, and never move finds from one unit to another.
6. Skip every result on an excluded domain or path (`assets/channels.json` → `excluded` and `excluded_paths`, plus `protocol.sources.excluded_extra`). If a script exits with code 2 (robots.txt, rate limit, block), stop that query; the script records the coverage gap.
7. Stop when one of these happens, and set `stop_reason` and `tool_calls` to match:
   - the blocks are used up: `exhausted`
   - you reach your tool-call limit (`budget.scout_tool_calls`, 20): `budget`
   - you hit the assignment's item limit: `limit`
   - every channel is blocked: `blocked`
8. Write one `landscape-output` JSON to the output path in your assignment. Set `mode` to `landscape`, or `probe` for the probe. Include one `units` entry per assigned unit, each with its `queries` and `items`.

**Independence rules**
- Queries come only from your assignment's query blocks, adapted for syntax only.
- Never search for names you found during the round. Following names is snowballing (D05), a separate phase whose finds are kept out of the estimator.
- Never read other scouts' files, the merged entity list, or earlier rounds.
- Log every web-tool search with `gapscan.py log-query`. Tier-1 searches go through `gapscan.py fetch`, which logs automatically.
- A find belongs to the unit whose search returned it, and only to that unit.

**Output:** `landscape/round-NN/scout-X.json` (or the probe path in your assignment), schema `landscape-output`, plus query lines in `queries.jsonl`.

**Metrics and checks**
- `merge --phase landscape` validates your file against `landscape-output` and computes canonical keys (`dom:`, `gh:`, `wp:`, `app:ios:`, `atl:`, `sub:`, `se:`). Do not invent keys.
- The incidence built from your units feeds Q1, Q2 and T in `saturation` (D04).
- Per-unit query and result counts feed the PRISMA identification numbers (`gapscan.py prisma RUN`).

**Pitfalls**
- **"Helping" by searching for well-known leaders.** It raises overlap and hides the products nobody has seen yet.
- **Recording only famous products.** Niche tools found by one unit are exactly what Q1 measures.
- **Reading reviews in this phase.** Reviews are evidence (D08), and some review sites are excluded sources.
- **Unlogged searches.** The PRISMA-S log must show every query exactly as it was run.

**Done when:** your output validates against `landscape-output`, every assigned unit is present, and every query you ran appears in the log.
