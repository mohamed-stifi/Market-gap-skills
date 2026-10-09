# D15 · Competitor matrix, price ladder, strategy canvas

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Concept matrix (Webster & Watson 2002) ↔ competitor matrix; strategy canvas and value curves (Kim & Mauborgne, Blue Ocean Strategy); price ladder; substitutes from Porter's Five Forces; platform dependency | P4 Coding and synthesis | synthesizer, orchestrator | core |

**Use when:** coding is accepted or provisional and themes are done, and `next` issues `assign --phase supply`.

**Why:** In a literature review, the concept matrix (articles × concepts) shows which concepts nobody has studied. The market version, products × jobs and attributes, shows which jobs nobody serves well and where every incumbent looks the same. Supply must be mapped from what products actually offer on their own pages, snapshotted, not from memory or reputation, because the gap map (D16) sets supply against demand.

**Inputs**
- `analysis/supply-assign.json`: your batch of entities, the frozen codebook's J- and O- codes, and the competing factors from `landscape/classification.json`.
- `landscape/entity-attributes.jsonl` (approach, category, segments, pricing, platform, deployment, languages, integrations, signals) and `landscape/entities.jsonl`.
- Existing snapshots listed in each entity's attributes.

**Procedure**
1. For each entity in your batch, open its product, pricing, docs and changelog pages with `gapscan.py snapshot RUN URL`. Reuse existing snapshots when they already answer the question. Work only from snapshotted pages.
2. Record `jobs_served`: the J- and O- codes the product demonstrably supports, meaning a documented feature or workflow, not a slogan. If a page claims a capability vaguely, leave the job out and say why in `note`.
3. Record `factor_levels` for every competing factor id (CF01, CF02, …) from classification.json:
   - 0: absent
   - 1: basic
   - 2: standard for the category
   - 3: best in class
   
   Base each level on the snapshot and on how the feature compares across the batch, not on brand reputation.
4. List the snapshot hashes you used in `evidence` (at least one). Write one line per entity to the output file named in your assignment (supply.schema.json).
5. Include substitutes on purpose: spreadsheets and templates, agencies and freelancers, in-house tools, and doing nothing. They appear as `approach` values in classification.json (D07), and as entities when a concrete substitute exists (a template listing, an open-source script). A gap analysis that ignores substitutes overestimates how empty the space is.
6. **Orchestrator:** run `gapscan.py merge RUN --phase supply`, then `gapscan.py matrix RUN`.

**Output** (written by `matrix`)
- `analysis/competitor_matrix.csv`: entities × (approach, category, segments, pricing model, platform, deployment, languages, integrations, jobs served).
- `analysis/price_ladder.csv`: entities sorted by pricing model and lowest paid monthly price, per currency, with free-tier and per-seat flags.
- `analysis/strategy_canvas.csv`: competing factors × entities, with offering level 0–3. Each entity's row is its value curve.
- `analysis/pain_by_entity.csv`: verified pain and praise per entity and code, counted as distinct authors from coded evidence.

**How to read the outputs** (synthesizer in P5, writer in P7)
- **Concept matrix:** job columns with few ticks are neglect leads. Rows that match across most columns mean a crowded, undifferentiated category.
- **Value curves:** if most curves have the same shape, incumbents compete on the same factors. That is a problematization lead (D18).
- **Positioning map:** in the dossier, plot lowest paid price (price ladder) against the number of jobs served (matrix). An empty quadrant is only a lead, because a quadrant can be empty for lack of demand. The gap map (D16) decides.
- **Price ladder:** a jump between tiers (nothing between free and an expensive team plan) is a price-gap lead. Compare only within the same currency and billing period.
- **Platform dependency:** note incumbents whose `platform` is a single host (one marketplace, one CRM, one e-commerce platform). The red team (D21) uses this to rate platform risk 0–3 for each gap.

**Metrics and checks**
- Every supply line validates against supply.schema.json and cites at least one snapshot.
- `matrix` reports entities without a supply line and factors with no level, so they can be completed before the gap map.

**Pitfalls**
- **Mapping supply from memory or from reviews.** Reviews are demand evidence; supply comes from the product's own pages.
- **Mixing currencies or monthly and annual prices** on one ladder.
- **Treating a feature checklist as satisfaction.** A product can serve a job and still be hated for it (`pain_by_entity.csv`). D16 combines both.
- **Skipping non-software approaches.** Templates, agencies and in-house tools are often the real competitors for small segments.

**Done when:** every included entity has a supply line, `matrix` has written all four CSVs, and `next` has moved on to `gapmap`.
