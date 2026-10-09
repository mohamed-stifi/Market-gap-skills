# V01 · Opportunity selection and Opportunity Solution Tree

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Opportunity Solution Tree (Torres, *Continuous Discovery Habits*); Customer Development (Blank: customer discovery before customer validation) | V1 Frame | orchestrator (init), designer | core |

**Use when:** right after `gapval.py init`, once per opportunity you validate.

**Why:** If you validate a single solution, every test turns into "prove my idea right". An Opportunity Solution Tree separates three things:
- the **outcome** you are trying to move
- the **opportunity**: the unmet need, taken from discovery evidence
- at least three different **solutions** that could serve it

Assumptions then belong to one specific solution, so each test has a clear target. If the target solution fails, the tree already holds the pivot candidates. Torres' hidden-solution check ("Is there more than one way to address this opportunity?") stops the tree from collapsing into three variants of one idea.

**Inputs**
- `validation/opportunity.json`, written by `init`:
  - From a discovery handoff: the gap statement, ICP, JTBD outcomes, top quotes, competitors, pricing hypothesis, MVP scope, suggested experiments, assumptions and certainty.
  - From `--idea`: only the one-line idea, with certainty "Very low". Fill in what you can, and leave every unknown visible as an assumption.
- `output/handoff.json` and `output/dossier.md` from the discovery run, and `validation/codebook.json` (the discovery run's frozen codebook, copied by `init`), when they exist.
- Defaults: `solutions.min_solutions` (3), `assumptions.importance_scale` (1–5), `assumptions.evidence_scale` (0–5).

**Procedure**
1. Orchestrator: run `gapval.py init RUN` (it takes the top-ranked opportunity), `gapval.py init RUN --gap GAP-NNN`, or `gapval.py init RUN --idea "TEXT"`. Then follow `gapval.py next RUN`. It asks for `gapval.py assign RUN --phase ost` and then a designer subagent.
2. Designer: write one **outcome** for this validation round: a metric, a target and why it matters. For example: "30 consented waitlist sign-ups from freelance translators within 21 days, because 30 is the smallest list that can seed a paid pilot". Use one outcome; two outcomes split your attention and your traffic.
3. Write the **opportunity** in the customer's words and cite discovery evidence ids in `evidence_ids`. If the evidence shows distinct needs (different job-map steps or segments), list them as `sub_opportunities`. A standalone idea may have no evidence ids; leave the list empty rather than inventing any.
4. Generate **at least three solutions** that differ in kind, not only in features. For example: a vertical SaaS app, a plugin inside a platform the ICP already uses, a template or workflow pack, a done-for-you service run by hand (concierge), an API. Give each a one-line `concept` and a `differentiator` against the competitors in `opportunity.json`. Run the hidden-solution check on each one.
5. For each solution, list **at least three assumptions**, each typed:
   - **desirability**: they want it and will act on it.
   - **viability**: they will pay enough, and the unit economics work.
   - **feasibility**: you, or agents, can build and run it, including platform APIs, terms of service and the human operating load.
   
   Number assumption ids uniquely across the whole tree (A1, A2, … up to A99), so every Test Card can cite them without ambiguity.
6. Rate each assumption:
   - **importance** 1–5: how badly the solution fails if the assumption is false.
   - **evidence** 0–5 on the evidence ladder:
     - 0: nothing
     - 1: desk quotes, opinions, surveys or clicks
     - 2: email sign-ups
     - 3: booked calls
     - 4: letters of intent
     - 5: deposits or pre-sales
     
     Discovery quotes are people *saying* things about the job, not acting on your solution. So they count as 1 at most for solution-specific assumptions, even when a quote is S4 ("I pay a freelancer $200 a month").
   - **ICE**: impact, confidence and ease, each 1–10. ICE only breaks ties in the ranking.
7. Choose `target_solution`: the solution most directly supported by the opportunity evidence and the most buildable by agents. Explain the choice in `notes`. Keep the other solutions in the tree; they are your pivot options.
8. Write `validation/ost.json` and nothing else. The orchestrator runs `gapval.py ost check RUN`; fix every message and run it again until it passes.

**Output:** `validation/ost.json` (schema `ost`).

**Metrics and checks**
- `gapval.py ost check RUN` enforces:
  - at least `solutions.min_solutions` solutions, whose concepts are not duplicates of each other
  - at least three typed assumptions per solution, with ids unique across the whole tree
  - importance 1–5, evidence 0–5 and ICE 1–10
  - a `target_solution` that exists in the tree and has at least one desirability and one viability assumption
- `ost check` does not look up `evidence_ids`. Cite only ids that exist in the discovery ledger (`evidence/ledger.jsonl`). Evidence you cannot cite does not raise an evidence rating.

**Pitfalls**
- **Three features of one idea.** "Dashboard", "dashboard with AI" and "mobile dashboard" fail the hidden-solution check.
- **Untestable assumptions.** "People will like it" cannot be falsified. Rewrite it as a behaviour: "freelance translators who reconcile invoices monthly will join a waitlist from a post in their community".
- **Rating evidence by enthusiasm.** Use the ladder. A compliment is 0; a quote about the job is 1 at most.
- **Skipping feasibility.** Agent-built products often depend on a host platform, an API's terms or a manual step. Name those dependencies so they are not discovered after launch.
- **Importing discovery certainty as validation evidence.** A "Moderate" pain certainty says the problem exists, not that your solution will sell.

**Done when:** `gapval.py ost check RUN` passes and `gapval.py next RUN` moves on to `assumptions rank`.
