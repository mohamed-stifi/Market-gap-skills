# D28 · Scan depth and the opportunity funnel

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Stage-gate new-product screening (Cooper 1990: staged work with go/kill gates); successive halving for best-arm identification (Karnin, Koren & Somekh 2013; Jamieson & Talwalkar 2016; Hyperband, Li et al. 2018): evaluate many candidates cheaply, keep the better half, give survivors more budget; scoping before a systematic review | P2-P7 (scan runs) | orchestrator, miner, red-team | conditional (protocol `depth: scan`) |

**Use when:** the protocol sets `depth: scan`. `gapscan.py init` writes it for new runs; use it for a broad topic or when you do not yet know which question to ask.

**Why:** The first full live run spent 91 subagents (about $250 and 4 hours) on a topic spanning seven jobs: the landscape never saturated and 11 of 12 gap cards lacked evidence. Breadth and depth need different budgets. A scan maps the market once, generates options from every lens (D26) by script, and spends evidence only on the best options, halving the field each round. Its output is a ranked list of options and protocol drafts for narrow deep runs, so the expensive method runs on one sharp question instead of a whole field. A simulated scan uses about 14 subagents, 12 of them on the fast tier.

**Inputs:** `protocol.json` with `depth: scan` (and optionally `lenses`); the scan profile in `assets/defaults.json` → `depth.profiles.scan`, which the protocol's own overrides still beat.

**Procedure**
1. **Map once (P1-P2).** One lexicon round without PRESS review, one landscape round (the saturation verdict is reported as a lower bound, usually STOP_UNSATURATED), no snowballing, a single screener per batch, then mapping (D07) and traction (D27).
2. **Generate (P5, script).** `gapscan.py opportunities scan RUN` writes options from every lens.
3. **Test round 1 (P3).** `gapscan.py assign RUN --phase scan-evidence` picks the `scan.evidence_candidates` options with the best structural signal, at most `scan.max_per_lens` per lens first so several kinds of opportunity get tested. One fast-tier miner per `scan.candidates_per_miner` options mines about `scan.records_per_candidate` records each, tagging every record with `candidate_ids`. A **leads miner** looks for evidence-led options the map cannot show: people paying a person for a job, leaving a product after a shutdown or price rise, using one part of a suite, gluing two tools, or asking for a product on another platform; it logs catalysts in the why-now file (D12).
4. **Merge, verify, re-scan, score.** Quotes are verified as always (D09). The scan runs again so evidence-led lenses (productize, replace, unbundle) can fire. `gapscan.py opportunities score RUN` sorts each option into a tier:
   - **promising:** at least `scan.min_records` supporting records, `scan.min_domains` domains and `scan.min_authors` authors;
   - **contradicted:** praise and contra records outnumber support (2 or more);
   - **thin:** some support; **untested:** none.
   The evidence score is the strength-weighted count of distinct authors (D10 weights), 1.0 at `scan.evidence_full`.
5. **Test round 2 (successive halving).** The better half (`scan.keep_fraction`) of all options with support, including evidence-led ones the leads miner surfaced, gets a second round from domains it does not have yet.
6. **Red flags (P6).** One standard-tier red-team subagent checks the top `scan.redflag_top` options: at least 2 logged searches each for a product that already does exactly this, the founder gates (D23) and a possible growth loop. `killed` needs the snapshot of a product that fully covers the option, or license text that forbids it. `gapscan.py merge RUN --phase redflag` enforces this.
7. **Rank and report (P6-P7, scripts).** `gapscan.py opportunities rank RUN` orders by tier, then red-flag status, then `scan.rank_weights` (prior and evidence). Gates and kills move options to `excluded` with reasons. `gapscan.py opportunities report RUN` writes `output/opportunities.md`, `output/opportunities.json` and `output/next-runs/OPP-NNN.protocol.json` drafts for the best `scan.next_runs` options. No writer subagent.
8. **Hand over.** The human picks an option. `gapscan.py init gap-runs/NEW --from-run SCAN_RUN --opportunity OPP-NNN` starts a deep run with the drafted protocol (depth deep, the option's lens first, its products as `seed_entities`). The human reviews the question, PICOS and eligibility before freezing.

**Output:** `opportunities/{candidates.jsonl, scores.json, redflags.jsonl, ranking.json}`, `output/{opportunities.md, opportunities.json, next-runs/, prisma.md}`, and the dashboard (charts 13-16, D25).

**Metrics and checks:** PRISMA (D25) adds an Opportunities section: options generated, tested, promising, contradicted, red-flag checked, excluded, ranked. `gapscan.py status RUN` shows subagents per phase and model tier.

**Pitfalls**
- **Reading a scan as a finding.** A scan ranks leads. Only a deep run gives certainty ratings, and only validation shows that people will pay.
- **Skipping round 2.** One round rewards whichever options happened to get easy sources; the second, independent round on new domains is the check.
- **Gaming the tags.** A record supports an option only if its quote bears on that option's question; miners tag counter-evidence too.

**Done when:** `next` prints DONE with `output/opportunities.md` and at least one next-run draft, or a note that no option reached the thin tier.
