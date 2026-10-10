# D06 · Screening and eligibility

| Origin | Phase | Roles | Status |
|---|---|---|---|
| PRISMA 2020 study selection with recorded exclusion reasons; dual independent screening with an agreement audit (Krippendorff's alpha; O'Connor & Joffe 2020 on double-coding 10–25%) | P2 Landscape | screener | core |

**Use when:** after every landscape, probe or snowball merge that added entities.

**Why:** Scouts collect broadly, and screening decides what belongs to the market the protocol defined. Systematic reviews screen against written eligibility rules and record a reason for every exclusion. That makes the selection inspectable, and the flow diagram shows how many items were removed and why.

A second screener re-screens a random sample independently. Their agreement (Krippendorff's alpha) shows whether the rules are applied consistently or depend on one agent's reading. Without it, "the market" is whatever one screener happened to accept.

**Inputs**
- Your screen assignment: the entity ids, names and URLs to screen, and whether you are screener A or B.
- The frozen `protocol.json`: `scope`, `eligibility`, `business_models`, `geography`, `languages`, `recency_days`, `as_of`.
- `screening.reason_codes` in `assets/defaults.json`.

**Procedure**
1. Read your assignment and the protocol's eligibility rules.
   - Screener B never opens any `screen-A*.jsonl`, `landscape/screening.jsonl` or any other screening decisions. B's value is independence.
2. For each entity, read its page through `gapscan.py snapshot RUN URL --by <assignment_id>` and the `.txt` file it saves, so the decision can be reproduced. If a page shows nothing without JavaScript, you may read it with your own web tool, but say so in `note`. App stores answer 404 for apps not offered in the fetching machine's country, so before deciding EX-NOT-FOUND on a store page, snapshot it once more with a storefront from the protocol's `geography` (Google Play `&gl=US`, App Store `/us/`).
3. Apply the rules in this order and stop at the first that fails:
   1. Does the page exist and name the entity? If not: `EX-NOT-FOUND`.
   2. Is it reachable only through an excluded source? `EX-EXCLUDED-SOURCE`.
   3. Is it a software product, a community or a directory? If not: `EX-NOT-SOFTWARE`.
   4. Was it active within `recency_days` before `as_of`? Look for a recent changelog, posts, an app update, a live domain. If not: `EX-DEAD`.
   5. Is it the same product as another entity under a different key (a rebrand, or a marketplace listing of a product already listed by domain)? `EX-DUPLICATE`, with `duplicate_of` set to the other entity id.
   6. Is it inside `scope.in` and clear of every `eligibility.exclude` rule? If not: `EX-OUT-OF-SCOPE`.
   7. Does it meet every `eligibility.include` rule? Then `include`, with reason `IN`.
4. Use `unsure` with reason `UNSURE` only when the page truly cannot answer a rule, and write in `note` what is missing. An unsure entity does not count as included.
5. Screen communities and directories too. Include them when the protocol's population gathers there or when they list in-scope products. They later serve as reach channels (D21) and snowball seeds (D05).
6. Write one `screening` JSON line per entity to your output path, with `entity_id`, `decision`, `reason_code`, `duplicate_of` (or null), a short `note` and `screener` (`A` or `B`).
7. **Orchestrator:** run `gapscan.py merge RUN --phase screen`. It applies screener A's decisions to `landscape/entities.jsonl` and keeps B's decisions for the audit.
8. **Orchestrator:** run `gapscan.py entities verify RUN`. It checks that each included entity's page answers HTTP 200 and names the entity. Only entities that are screened in **and** verified count anywhere: in saturation, mapping and evidence.
9. **Orchestrator:** after every screening merge, `next` runs `gapscan.py screen-audit RUN` on all double-screened entities so far. If alpha is low, read the disagreements, then clarify the rule that caused them with `gapscan.py protocol amend RUN --reason "..." --set eligibility.include=[...]`, and record the low audit as a limitation. A live run had one recurring disagreement (payment processors versus billing tools for software sellers); an amendment after the second batch resolved it.
10. Once the cumulative audit is `accept` over at least `screening.audit_until_units` (50) entities, later batches skip screener B: the rule has been shown to be applied reliably, and each skipped audit saves a subagent (a live run reached alpha 0.90 over 162 audited entities across 7 audits). A later `revise` verdict reopens auditing. The dossier states the batches that were audited.

**Output**
- `screen-A1.jsonl`, `screen-A2.jsonl`, … and `screen-B1.jsonl`, … in `landscape/screen/batch-NN/` (schema `screening`).
- The merged decisions in `landscape/screening.jsonl`.
- `landscape/screening-audit.json`.

**Metrics and checks**
- Audit sample: `screening.audit_fraction` (0.2) of the screened entities, with a minimum of `screening.audit_min_units` (10), until the audit is accepted over `screening.audit_until_units` (50). Batches hold `screening.batch_size` (60) entities.
- Krippendorff's alpha on the include/exclude decisions of A and B:
  - ≥ `screening.alpha_accept` (0.8): accept.
  - From `screening.alpha_provisional` (0.667) up to 0.8: provisional, reported as a limitation.
  - Below 0.667: the rules are not being applied consistently, so fix the rules, not the decisions.
- PRISMA exclusion counts per reason code come from `gapscan.py prisma RUN`.

**Pitfalls**
- **Screening on impressions** ("looks small", "seems old") instead of the written rules.
- **Excluding products because they are unfamiliar.** Unknown niche products are exactly what the landscape needs.
- **Using `EX-OUT-OF-SCOPE` as a catch-all.** The specific code matters for the flow diagram and the audit.
- **Resolving A–B disagreements by editing files.** Disagreements are the audit's data.

**Done when:** every entity in your assignment has exactly one decision line, and your file validates against `screening`.
