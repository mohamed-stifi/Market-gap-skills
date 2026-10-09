# D02 · Lexicon harvest and PRESS review

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Doctoral teams' independent vocabulary harvest before the literature search; facet-block search strategies (PICO-style concept blocks); PRESS peer review of electronic search strategies (McGowan et al. 2016) | P1 Lexicon | scout, reviewer | core |

**Use when:** right after the protocol is frozen and before any landscape search.

**Why:** A search finds only what its words describe, and a market is described by several vocabularies at once:
- the buyer's job titles
- the practitioner's jargon
- the vendors' category names
- the words people use when they complain or improvise

The doctoral teams the user described begin by having each researcher collect vocabulary alone and then compare lists. A term only one person found shows a blind spot.

The merged lexicon becomes deterministic query blocks, which are split between landscape scouts so their searches stay independent (D03). A reviewer then checks the strategy against the PRESS checklist. Errors at this stage, such as a missing synonym or a wrong filter, silently remove whole parts of the market from every later phase.

**Inputs**
- Scouts: your assignment (persona, seed terms, output path, tool-call limit) and the frozen `protocol.json`.
- Reviewer: the protocol, `lexicon/lexicon.json` and `lexicon/query-blocks.json`.

**Procedure**
1. **Scout:** read only your assignment and the files in its `read` list. Do not open other scouts' files in `lexicon/`; the value of the exercise is that the lists are independent.
2. **Scout:** search as your persona (`assets/personas.json`), starting from the seed terms.
   - Use your web-search tool, and log every search with `gapscan.py log-query RUN --source web --query "..." --count N --by <assignment_id>`.
   - Tier-1 sources go through `gapscan.py fetch RUN hn|se|gh-issues|... --query "..." --by <assignment_id>`, which logs automatically.
3. **Scout:** read what the searches return and record the terms people actually use, in six facets (examples are illustrative):
   - `segment`: job titles, company types and sizes ("freelance translator", "LSP", "boutique agency").
   - `job`: the job's verbs and objects ("send invoices", "chase late payments", "reconcile payouts").
   - `category`: what the market calls its products ("invoicing software", "accounts-receivable automation").
   - `tool`: incumbent product names, including spreadsheets and generic tools.
   - `pain`: complaint words ("late payments", "double entry", "currency fees").
   - `workaround`: improvised fixes ("invoice template", "Google Sheet", "Zapier", "virtual assistant").
   
   Use `other` for useful terms that fit nowhere else.
4. **Scout:** add a term only after you have seen it on a real page or post during this assignment, never from memory. The lexicon must describe the market, not your training data. Include spelling variants, abbreviations, plurals, and terms in every language listed in `protocol.languages`.
5. **Scout:** stop when new searches stop producing new terms, or at your tool-call limit (`budget.scout_tool_calls`, 20). Write `lexicon-output` JSON to your output path with `facets`, every search you ran in `queries`, `notes` and `tool_calls`.
6. **Orchestrator:** run `gapscan.py merge RUN --phase lexicon`. It normalises terms, computes overlap between the scouts (Jaccard per facet and overall), and writes `lexicon/lexicon.json`, recording how many scouts found each term.
7. **Orchestrator:** follow `next`. While overall overlap is below `lexicon.overlap_target` (0.8) and fewer than `lexicon.max_rounds` (2) rounds have run, another round runs, seeded with the union so far. Low overlap is information, not failure: it means the vocabulary is wider than any one scout saw.
8. **Orchestrator:** the merge builds `lexicon/query-blocks.json` deterministically. Each block combines terms across facets: segment × job, tool × pain, workaround × job, "alternative to" + tool, and so on. There are up to `lexicon.queries_per_scout` (24) blocks per scout.
9. **Reviewer** (spawned after `assign --phase press`): check the blocks against the protocol and fill the six PRESS items in `press.json`, each with `status` (`ok` or `issue`) and a `note`:
   - `translation`: do the blocks cover every PICOS element, including workarounds and doing nothing?
   - `operators`: is each block valid for the channels it will run on (quoted phrases, `site:` filters, tags)?
   - `synonyms`: are synonyms, abbreviations, regional spellings or protocol languages missing?
   - `spelling`: are there typos or misspelled product names?
   - `limits`: do the date, language and recency filters match `as_of`, `languages` and `recency_days`?
   - `other`: terms that flood results (product names that are common words), or terms outside the scope.
10. **Reviewer:** put missing terms in `add`, by facet, and harmful terms in `remove`. Set `verdict` to `revise` if either list is non-empty. Do not rewrite blocks by hand. The orchestrator then runs `gapscan.py lexicon apply-press RUN`, which rebuilds the blocks deterministically.

**Output**
- `lexicon/round-NN/scout-X.json` (schema `lexicon-output`)
- `lexicon/lexicon.json`
- `lexicon/query-blocks.json`
- `lexicon/press.json` (schema `press`)

**Metrics and checks**
- Overlap is Jaccard |A∩B| ÷ |A∪B| on normalised term keys (case, plurals, word order and stop-words ignored, so 'late payments' = 'payment, late'), per facet and overall; exact-string Jaccard is reported alongside. Target: `lexicon.overlap_target` (0.8), for at most `lexicon.max_rounds` (2) rounds. Low overlap with different personas is expected (a live run measured 0.06–0.12): it means the vocabulary space is wide, which is what the expansion round and the PRESS review address.
- All six required facets must be present in each scout output. An empty facet is allowed but should be explained in `notes`.
- Every search a scout ran appears in `queries.jsonl` and in that scout's `queries` list.

**Pitfalls**
- **Echoing the protocol's own words.** Those are already the seed terms; the value lies in words practitioners use that the protocol did not.
- **Vendor vocabulary only.** Complaint and workaround words come from forums, reviews and Q&A, not from product pages.
- **Forgetting non-English terms** when `protocol.languages` lists more than one language.
- **Reviewers editing `query-blocks.json` directly.** Changes go through `add`/`remove` so the blocks stay reproducible.

**Done when:** every lexicon round has been merged, `press.json` exists, and `lexicon apply-press` has run. `next` then moves on to the landscape phase.
