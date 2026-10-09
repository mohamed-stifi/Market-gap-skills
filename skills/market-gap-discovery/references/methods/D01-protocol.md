# D01 · Protocol and pre-registration

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Systematic-review protocols registered before searching (PRISMA-P); scoping-review framework (Arksey & O'Malley 2005); PICOS question framing (Robinson et al. 2011); founder fit (Graham, "How to Get Startup Ideas") | P0 Setup | orchestrator | core |

**Use when:** at the start of every run, after `init` and `doctor` and before any searching. Use it again whenever the human gives a directive that changes the plan.

**Why:** A doctoral review starts with a protocol so that nobody can move the goalposts once results come in. The risk is larger with agents. An agent can redefine the segment, loosen eligibility or drop a source after seeing what it found, and the result still looks systematic while actually being cherry-picked.

Writing the question, eligibility rules, sources and thresholds first, and freezing them by hash, ties every later number to a decision made before any data existed. PICOS forces the question to name a population, a job, the comparators (spreadsheets and doing nothing included) and the outcomes. Those are exactly what later phases search for, code and score.

**Inputs**
- The human's topic and constraints.
- The `protocol.json` draft written by `init`.
- `doctor.json`, `assets/defaults.json`, `references/glossary.md`.

**Procedure**
1. If the run folder does not exist yet, run `gapscan.py init RUN --topic "..." [--title "..."] [--autonomy autonomous|gated]`. Keep the `seed` it writes; it makes every assignment reproducible.
2. Run `gapscan.py doctor RUN`. From `doctor.json`, note which tier-1 sources are reachable and whether `MGD_CONTACT` and any tier-2 keys are set. Plan only with what is available.
3. Write `question` and all five `picos` fields:
   - `population`: a segment concrete enough to search, by role, company type and size. Illustrative: "freelance translators and translation agencies with 2–10 people".
   - `intervention`: the job or category, phrased without a product. Write "getting paid for finished jobs", not "an invoicing app".
   - `comparator`: incumbents, workarounds (spreadsheets, templates, freelancers) and doing nothing.
   - `outcomes`: the outcomes people want (time, cost, errors, compliance, cash flow).
   - `setting`: geography, languages, platforms, company size.
   
   Template for `question`: "Which jobs of [population] in [setting] are under-served by current [category] software and workarounds, and which of them could a small, agent-built SaaS serve profitably?"
4. Fill `scope.in` and `scope.out`. Then `business_models` (schema enum values only), `geography`, `languages` (ISO codes such as `en`, `fr`, `pt-BR`), and `as_of` (the run's reference date; evidence posted after it is ignored). Last, `recency_days`: how recent a product's last activity or a post must be to count.
5. Write `eligibility.include` and `eligibility.exclude` as testable rules that a screener can apply from a single page (D06). Every exclude rule should map to one of the `screening.reason_codes`.
6. Fill `founder_fit` with the human, honestly: `skills`, `budget_usd`, `hours_per_week`, `exclusions`, `schlep_tolerance` and `unfair_advantages`. Graham's test explains why it matters: the best gaps are ones the founder wants, can build, and few others realise are worth doing. These fields feed the right-to-win judgment (D21, D23).
7. Set `ambition.min_arr_usd`, the size anchor used in sizing and scoring (D24, D23).
8. Set `variation_dimensions`: the values that change-one-dimension variation may try (D19). These are `segment`, `language`, `platform`, `price_tier`, `delivery`, `integration` and `ai_native`. Add `competing_factors` only if the human already knows them; otherwise mapping proposes them (D07).
9. Set `sources.allowed_tiers`, starting from `[0, 1]`. In `sources.tier2_enabled`, list only families whose keys `doctor` found and whose terms allow your use; check the `tos` field in `assets/channels.json`. Put any extra domains to avoid in `sources.excluded_extra`. Then set `autonomy` and `budget`.
10. Override a default only when this run truly needs it. Put the override in `overrides` (for example `"landscape.coverage_target": 0.97`) and explain why in `notes`.
11. Run `gapscan.py protocol check RUN`. Fix every error it reports and re-run until it passes.
12. Call `gapscan.py next RUN`.
    - In gated runs it returns `BLOCKED HT-NNN`. Show the human `gapscan.py protocol show RUN` and wait for `gapscan.py hq done RUN HT-NNN`.
    - In autonomous runs it returns the freeze step.
13. Run `gapscan.py protocol freeze RUN`. From then on, never edit `protocol.json` directly.
14. Record every later change with `gapscan.py protocol amend RUN --reason "..." --set KEY=JSON`. That includes human directives such as "focus on agencies", recorded as a `directive` human task. The reason becomes part of the audit trail and appears in the dossier's limitations.

**Output:** `protocol.json` (schema `protocol`) and `protocol.lock.json` (sha256 hash, freeze time, amendments).

**Metrics and checks**
- `protocol check` validates the schema. All five PICOS fields, at least one `eligibility.include` rule, valid language codes and `recency_days` ≥ 30 are required.
- After the freeze, any direct edit stops matching `protocol.lock.json`, so `validate` can detect it. Amendments are the only legitimate path.
- The handoff carries `protocol_sha256` (D25). Later skills can tell exactly which protocol produced an opportunity.

**Pitfalls**
- **Solution-shaped questions** ("demand for an AI invoicing tool"). They push every phase toward confirming the solution. Ask about jobs instead.
- **Vague populations** ("small businesses"). They make screening and coding unreliable; name roles and company types.
- **Missing `as_of` or `recency_days`.** Without them, evidence from different weeks of the run is not comparable.
- **Enabling tier-2 sources whose terms forbid commercial use** (see Product Hunt and Reddit in `assets/channels.json`).
- **Silent edits after the freeze.** Use `protocol amend`, even for small fixes.

**Done when:** `protocol check` passes, the protocol is frozen (and approved, in gated runs), and `next` moves on to the lexicon phase.
