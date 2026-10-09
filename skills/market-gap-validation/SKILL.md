---
name: market-gap-validation
description: Designs, pre-registers, runs (with a human operator for every outward action) and analyses validation experiments for a SaaS opportunity, then returns a deterministic GO / ITERATE / PIVOT / KILL verdict. It covers Opportunity Solution Trees, assumption mapping, frozen Test Cards with XYZ hypotheses and sample sizes, honest smoke tests and fake doors, Mom Test and switch interviews, ODI, Kano and Van Westendorp surveys, pre-sales and LOIs, Wilson-interval decisions, and Learning Cards. Use after market-gap-discovery, or whenever the user wants to validate a SaaS idea, test demand or willingness to pay, run a landing-page or waitlist test, interview customers, or decide whether to build. For finding gaps in the first place use market-gap-discovery.
compatibility: Python 3.8+ standard library. Parallel subagents recommended (Claude Code Agent tool, OpenCode Task tool, Codex delegation). A human operator is required for publishing, posting, recruiting, payments and data exports.
metadata:
  version: "1.0.0"
  suite: market-gap-skills
---

# Market gap validation

This skill tests the riskiest assumptions behind one opportunity with real behaviour. It decides with rules frozen before any data arrives. Its inputs and outputs:
- **Input:** a discovery run's `output/handoff.json`, or a one-line idea for standalone use.
- **Output** in `RUN/validation/`:
  - `verdict.json`: GO, ITERATE, PIVOT or KILL, with reasons
  - `report.md` and Learning Cards
  - `validated-handoff.json`: for build, launch and monitor agents

## Principles
1. **Test the riskiest assumption with the cheapest experiment that could prove it wrong.** Then escalate the evidence (click < email < booked call < LOI < deposit or pre-sale). Saying is weaker than doing; money is the strongest signal.
2. **Pre-register.** Each Test Card fixes its hypothesis ("at least X% of Y will Z"), metric, sample size, decision rule and actions on pass, fail or inconclusive. `prereg freeze` hashes it, and any later edit is reported as TAMPERED. Derive X from unit economics, not from generic benchmarks.
3. **The human does every outward action.** Agents draft. The human publishes pages, posts in communities (from their own account, with affiliation disclosed), recruits interviewees, creates payment links, spends on ads and exports data. `next` turns these into blocking human tasks in every autonomy mode.
4. **Be honest with participants.**
   - Fake doors reveal the truth right after the click.
   - Every email collection has consent and a privacy notice.
   - Nobody is charged without explicit consent.
   - No fabricated testimonials, counts, logos or ratings: `assets check` enforces this.
   - Only pseudonymous ids enter the run folder.
5. **Scripts decide.** `stats` applies each frozen rule and `verdict` combines them. When critical assumptions disagree, the most conservative pre-registered action wins (KILL > PIVOT > ITERATE > GO). Never soften a result in prose.

## Quick start
`V` stands for `python3 SKILL_DIR/scripts/gapval.py`.
1. After discovery: `V init RUN`. This picks the top-ranked opportunity; use `--gap GAP-NNN` for another.
2. Standalone idea: `V init idea-runs/<slug> --idea "<one line>"`. Certainty starts at "Very low".
3. Loop on `V next RUN` until `DONE`, exactly as in the table below.
4. Report the verdict, the evidence strength and the Learning Cards. Point to `validated-handoff.json` as the base for building.

## The `next` loop
| First line | Do this |
|---|---|
| `RUN gapval.py ...` | Run it (the NOTE `cmd:` line has the full path). On exit 1, read the message and fix the inputs. |
| `SPAWN <role> <n> <paths>` | One subagent per assignment, in parallel; see "Spawning subagents". |
| `DO <card> <task>` | Read the method card in `references/methods/` and do the task, for example fixing a Test Card or creating UTM links from the deployed URL. |
| `BLOCKED HT-NNN` | Show the human the task with `V hq list RUN`, including the drafts it points to, then wait for `hq done` or `hq decline`. |
| `DONE` | Report the verdict and deliverables. |

## Spawning subagents
Give each subagent this prompt:

> You are the `<role>` in a market-gap validation run. First read `<absolute assignment path>`. Then read exactly the files in its `read` list (relative to `<SKILL_DIR>`) and the inputs it names. Write only the paths in `outputs`. You draft; you never publish, post, send, deploy or spend. Finish with one line: `done` or `blocked: <reason>`.

- **Claude Code:** Agent tool, one message per SPAWN.
- **OpenCode:** Task tool.
- **Codex:** explicit delegation.
- **No subagents:** do the assignments one at a time, re-reading only that assignment.

Coder B must never see coder A's output, so run B in a fresh context.

## Phase checklist
- [ ] V1 Frame: the Opportunity Solution Tree with at least 3 genuinely different solutions (**V01**); the assumption map ranked by importance × missing evidence (**V02**).
- [ ] V2 Design: choose experiments (**V03**); fill and freeze Test Cards: XYZ, X derivation, `samplesize`, decision rule, actions, ethics, human-task slugs (**V04**); the human approves the plan and budget.
- [ ] V3 Assets: interview guides (**V05**), surveys (**V06**), landing page and posts (**V07**); `assets check`.
- [ ] V4 Launch: the human deploys, posts, recruits and runs payment links (**V08**); create UTM links once deployed.
- [ ] V5 Collect and analyse: the human exports pseudonymous data; `ingest`; interview coding with α and saturation; `stats` (**V09**).
- [ ] V6 Decide: `verdict`, Learning Cards, report, validated handoff (**V10**), `validate`.

## Experiment choices at a glance
| Assumption | Cheapest falsifying test first | Stronger follow-up |
|---|---|---|
| Problem is real and frequent (desirability) | Mom Test problem interviews (≥10, until saturated) | Smoke test with a waitlist (email level) |
| They want this solution (desirability) | Smoke test or fake door with honest disclosure | Booked calls, concierge |
| They will pay this price (viability) | Van Westendorp + NMS pricing survey (100–200 per segment) | LOIs, deposits, pre-sales |
| Which outcomes are underserved | ODI survey (n ≥ 180) | — |
| Which features delight or are expected | Kano survey (n ≥ 200, otherwise directional) | — |
| We can build it (feasibility) | Technical spike with acceptance tests | — |

## Reference files
- `references/cli.md`: every command and the folder layout.
- `references/metrics.md`: Wilson decisions, sample size, ODI, Kano, Van Westendorp/NMS, PMF and verdict rules, with worked examples.
- `references/ethics.md`: honest experiments, consent, privacy and community rules.
- `references/human-ops.md`: the validation human tasks.
- `references/glossary.md`: the shared vocabulary.
- `agents/*.md`: role briefs (designer, builder, coder, analyst).
- `assets/templates/`: landing page, privacy notice, interview guides, surveys, Test and Learning Cards, post drafts.
- `assets/defaults.json`: thresholds, each with its source.
