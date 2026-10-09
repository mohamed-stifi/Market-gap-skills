# Market-gap skills

Two Agent Skills that let coding agents (Claude Code, OpenCode, Codex CLI) find and validate **SaaS market gaps** with a systematic, auditable method instead of guesswork:

| Skill | Turns | Into |
|---|---|---|
| `market-gap-discovery` | a topic | a ranked dossier of evidence-backed gaps + `handoff.json` |
| `market-gap-validation` | one opportunity (or a one-line idea) | pre-registered experiments run with a human operator + a GO / ITERATE / PIVOT / KILL verdict + `validated-handoff.json` |

The method comes from how doctoral teams find research gaps. Researchers search independently, compare how much their results overlap, continue only when the overlap is high, code evidence in pairs, and report what they could not cover. Here, agents do the reading and labelling, and deterministic Python scripts do all the counting, merging, verifying, scoring and deciding.

## How the research method maps to the skills
| Doctoral practice | In the skills |
|---|---|
| Register a protocol before searching | `protocol.json`, hash-frozen; changes are logged amendments (D01) |
| Each researcher builds vocabulary in their own sheet | Isolated lexicon scouts and a PRESS review (D02) |
| Independent searches, then compare the overlap (~90%) | Sampling units (scout × channel), Chao2 + sample coverage + a holdout probe (D03–D04) |
| Follow references backward and forward | Snowballing through alternatives, integrations and "vs" pages (D05) |
| Dual screening with reasons | Screener A + blind screener B, Krippendorff's α, PRISMA flow (D06) |
| Concept matrix / evidence gap map | Competitor matrix, strategy canvas, demand–supply gap map (D15–D16) |
| Double-coding qualitative data | JTBD codebook, coder A + blind coder B, α per code, theme saturation (D13–D14) |
| Gap-spotting and problematization | Confusion / neglect / application spotting, ERRC, change-one-dimension (D17–D19) |
| Peer review and certainty of evidence | Red team and pre-mortem; GRADE-CERQual-style certainty (D21–D22) |

`docs/method-map.md` traces every method from the original research-gap and market-gap answers to its card, script and status, including what was excluded and why. `docs/research-notes.md` records the verified sources, formulas and test vectors.

## Repository layout
```
skills/market-gap-discovery/   SKILL.md, agents/ (8 role briefs), references/ (cli, metrics, glossary, sources,
                               human-ops, portability, methods/D01-D25), scripts/gapscan.py, assets/
skills/market-gap-validation/  SKILL.md, agents/ (4 role briefs), references/ (cli, metrics, glossary, ethics,
                               human-ops, methods/V01-V10), scripts/gapval.py, assets/templates/
shared/                        single source of truth for mgcore (math, schemas, glossary) -> copied into both skills
tools/sync_shared.py           copy shared/ into the skills (run after editing shared/)
tests/                         stdlib unittest suite (math vectors, safeguards, end-to-end simulations, structure)
evals/                         scenario evals and trigger evals for both skills
docs/                          method map and research notes
```

## Install
Each skill folder is self-contained (standard-library Python 3.8+, no dependencies). Symlink it where your agent looks for skills:

```bash
REPO=/path/to/build-skills-center
# Claude Code (and OpenCode, which also reads .claude/skills); use ~/.claude/skills for all projects
mkdir -p .claude/skills && ln -s $REPO/skills/market-gap-discovery $REPO/skills/market-gap-validation .claude/skills/
# Codex CLI and OpenCode (.agents/skills); use ~/.agents/skills for all projects
mkdir -p .agents/skills && ln -s $REPO/skills/market-gap-discovery $REPO/skills/market-gap-validation .agents/skills/
```

Codex runs with network access disabled by default; enable it for discovery runs. `agents/openai.yaml` in each skill is optional display metadata for Codex.

**Claude Code permissions (optional).** To avoid a prompt for every script call, allow the two scripts in `.claude/settings.json`:
```json
{"permissions": {"allow": ["Bash(python3 */skills/market-gap-discovery/scripts/gapscan.py:*)",
                           "Bash(python3 */skills/market-gap-validation/scripts/gapval.py:*)"]}}
```

**Before a run, the human may set:**
- `MGD_CONTACT`: a contact string (URL or email) sent in API User-Agents. It is required by Wikimedia and is only ever sent when you set it.
- `gh auth login`: for GitHub search.
- Optional keys such as `STACKEXCHANGE_KEY`, `SERPAPI_KEY`. `assets/channels.json` lists the tier-2 sources.

## Use
Ask the agent in plain words, for example "find market gaps in scheduling software for small dental clinics", "validate the top opportunity", or "test whether lawyers would pay for AI meeting notes". The skills drive themselves through one loop:

- `gapscan.py next RUN` (discovery) or `gapval.py next RUN` (validation) prints exactly one action: `RUN` a script, `SPAWN` independent subagents, `DO` a judgment task, `BLOCKED` on a human task, or `DONE`.
- A run is a folder (`gap-runs/<slug>/`). It can be resumed in any session or tool, and every intermediate artifact is kept for audit.

Deliverables:
- discovery: `output/dossier.md`, `output/handoff.json`, `output/prisma.md`, `output/watchlist.json`
- validation: `validation/report.md`, `validation/verdict.json`, `validation/validated-handoff.json`, Learning Cards

**The human's role.** The human is the operator: accounts, keys, payments, publishing, posting, recruiting and data exports are human tasks (`hq list` shows them).
- In `autonomous` mode, discovery runs without stopping; optional tasks fall back to recorded coverage gaps.
- In `gated` mode, the human approves the protocol, the landscape and the shortlist.
- Validation always waits for the human before anything outward-facing.

## Tests
```bash
python3 -m unittest discover tests      # math vectors, safeguards, end-to-end simulations, structure checks
python3 tools/sync_shared.py --check    # shared copies in sync
```
The end-to-end tests run a whole discovery run and a whole validation run with simulated subagents, a simulated human operator and a fake network. They cover init through DONE, the probe blocking a false stop, tamper detection, and the honesty checks.

## Known limits
- **Desk evidence is weak evidence of demand.** Discovery ranks gaps; only validation experiments can show people will act or pay.
- **Sources are limited by access and terms.** Review sites that forbid automated use (G2, Capterra, GetApp, TrustRadius), Indie Hackers, Upwork/Fiverr scraping, and Reddit without approved API access are excluded. Tier-2 sources (SerpApi, DataForSEO, Product Hunt, Reddit OAuth, Google Trends alpha) have registry entries but no scripted adapters yet; they are recorded as coverage gaps.
- **Some free sources are unreliable or closed to agents (seen in a live run, 2026-10-09).**
  - AlternativeTo answers 403.
  - Apple's review feed is intermittently empty.
  - Some vendor sites block AI agents in robots.txt.
  
  Each case is logged as a coverage gap and reported, never worked around.
- **The stopping test for large evidence pools needs more budget than a standard miner assignment.** Untested, truncated pools are reported in `prisma.json` as a limitation.
- **Measuring every frequent code costs coder time.** With many rare codes, the stratified reliability sample is large: in the live run, 95 of 201 records were double-coded so that all 38 frequent codes could be measured. A random 20% sample would have measured 3.
- **Saturation is a lower bound.** Same-model scouts are correlated. Personas, channel rotation and the holdout probe reduce this but cannot remove it.
- **Thresholds are partly design operationalisations.** The certainty operationalisation and the scoring weights and anchors are design defaults, documented with their sources in `assets/defaults.json` and changeable only through a logged protocol amendment.
- **Planned next skills:** build (MVP from `validated-handoff.json`), launch / go-to-market, and monitor (re-runs from `watchlist.json`, the post-launch PMF survey).
