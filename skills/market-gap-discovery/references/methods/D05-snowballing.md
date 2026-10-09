# D05 · Snowballing

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Snowballing guidelines for systematic literature studies (Wohlin 2014): iterate backward (reference lists) and forward (citing papers) from a diverse start set until an iteration adds nothing | P2 Landscape | scout | core |

**Use when:** after the sampling loop ends with SATURATED or STOP_UNSATURATED. Run up to `snowball.max_iterations` (3) iterations.

**Why:** Keyword searches miss products described with words the lexicon never saw. Software products reference each other much as papers cite each other. Vendors publish "alternatives" and "vs" pages, integration directories list their partners, and comparison posts and "alternative to X" threads link competitors. Following those links backward (from an entity's own pages) and forward (to whoever mentions the entity) reaches products that keyword searches cannot.

Each step starts from what is already known, so snowball finds are not independent samples. They join the landscape but stay out of the estimator's incidence (D04). A high snowball yield is itself a finding: it means the sampling missed part of the market.

**Inputs**
- Your assignment:
  - the seed entities (ids, names, URLs), which form the start set for this iteration
  - the unit to report under (`unit_id`, family `snowball`)
  - output path and limits
- `assets/channels.json` for exclusions.

**Procedure**
1. Work through every seed in your assignment, not just the famous ones. Wohlin stresses a diverse start set (different categories, sizes, platforms), and the assignment draws seeds that way. Skipping obscure seeds throws away the diversity.
2. **Backward pass.** For each seed, read the entity's own pages that name other products: "alternatives", "compare", "vs", "migrate from", the integrations or partner directory, and docs that mention competitors.
   - Snapshot each page with `gapscan.py snapshot RUN URL --by <assignment_id>`, then read the `.txt` file it saves, so the trail can be reproduced.
   - Record every product, community or directory those pages name, with `direction` = `backward` and `via_entity` = the seed's entity id.
3. **Forward pass.** For each seed, find who mentions or lists it:
   - Web searches such as `alternative to <name>`, `<name> vs`, `<name> competitors`, each logged with `gapscan.py log-query RUN --source web --query "..." --unit <unit_id> --by <assignment_id>`.
   - `gapscan.py fetch RUN hn --query "<name>" --unit <unit_id> --by <assignment_id>`, for launch threads and comparisons.
   - `gapscan.py fetch RUN gh-repos --query "<name> alternative" --unit <unit_id> --by <assignment_id>`, for open-source alternatives.
   - Directory listing pages that show the seed next to others (listings only, never reviews).
   
   Record what you find with `direction` = `forward` and `via_entity` = the seed.
4. Unlike D03, searching by product name is the whole point of this phase. Log every search exactly as you ran it.
5. Apply the exclusions from D03: skip excluded domains and paths, and stop a query when a script exits with code 2.
6. Record items as in D03 (`name`, `url`, `kind`, `listing_url`, `evidence_url`, `query_index`, `note`) and add `via_entity` and `direction`.
   - Record every entity you meet, including ones you suspect are already known.
   - You must not consult `landscape/entities.jsonl` to check. The merge de-duplicates by canonical key.
7. Write one `landscape-output` JSON with `mode` = `snowball`, your `units`, `stop_reason` and `tool_calls`, to the output path in your assignment.
8. **Orchestrator:** run `gapscan.py merge RUN --phase snowball`. New entities then go through screening (D06) and `gapscan.py entities verify RUN` like any others. `next` starts another iteration until one adds no new verified entity or the limit is reached.

**Output:** `landscape/snowball/iter-NN/scout-X.json` (schema `landscape-output`, `mode` = `snowball`).

**Metrics and checks**
- Snowball finds are tagged at merge, and they never enter `landscape/incidence.json`, so they cannot inflate the Chao2 overlap.
- Yield per iteration is new verified entities ÷ entities known before the iteration. It should fall from one iteration to the next; in Wohlin's worked example it reached zero by the fourth.
- If snowballing adds more than `snowball.high_yield_flag` (0.1) of the landscape as new verified entities, the run records a coverage limitation. That lowers certainty (D22) and is stated in the dossier.

**Pitfalls**
- **Treating a vendor's "alternatives" page as neutral.** It lists who the vendor wants to be compared with. That is fine for discovery, but not as evidence about quality.
- **Following links into excluded review sites** (G2, Capterra and the others listed in `assets/channels.json`).
- **Starting from leaders only.** The start set's diversity is what lets snowballing reach unfamiliar corners.
- **Reporting only entities you think are new.** You cannot know which are new without breaking isolation, so report all of them.

**Done when:** every seed has had a backward and a forward pass, your output validates, and every search is logged.
