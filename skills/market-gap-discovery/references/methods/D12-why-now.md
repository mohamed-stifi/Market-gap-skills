# D12 · Why-now scan (PESTLE)

| Origin | Phase | Roles | Status |
|---|---|---|---|
| PESTLE environmental scan (political, economic, social, technological, legal, environmental) plus a platform factor for SaaS; Sequoia's question "why hasn't this been built before now?"; new tools and techniques as gap sources in research labs; accelerator requests (YC RFS) and investor theses as weak signals | P3 Evidence | miner | core |

**Use when:** in evidence round 1. Refresh in later rounds only if the orchestrator asks.

**Why:** A gap that has stayed open for ten years usually has a reason: tiny demand, bad economics, a regulator, or a platform owner. A gap that opened because something changed is different. Incumbents were built for the old world, and the new constraint or capability favours newcomers.

Research labs see the same thing when a new instrument or method suddenly makes an old question answerable. Recording catalysts systematically turns "the timing feels right" into evidence that the red team (D21) and the scoring (D23) can check. Each catalyst gets a date, a primary source, and the job it unlocks.

**Inputs**
- Your assignment.
- The protocol: `picos`, `geography`, `as_of`, `recency_days`.
- The lexicon terms.
- `evidence/bursts.json`, if it already exists.

**Procedure**
1. For each factor, search for changes inside the protocol's geography and recency window that touch the protocol's jobs. The examples are illustrative; search your own setting.
   - **political:** public procurement rules, government digital programmes.
   - **economic:** incumbent price rises or plan cuts, currency or interest shifts that change budgets.
   - **social:** changes in how the population works (remote teams, freelancing, new roles).
   - **technological:** new capabilities, or sharp cost drops in models, APIs or open-source components, that make a job automatable.
   - **legal:** mandates, deadlines and standards (e-invoicing, data protection, accessibility, reporting).
   - **environmental:** reporting or compliance duties.
   - **platform:** app-store or marketplace policy changes, new or deprecated APIs, fee changes, new extension points.
2. Prefer primary sources: the law or the regulator's page, the platform's own changelog or announcement, the vendor's pricing-change notice. Log each search with `gapscan.py log-query RUN --source web --query "..." --by <assignment_id>`. Snapshot each page you rely on with `gapscan.py snapshot RUN URL --by <assignment_id>`.
3. Write one `why-now` line per catalyst to the why-now path in your assignment (`evidence/round-NN/why-now-C.jsonl`); the merge adds them to `evidence/why-now.jsonl`:
   - no `id`: the merge assigns `WN-NNN` ids so parallel miners never collide.
   - `factor`, and `change` (what changed, in one or two sentences).
   - `date`: when the change happened or takes effect, as YYYY, YYYY-MM or YYYY-MM-DD.
   - `url`, `snapshot`, and optionally a verbatim `quote` of at most 280 characters.
   - `job_unlocked`: the specific job that becomes newly painful or newly solvable. Illustrative: "issue compliant e-invoices from a freelancer's existing tool".
   - `strength`:
     - `strong`: a primary source, dated, directly about the job.
     - `moderate`: a credible secondary source with a date.
     - `weak`: an opinion, forecast, investor thesis or accelerator request.
   - `related_terms`: lexicon terms whose signal series could corroborate the catalyst (D11).
4. Record YC Requests for Startups and investor theses as `weak` at most. They show what investors believe, not what customers do.
5. Ask Sequoia's question of every catalyst: why could this not have been built before now? If the honest answer is "it could have", the catalyst is weak, whatever its source.
6. Make sure every factor has been searched, including the ones where you expect nothing. The query log is the proof that a factor was considered and came up empty.

**Output:** your assignment's `why-now-C.jsonl` (schema `why-now`), merged into `evidence/why-now.jsonl` with WN ids.

**Metrics and checks**
- Gap cards cite catalysts by id in their `why_now` field (D20). The why-now criterion in scoring counts them and weighs their strength (D23).
- A catalyst without a snapshot or a date does not count.
- A significant burst (D11) in one of the `related_terms` corroborates a catalyst. The absence of a burst does not refute it.

**Pitfalls**
- **Hype as a catalyst** ("AI changes everything"). Name the specific capability, its date and the job it unlocks.
- **Drafts and proposals presented as rules.** If something has no effective date or may never pass, record it as `weak` and say so in `change`.
- **News from outside the protocol's geography.**
- **Mistaking the catalyst for the gap.** The gap still needs pain, demand and supply evidence (D20).

**Done when:** all seven factors have logged searches, and every catalyst found has a valid line with a snapshot and a date.
