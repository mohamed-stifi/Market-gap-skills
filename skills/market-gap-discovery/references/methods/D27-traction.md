# D27 · Traction: proven demand from marketplace numbers

| Origin | Phase | Roles | Status |
|---|---|---|---|
| App-store analysis for software engineering (Harman, Jia & Zhang 2012; Martin et al. 2017): installs, ratings and reviews as observable evidence of use; revealed preference over stated preference | P2 Landscape | orchestrator (runs) | core |

**Use when:** `next` issues `RUN gapscan.py traction RUN` after the landscape map (both depths).

**Why:** Quotes show that people feel a pain; installs, rating counts and paid plans show that they already act on it. Those numbers sit in the marketplace API responses the scouts saved while searching (`wp-search`, `apple-search`, `atl-search`), so reading them costs no subagent and no network. In the first live run, saved responses gave numbers for 127 of 151 marketplace products. Every number keeps the snapshot it came from, so it is as checkable as a verified quote.

**Inputs:** included, verified products in `landscape/entities.jsonl` with a marketplace key (`wp:`, `app:ios:`, `atl:`), directly or as an alias; the run's API snapshots in `snapshots/`.

**Procedure**
1. **Orchestrator:** run `gapscan.py traction RUN`. It:
   - reads every saved WordPress.org, App Store and Atlassian Marketplace response and keeps the newest numbers per product: installs, rating count, average rating (WordPress's 0-100 scale divided by 20), the 1-5 star distribution when given, and the App Store price;
   - looks up products still missing, up to `traction.max_lookups`: WordPress.org `plugin_information` and the iTunes lookup API (`gapscan.py fetch RUN apple-lookup --id ID` does the same by hand). Failures are coverage gaps; Atlassian has no documented lookup by app id, so those products rely on saved search responses;
   - writes `landscape/traction.jsonl`, one row per product with the snapshot sha.
2. Use `--offline` to read saved responses only (no network).
3. Products without a row fall back to the mapper's `signals` fields, marked `via: mapping`.
4. The lens rules (D26) turn the numbers into percentiles within each store: installs and rating counts are not comparable across WordPress.org, the App Store and Atlassian. A product is **proven** in the top third (`opportunity.traction_quantile`) and **poorly rated** in the bottom third of average ratings (`opportunity.low_rating_quantile`), counting only averages over at least `opportunity.min_ratings_for_rating` ratings.

**Output:** `landscape/traction.jsonl` (entity_id, key, source, installs, ratings_count, rating_avg, ratings_dist, price_usd, snapshot, retrieved_at, via).

**Metrics and checks:** `state.json` → `traction` records how many marketplace products got numbers, how many were looked up, failed or skipped. The scan report states the share of products with numbers; products without them are never ranked as proven.

**Pitfalls**
- **Treating absence of numbers as low traction.** Most SaaS products have no public install count. Unknown is neutral.
- **Comparing raw counts across stores.** Use the within-store percentiles the scripts compute.
- **Snapshotting API URLs by hand.** robots.txt blocks several API paths; the adapters are the sanctioned route.

**Done when:** `landscape/traction.jsonl` exists and is newer than the landscape map.
