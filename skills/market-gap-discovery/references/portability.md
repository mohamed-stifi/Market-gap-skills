# Running the skill in different agent tools

The method needs exactly two things from the agent tool:
- **Isolated subagents.** Scouts, screeners and coders must not see each other's work, or the agreement statistics mean nothing.
- **A shell that can run Python 3.8+.** Every count and every stop decision comes from `gapscan.py`.

Everything else is the same everywhere: the orchestrator calls `gapscan.py next RUN`, does what the first line says, and calls `next` again.

Contents
1. Install
- Model tiers
2. Claude Code
3. OpenCode
4. Codex CLI
5. No subagents available

## 1. Install
Keep one copy of the skill and link it where each tool looks. From the repository root:
```
mkdir -p .claude/skills .agents/skills
ln -s ../../skills/market-gap-discovery .claude/skills/market-gap-discovery
ln -s ../../skills/market-gap-discovery .agents/skills/market-gap-discovery
```
- Claude Code reads `.claude/skills/` (or `~/.claude/skills/`).
- Codex reads `.agents/skills/` (from the working directory up to the repository root, or `~/.agents/skills/`).
- OpenCode reads `.opencode/skills/`, `.claude/skills/` and `.agents/skills/`, plus their home-folder versions, so either link works for it.

The folder name must stay `market-gap-discovery`, matching the skill's `name`.

## Model tiers
Every assignment has a `model` block (`tier`: fast, standard or strong; `names`: the model name per tool), and `next` repeats it on a `NOTE model:` line after each SPAWN. Defaults come from `assets/defaults.json` → `models` and the protocol's `cost_profile`:

| Profile | Scout, screener, miner, coder | Reviewer | Synthesizer, red team, writer |
|---|---|---|---|
| `budget` | fast | fast | standard |
| `balanced` (default) | fast | standard | standard |
| `quality` | standard | standard | strong |

Fast-tier roles are the ones whose output a script checks (quotes, schemas, screening α, coding α), so a weak output is rejected rather than trusted. When a check fails, that role is escalated one tier automatically (`state.json` → `models.log`). If your tool cannot choose a model per subagent, every subagent runs on the session model; costs rise but the method is unchanged.

| Tier | Claude Code (`Agent` tool `model`) | OpenCode (agent config `model`) | Headless CLI |
|---|---|---|---|
| fast | `haiku` | `anthropic/claude-haiku-5-5` | `claude -p --model haiku`, `opencode run -m anthropic/claude-haiku-5-5` |
| standard | `sonnet` | `anthropic/claude-sonnet-5-5` | `claude -p --model sonnet` |
| strong | `opus` | `anthropic/claude-opus-5-5` | `claude -p --model opus` |

Codex: name the model when you delegate, or pass it with `codex exec -m <model>`; Codex model names change, so pick your installation's fast and default models.

## 2. Claude Code
When `next` prints `SPAWN <role> <n> <assignments…>`:
1. Send n Agent tool calls in **one message** so they run in parallel. Use the general-purpose subagent type for each, with `model` set from the `NOTE model:` line.
2. Give each the same short prompt, varying only the paths: "You are the <role>. Read `<assignment path>` first, then exactly the files in its `read` list (paths relative to `<skill folder>`). Write only the output path(s) it names. Reply with a two-line summary and any blocks you hit."
3. Wait for all of them, then call `next`.

Files in the skill's `agents/` folder are role briefs, not registered subagent types; the assignment tells each subagent which brief to read.

## 3. OpenCode
- Use the Task tool with the built-in `general` subagent and the same prompt as above.
- To run a tier on its own model, define one agent per tier in your OpenCode config (for example `gapscan-fast` with `model: anthropic/claude-haiku-5-5`) and use it for that SPAWN.
- If you aren't sure that several Task calls run in parallel, run them one after another.
- Independence still holds when they run in sequence: each Task subagent starts with a fresh context and receives only its assignment.
- The orchestrator must not paste one subagent's output into another's prompt.

## 4. Codex CLI
- Install under `.agents/skills/`. `agents/openai.yaml` is optional display metadata for Codex.
- Codex starts subagents only when explicitly asked. On `SPAWN`, say it outright: "Spawn <n> subagents in parallel, one per assignment file: <paths>. Each reads its assignment, then the files in its `read` list, and writes only its output path."
- Codex sandboxes start without network access. Discovery needs the network for search and `fetch`, so enable network access for the session in Codex's sandbox and approval settings before running `doctor`. If `doctor` still reports no network, raise a human task; don't continue with an empty search.

## 5. No subagents available
**Preferred fallback: one headless process per assignment.** Each process has its own context, so independence is preserved. Run them in the background and wait for all of them:
```
claude -p "You are the scout. Read <assignment> first, then the files in its read list. Write only its output path."
codex exec "<same prompt>"
opencode run "<same prompt>"
```

**Last resort: run the assignments one after another in your own context.** You will remember earlier results, so the scouts are no longer independent and agreement overstates coverage. Mark the run before starting:
```
gapscan.py protocol amend RUN --reason "independence degraded: no isolated subagents" --set 'independence="degraded"'
```
In a degraded run:
- the holdout probe becomes mandatory (D04)
- certainty is downgraded (D22)
- the dossier states the limitation

## Model notes
Smaller models can run the pipeline because the arithmetic and the decisions live in scripts. Keep each subagent to its role brief and its assignment, and keep the orchestrator's own reading to script summaries rather than raw outputs. That keeps the context small enough for long runs.
