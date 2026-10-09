# Human operations

The human operator is the run's hands in places agents shouldn't act: accounts, keys, money, legal acceptance and anything visible to other people. They also make the judgement calls at gates. Everything else the agents do on their own, so the human can stay out of the loop until a task actually needs them.

Contents
1. What only the human does
2. The human-task record and commands
3. Autonomy modes and gates
4. Directives
5. Example tasks

## 1. What only the human does
| Type | Examples |
|---|---|
| `account` | `gh auth login`; creating an API account |
| `key` | setting `MGD_CONTACT`, `STACKEXCHANGE_KEY`, `SERPAPI_KEY` as environment variables |
| `payment` | approving paid API credits (DataForSEO, SerpApi beyond its free tier) |
| `legal` | accepting API terms; asking a vendor for commercial-use permission (Product Hunt) |
| `outward-action` | anything other people would see: posts, messages, emails, ads (not used in discovery) |
| `judgment` | approving the protocol, the landscape or the shortlist in gated runs |
| `directive` | the human steering the run ("focus on X", "drop segment Y") |

What agents must never do:
- post, message or email anyone
- sign up for anything or log in
- accept terms
- spend money or create API keys
- change account settings

Secrets travel only as environment variables. Never write a key into a file, a URL, a query log, a note or an output. A secret in the run folder is a leak, because run folders get shared.

## 2. The human-task record and commands
Each task follows `human-task.schema.json`:
- `id` (HT-NNN), `type`, `title`
- `why` (what it unlocks)
- `steps` (exact instructions)
- `returns` (what the human hands back, for example "environment variable SERPAPI_KEY set")
- `phase`, `blocking`, `fallback` (what happens if declined)
- `status` (open, done, declined), `note`, `created_at`, `closed_at`, `gate`

Commands (`python3 SKILL_DIR/scripts/gapscan.py ...`):
- `hq add RUN --type key --title "..." --why "..." --steps "..." --returns "..." --phase P3 [--blocking] [--fallback "..."]`
- `hq list RUN`: open and closed tasks. `human-tasks.md` is a rendered view; don't edit it.
- `hq done RUN HT-004 --note "set in shell profile"` or `hq decline RUN HT-004 --note "no budget"`

Write `steps` so a non-expert can follow them without asking anything back. Name the exact page, command or setting, and say what "done" looks like.

## 3. Autonomy modes and gates
- **`autonomous`:** optional tasks never block. `next` takes the fallback and records it, for example "tier-2 search volume skipped; coverage gap noted". Discovery is read-only research, so a fully autonomous run is safe.
- **`gated`:** `next` creates `judgment` tasks and returns `BLOCKED HT-NNN` until each one is closed:
  1. **Protocol approval:** before `protocol freeze`, so the human approves the question, scope, thresholds and founder fit.
  2. **Landscape approval:** after saturation and snowballing, before mapping. The human can add known competitors as a directive.
  3. **Shortlist approval:** after `score`, before the report.

A blocking task stops the loop in either mode. Use `--blocking` only when nothing sensible can continue without it, for example when no network is available at all.

## 4. Directives
The human can steer at any time. Record each directive before acting on it, so the audit trail explains why the run changed:
```
gapscan.py protocol amend RUN --reason "directive: focus on agency-billed translators" --set 'scope.in=["agency-billed freelance translators"]'
```
Then continue the `next` loop. When a directive asks for something that only re-running a step can satisfy, for example "redo the red team for GAP-004", say so and let `next` and the scripts drive the re-run. Never edit artifacts by hand.

## 5. Example tasks
```json
{"id": "HT-001", "type": "key", "title": "Set a contact string for API User-Agent headers",
 "why": "Wikimedia requires a contact in the User-Agent; other APIs treat identified clients better.",
 "steps": "Choose a contact you are happy to share with API operators (a project URL or a dedicated email). Run: export MGD_CONTACT='<your contact>' in the shell that runs the agent.",
 "returns": "Environment variable MGD_CONTACT set", "phase": "P0", "blocking": false,
 "fallback": "Skip Wikimedia pageviews; record a coverage gap", "status": "open", "created_at": "2026-10-09T09:00:00Z"}
```
Other common tasks, in short:
- **HT `key`, STACKEXCHANGE_KEY:** register a free Stack Apps key and export it. Fallback: unauthenticated quota of 300 requests/day.
- **HT `account`, GitHub CLI login:** run `gh auth login` and choose the browser flow. Fallback: skip the `gh` family and record a coverage gap.
- **HT `key` + `payment`, SERPAPI_KEY:** create a SerpApi account (250 free searches/month) and export the key. Fallback: no search-volume signal.
- **HT `judgment`, approve shortlist (gated):** read `gaps/ranking.json` and the red-team verdicts, then `hq done` with any exclusions written in `--note`.
