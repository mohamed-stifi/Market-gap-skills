# gapscan.py command reference

Contents
1. Conventions
2. The `next` loop and its verdicts
3. Pipeline steps (what `next` checks, in order)
4. Commands
5. Run folder layout

## 1. Conventions
- **How to run:** `python3 SKILL_DIR/scripts/gapscan.py <command> ...`. SKILL_DIR is the folder holding this skill's SKILL.md. `RUN` is the run folder, for example `gap-runs/invoicing-translators`, and its folder name is the run id.
- **Dependencies:** scripts use only the Python 3.8+ standard library.
- **Output:** every command prints a short summary. `next`, `status` and `compare` can also print JSON (`--json`, or `compare --out FILE`).
- **Who writes what:** scripts write the ledgers and analyses. Agents write only the output paths named in their assignment. Never hand-edit a script-made artifact: fix its inputs and re-run the script.
- **Exit codes:**
  - 0: ok
  - 1: usage or validation error (the message says what to fix)
  - 2: blocked (network, robots.txt, excluded source, missing key, human approval needed)
  - 3: budget exhausted

## 2. The `next` loop and its verdicts
`gapscan.py next RUN` inspects the run folder and prints one action on the first line:

| First token | Meaning | What the orchestrator does |
|---|---|---|
| `RUN gapscan.py <args>` | A deterministic step is due | Run it (the `NOTE cmd:` line gives the full path), then call `next` again |
| `SPAWN <role> <n> <assignment paths ...>` | Independent agent work is due | Start n subagents in parallel, one per assignment file; each reads its assignment, then only the files in its `read` list. When all have finished, call `next` |
| `DO <card-id> <task>` | A judgment task for the orchestrator | Follow that method card, then call `next` |
| `BLOCKED <HT-id>` | Waiting for the human operator | Show the task (`hq list`) and stop until the human records `hq done` or `hq decline` |
| `DONE` | The run is complete | Report the deliverables named in the NOTE lines |

The lines after the first start with `NOTE`: the phase, the methodological reason (for example `landscape EXPAND k=6`, `landscape PROBE`, `ADVANCE P3`), and the full command.

## 3. Pipeline steps
`next` returns the first unmet step.
- **P0 Setup:**
  1. `doctor`.
  2. Fill `protocol.json` (`DO D01`; `protocol check` lists what is missing).
  3. Gated runs: the human approves.
  4. `protocol freeze`.
  
  If `protocol.json` changes after freezing, `next` stops until it is restored or amended.
- **P1 Lexicon:**
  1. `assign --phase lexicon` → SPAWN scouts → `merge --phase lexicon`.
  2. A second round runs while overlap is below `lexicon.overlap_target` and rounds remain.
  3. `assign --phase press` → SPAWN reviewer → `lexicon apply-press`.
- **P2 Landscape:**
  1. `assign --phase landscape` → SPAWN scouts → `merge --phase landscape`.
  2. While unscreened entities exist: `assign --phase screen` (screener A gets all, B an audit sample) → SPAWN → `merge --phase screen`.
  3. `entities verify`, repeated until none are pending.
  4. `saturation`. EXPAND starts a new round of k units. NEEDS_PROBE runs `assign --phase probe` → SPAWN → `merge --phase probe` → screen → verify → `saturation`. SATURATED or STOP_UNSATURATED closes sampling.
  5. Snowball iterations (`assign --phase snowball` → SPAWN → `merge --phase snowball` → screen → verify) until an iteration adds no included entity.
  6. `screen-audit`. If α is too low, `DO D06` (clarify eligibility with `protocol amend`).
  7. Gated runs: the human approves.
  8. `assign --phase mapping` → SPAWN → `merge --phase mapping`.
- **P3 Evidence:**
  1. `assign --phase evidence` → SPAWN miners → `merge --phase evidence`.
  2. `verify`.
  3. `bursts`, whenever signal series are newer than the last run.
- **P4 Coding and synthesis:**
  1. `assign --phase coding-open` → SPAWN coder → `codebook freeze`.
  2. `assign --phase coding-closed` → SPAWN coders → `merge --phase coding`.
  3. `assign --phase coding-reliability` → SPAWN coder B → `merge --phase coding` → `agreement`.
     - If the verdict is insufficient, repeat `assign --phase coding-reliability`: a top-up of only the records still needed.
     - If the verdict is revise, `assign --phase coding-open --revise`, then refreeze and recode.
  4. `themes`. If themes are unsaturated and evidence rounds remain, return to P3.
  5. `assign --phase supply` → SPAWN → `merge --phase supply` → `matrix` → `gapmap`.
  6. After a codebook revision, `assign --phase supply` again in update mode (only changed codes are re-judged).
- **P5 Gaps:** `variants` → `assign --phase synthesis` → SPAWN → `cards check`. If it lists problems: `DO D20`.
  - If fewer than `evidence.target_candidates` cards pass and near-miss cards fail only on evidence counts: `assign --phase evidence --targeted` (once per run), then the new records are coded, the gap map is recomputed and the cards are updated (`assign --phase synthesis` in update mode) before the red team.
- **P6 Appraisal:**
  1. `assign --phase redteam` → SPAWN → `merge --phase redteam` → `certainty`.
  2. `assign --phase sizing` → SPAWN → `size` → `score`.
  3. Gated runs: the human approves.
- **P7 Report:**
  1. `prisma` → `assign --phase writer` → SPAWN → `validate --report`.
  2. If it fails, run up to two writer fix passes, then `DO D25`.
  3. `viz` (when matplotlib is installed): `output/summary.md` and `output/dashboard/`.
  4. `DONE`.

## 4. Commands
**Setup and control**
- `init RUN --topic TEXT [--title TEXT] [--seed INT] [--autonomy autonomous|gated]`: create the run folder, a protocol draft, the author-hash salt and the state file.
- `doctor RUN [--offline]`: check Python, `MGD_CONTACT`, the `gh` login, reachability of tier-1 sources and tier-2 keys.
  - Writes `doctor.json`.
  - Unreachable sources are added to `coverage-gaps.jsonl`.
  - Optional human tasks (contact string, `gh` login) are added to the queue.
- `protocol check|show|freeze RUN`: validate, print or hash-freeze `protocol.json`.
- `protocol amend RUN --reason TEXT [--set KEY=JSON ...]`: a logged change to the frozen protocol. KEY is a dotted path, for example `--set 'geography=["EU"]'` or `--set overrides.landscape.coverage_target=0.97`. `--set 'independence="degraded"'` also marks the run state.
- `next RUN [--json]`: the next action. A SPAWN is followed by `NOTE model: <tier> …` (the model each of its subagents should use).
- `status RUN [--json]`: run summary, including `spend_by_phase`, `spend_by_tier` and `model_escalations`.
- `protocol check` also prints non-blocking warnings: a broad intervention (>= `scope.broad_jobs_warning` jobs) and an unset `cost_profile`.
- `hq list RUN`
- `hq add RUN --type TYPE --title TEXT --why TEXT --steps TEXT --returns TEXT [--phase P] [--blocking] [--fallback TEXT]`
- `hq done|decline RUN HT-NNN [--note TEXT]`
- Human-task TYPE is one of account, key, payment, legal, outward-action, judgment, directive.

**Assignments and merges**
- `assign RUN --phase PHASE [--units K] [--batch N] [--revise] [--targeted]`: seeded assignment files.
  - PHASE: lexicon, press, landscape, probe, snowball, screen, mapping, evidence, coding-open, coding-closed, coding-reliability, supply, synthesis, redteam, sizing, writer.
  - `--targeted` (evidence): one miner per near-miss gap card from `gaps/card-check.json`, mining only domains the card lacks.
  - Every assignment carries a `model` block: the tier from `models.profiles[cost_profile][role]`, raised one step per escalation (`state.json` → `models`).
  - Fails with exit 3 when `budget.subagents_max` would be exceeded.
- `merge RUN --phase PHASE`: validate agent outputs against their schemas, then fold them into the ledgers. `--retry` (evidence only) merges the current round again after rejected records were fixed; the retry report is `merge-retry-N.json`, and PRISMA counts its accepted records as `accepted_on_retry`. A unique snapshot-id prefix of 12 or more hex characters resolves to the full hash.
  - PHASE: lexicon, landscape, probe, snowball, screen, mapping, evidence, coding, supply, redteam.
  - Evidence records are rejected (and listed) when they have: a raw author field, a username in the quote, an excluded source, a snapshot not made by gapscan, a quote over 280 characters, or a schema error.
- `lexicon apply-press RUN`, `entities verify RUN [--limit N]`, `codebook freeze RUN`.
- `entities verify RUN --recheck` re-runs only the name check against the snapshots it already has, with no new fetch. Use it after the matching rules change.

**Collection**
- `fetch RUN SOURCE [options] [--unit UNIT] [--by AGENT] [--show N]`: tier-1 adapters.
  - The raw response is saved as a snapshot.
  - The query is logged in `queries.jsonl`, with the total hit count you need for `stoptest`.
  - Normalised items go to `raw/SOURCE/<sha16>.jsonl`. Each item has `n, source, id, url, title, text` (an excerpt of the snapshot text), `author_hash, posted_at, metrics, snapshot, kind_hint, entity_url, listing_url`.
  
  SOURCE and its options:
  - `hn --query Q [--tags story|comment|show_hn|ask_hn|(story,comment)] [--since YYYY-MM-DD] [--limit N]`
  - `hn-counts --query Q --from YYYY-MM --to YYYY-MM [--tags T]`: writes `evidence/signals/SIG-hn-*.json` (monthly r of d).
  - `hn-hiring --query Q [--months N]`
  - `se --query Q [--site stackoverflow] [--limit N]`
  - `se-counts --query Q --from YYYY-MM --to YYYY-MM [--site S]`
  - `gh-issues --query Q [--limit N]`, `gh-repos --query Q [--limit N]` (need `gh auth login`)
  - `wiki-views --article TITLE --from YYYY-MM --to YYYY-MM [--project en.wikipedia]` (needs `MGD_CONTACT`; absolute series)
  - `wp-search --query Q`, `wp-plugin --slug S`, `wp-reviews --slug S`
  - `apple-search --query Q [--country us]`, `apple-reviews --id APPID [--country us] [--pages N]`
  - `atl-search --query Q`, `atl-reviews --key ADDON_KEY`
  - `yc --query Q`
- `snapshot RUN URL [URL ...] [--by AGENT] [--refresh]`: robots-checked, rate-limited raw fetch.
  - Prints `<sha256> <status> <url>`.
  - A snapshot of the same URL from the last 24 h is reused unless `--refresh` is given.
  - Excluded sources, robots disallows, 401/403/429 and network errors are refused and logged as coverage gaps (exit 2 when every URL is refused).
- `hash-author RUN PLATFORM HANDLE`: prints `ah_` plus 16 hex characters, or `unknown` for an empty handle.
- `log-query RUN --source S --query Q [--count N] [--filters F] [--unit UNIT] [--by AGENT]`: log a search made with your own web-search tool.
- `stoptest --unseen N --sample-n n --sample-k k --found R [--recall 0.95] [--confidence 0.95] [--run RUN --source S --query Q --by AGENT]`: Callaghan & Mueller-Hansen stopping test. Prints STOP or CONTINUE with the p-value, and logs the decision when `--run` is given.

**Analysis**
- `saturation RUN`: Chao2 with its 95% CI, coverage Ĉ, completeness, marginal yield, the probe's new share, the extra units needed, and the verdict EXPAND, NEEDS_PROBE, SATURATED or STOP_UNSATURATED.
- `verify RUN`: check every evidence quote against its snapshot. Only verified records count.
- `screen-audit RUN`, `agreement RUN`, `themes RUN`, `bursts RUN`, `matrix RUN`, `gapmap RUN`, `variants RUN`, `cards check RUN`, `certainty RUN`, `size RUN`, `score RUN`, `prisma RUN`: see the matching method cards.
- `validate RUN [--report] [--file PATH [--schema NAME]]`: check every artifact against its schema. `--report` also checks the dossier and handoff against the ledger and ranking, and writes `output/report-check.json`. `--file` checks only one file (the schema is inferred from its path); subagents use it to self-check their own output.
- `viz RUN [--out DIR]`: `output/summary.md` (one-page plain-language verdict) and `output/dashboard/` (PNG charts, `index.html` embedding all of them, `manifest.json`). Needs matplotlib; every other command is stdlib-only. Reads only the run's files; charts whose inputs are missing are skipped with a reason.
- `compare RUN_A RUN_B [--out FILE]`: entity Jaccard, the Webster–Kemp estimate of missed items, top-k gap matches, rank-biased overlap, and pass/fail.
- `purge RUN [--days N]`: delete snapshot bodies older than `evidence.retention_days`. Hashes, metadata and the ledger quotes are kept.

## 5. Run folder layout
```
RUN/
  state.json  events.jsonl  protocol.json  protocol.lock.json  doctor.json  .salt
  human-tasks.json  human-tasks.md  queries.jsonl  coverage-gaps.jsonl
  cache/{robots/, rate/, snapshot-index.jsonl, fetch-count.jsonl, public_suffix_list.dat, yc-all.sha}
  lexicon/round-NN/{assign-X.json, scout-X.json, overlap.json}  lexicon.json  query-blocks.json  press-assign.json  press.json
  landscape/round-NN/{assign-X.json, scout-X.json, merge.json}
  landscape/probe/NN/{assign-P.json, scout-P.json, merge.json}
  landscape/snowball/iter-NN/{assign-X.json, scout-X.json, merge.json}
  landscape/screen/batch-NN/{assign-A1.json, assign-A2.json, ..., assign-B1.json, screen-A1.jsonl, ..., screen-B1.jsonl}  (batches of screening.batch_size)
  landscape/{entities.jsonl, units.json, saturation.json, screening.jsonl, screening-audit.json,
             mapping-assign.json, classification.json, entity-attributes.jsonl}
  snapshots/<sha256>.raw|.txt|.meta.json        raw/<source>/<sha16>.jsonl
  evidence/round-NN/{assign-X.json, miner-X.jsonl, why-now-C.jsonl, merge.json}
  evidence/{ledger.jsonl, verify-report.json, why-now.jsonl, signals/SIG-*.json, bursts.json}
  coding/{open-assign-vN.json, codebook-draft-vN.json, codebook.vN.json, codebook.lock.json,
          closed-assign-vN-bNN.json, codes-A-vN-bNN.jsonl, codes-A.jsonl,
          reliability-assign-vN.json, codes-B-vN.jsonl, codes-B.jsonl, agreement.json, themes.json}
  analysis/{supply-assign.json, supply.jsonl, matrix.json, competitor_matrix.csv, price_ladder.csv,
            strategy_canvas.csv, pain_by_entity.csv, gapmap.json, association.csv}
  gaps/{variants.jsonl, synth-assign.json, cards.jsonl, card-check.json, redteam/assign-NN.json,
        redteam/GAP-NNN.json, judgments.jsonl, certainty.json, sizing-assign.json, sizing-inputs.json,
        sizing.json, scores.csv, ranking.json}
  output/{writer-assign-NN.json, dossier.md, handoff.json, watchlist.json, prisma.json, prisma.md, report-check.json, summary.md}
  output/dashboard/{NN-*.png, index.html, manifest.json}
  scratch/<assignment_id>/   (subagents' helper scripts; never read by other agents)
```
