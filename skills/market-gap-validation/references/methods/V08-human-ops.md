# V08 · Human operations and launch

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Human-operator protocol of this skill system; GDPR consent and transparency; platform and community rules | V4 Launch | orchestrator, human operator | core |

**Use when:** after the cards are frozen (plan approval) and after `gapval.py assets check` passes (launch), and whenever an operation is missing from the queue.

**Why:** Validation touches the outside world: a page goes live, a post appears in a community, an ad spends money, a stranger gets an email. Those actions carry the human's identity, money and reputation, and they are hard to undo. So the agent prepares everything and the human performs, or explicitly authorises, every outward action. This holds even when the run's autonomy is `autonomous`. Autonomy only changes who approves *internal* steps.

**Inputs:** the frozen cards (`required_ht`, `channels`, `budget_usd`, `exposure_limit`), the checked assets in `validation/assets/EXP-NN/`, and `references/human-ops.md` (task catalogue and examples).

**Procedure**
1. Run `gapval.py hq list RUN` to see the queue. `gapval.py next` creates the tasks below automatically; do not add duplicates.
2. **Plan approval (automatic).** Once every card is frozen, `next` adds one blocking `judgment` task that lists each experiment's type, X, `min_n` and budget, so the human approves the whole plan in one place. A decline with a note makes `next` ask you to revise: close or replace experiments with new cards (new ids), and approval is requested again.
3. **Launch tasks (automatic).** For each frozen card, `next` adds one blocking task per `required_ht` slug, in the card's order, plus an "EXP-NN: export results" task that names the exact data paths (`validation/data/EXP-NN/<kind>.csv`, or `validation/data/EXP-NN/interviews/` with one `.txt` per interview). The task type comes from the slug's words:
   - deploy, hosting, domain, form, analytics → `account`
   - stripe, payment, presale, deposit, ads, budget → `payment`
   - post, outreach, email, recruit, publish → `outward-action`
   - legal, privacy → `legal`
   - anything else → `outward-action`
   
   Add extra tasks only for operations the cards missed, for example a `key` task for a deploy token: `gapval.py hq add RUN --type key --title "..." --why "..." --steps "..." --returns "..." --phase V4 --blocking`.
4. **Waiting.** `gapval.py next RUN` returns `BLOCKED HT-NNN` while a blocking task is open. Stop there. Do not look for a way around it. On landing-page tests, once the deploy task is closed with the live URL in its note, `next` returns `DO V07` to create the UTM links before any posting task.
5. **Closing.** The human records the outcome with `gapval.py hq done RUN HT-NNN --note "..."` (including the live URL, the date posted, or the environment variable's *name*), or `gapval.py hq decline RUN HT-NNN --note "..."`. Declining any launch or export task closes that experiment: the verdict lists it as NOT_RUN, and the report says why. A fallback channel needs a new card.
6. **Agent deployment** is allowed only when both of these hold:
   - the human has approved the publish task
   - the deploy token is in the environment variable named in that task
   
   Deploy exactly the checked files, then record the live URL in the task note through the human.
7. **During the run,** watch the `exposure_limit`. If it is reached, or if harm appears (complaints, a moderator warning, confusion about payment), add a blocking `judgment` task to stop the experiment, and tell the human immediately. To close a stopped experiment, the human declines its open export task with the reason. If its data should still be judged, the human exports what exists instead, and `stats` rules on it (below `min_n` it is INCONCLUSIVE).

**Output:** human tasks in `RUN/human-tasks.json` (schema `human-task`) and its rendered view `RUN/human-tasks.md`; live URLs and dates in task notes.

**Metrics and checks**
- Every slug in every frozen card's `required_ht` has exactly one task, created by `next`, plus one export task per experiment.
- Each task has a type, a `why`, exact `steps` and a `returns` description.
- No secret appears in any file in the run folder. Tokens live only in environment variables.

**Pitfalls**
- **"Small" outward actions.** "Just one post" is still the human's identity in a community. It needs a task and approval.
- **Posting without disclosure.** Every post and outreach message says that the human is building the product (`assets/templates/post-drafts.md`).
- **Ignoring community rules.** Many communities ban self-promotion or require approval from a moderator. Check the rules in the task steps; when they forbid it, use the fallback.
- **Spam and astroturfing.** No cross-posting the same text to many groups, no fake accounts, no friends posing as customers.
- **Secrets in notes.** Record the *name* of the environment variable, never its value.

**Done when:** every blocking task for the running experiments is done or declined with its fallback applied, and `gapval.py next RUN` moves on to data collection.
