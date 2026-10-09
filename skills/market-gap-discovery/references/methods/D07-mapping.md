# D07 · Systematic mapping and classification

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Systematic mapping studies in software engineering (Petersen et al. 2008, 2015): keyword the abstracts, cluster the keywords into a classification scheme, then classify every included study | P2 Landscape (closing step) | synthesizer | core |

**Use when:** once the landscape is closed (after snowballing and the screening audit) and before evidence mining.

**Why:** A list of products is not yet a map. Mapping studies build their categories bottom-up: read each paper's abstract, note keywords, cluster them into a scheme, then classify every paper. Crowded and empty categories then become visible.

Doing the same with products produces the axes the later analysis needs:
- the solution **approach**, which becomes the gap-map columns (D16)
- **pricing models**, for the price ladder (D15)
- **platforms**, for variation (D19)
- the **competing factors** of the strategy canvas (D15)

Building the scheme from the products' own pages, rather than from assumptions, keeps it grounded and reproducible.

**Inputs**
- The mapping assignment, which lists the included, verified products.
- The homepage snapshots made by `entities verify`.
- The protocol: `competing_factors` if given, plus `business_models` and `variation_dimensions`.

**Procedure**
1. **Keywording.** For each product, read its homepage snapshot (`snapshots/<sha>.txt`). Snapshot its pricing page with `gapscan.py snapshot RUN URL --by synthesizer`. Note a few keywords for what it is, who it is for, how it is delivered and how it charges.
2. **Scheme.** Cluster the keywords into values for six facets. Give each value an `id` (lowercase, hyphenated), a `label` and a one-sentence `definition`:
   - `approach`: how the job gets solved. Illustrative ids: `horizontal-saas`, `vertical-saas`, `plugin`, `browser-extension`, `marketplace-app`, `spreadsheet-template`, `open-source`, `api`, `service`.
   - `category`: the product category in neutral words.
   - `segment`: who the product says it serves.
   - `pricing_model`: illustrative ids `free`, `freemium`, `subscription`, `usage`, `one-time`, `open-source`.
   - `platform`: web, mobile, a host platform (Shopify, WordPress, Atlassian…), desktop.
   - `deployment`: cloud, self-hosted, hybrid.
   
   Keep the values within one facet mutually exclusive. When something truly fits nowhere, add an `other` value rather than forcing it.
3. **Competing factors.** List 3–12 factors the products compete on, with ids `CF01`, `CF02`, … plus a label and a definition. Examples: price, ease of setup, integrations, local-language support, compliance features, support. If the protocol lists `competing_factors`, start from them and add only what the pages show.
4. **Classification.** Write one `entity-attributes` line per included product:
   - `entity_id`
   - `approach`, `category`, `segments`, `platform` and `deployment`, using only ids from your scheme
   - `pricing`: `model`; `min_paid_month` (the cheapest paid plan per month; divide annual-only prices by 12); `currency` (ISO code such as `USD`, `EUR`); `free_tier`; `per_seat`; and `snapshot` (the pricing page's hash)
   - `languages`, `integrations`, and a neutral one-line `description`
   - `evidence`: the snapshot hashes you used
5. **Signals.** Where a tier-1 source has them, fill `signals` (`installs`, `ratings_count`, `rating_avg`, `stars`) from the scripts, not by reading numbers off pages. Use `gapscan.py fetch RUN wp-plugin --slug S`, `apple-search --query Q`, `atl-search --query Q` or `gh-repos --query Q`.
6. Do not write attribute lines for communities and directories. They are used later as reach channels and seeds.
7. Write `landscape/classification.json` (schema `classification`) and `landscape/entity-attributes.jsonl` (schema `entity-attributes`) to the paths in your assignment. The orchestrator then runs `gapscan.py merge RUN --phase mapping`.

**Output:** `landscape/classification.json` and `landscape/entity-attributes.jsonl`.

**Metrics and checks**
- Every attribute value must be an id defined in `classification.json`.
- Every included product has exactly one attributes line. Pricing figures need the pricing-page snapshot.
- When prices are hidden ("contact sales"), leave `min_paid_month` null rather than guessing. The price ladder (D15) treats null as unknown, not as zero.
- The facet counts give a first, coarse view of crowded approaches. The real supply analysis comes after coding (D15, D16).

**Pitfalls**
- **Copying marketing categories** ("all-in-one platform"). Describe what the product does.
- **Mixing currencies or billing periods** in `min_paid_month`. Normalise to per month and record the currency.
- **Inventing job labels now.** Which jobs each product serves is mapped later, against the frozen codebook (D15).
- **Over-splitting facets** until every product has its own value. The scheme must group products to show patterns.

**Done when:** both files validate, every included product is classified, and `merge --phase mapping` succeeds.
