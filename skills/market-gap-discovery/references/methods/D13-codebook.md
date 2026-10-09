# D13 · Codebook (JTBD, job map, outcomes, forces)

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Jobs-to-be-Done (Christensen); universal job map (Bettencourt & Ulwick 2008); Outcome-Driven Innovation outcome statements (Ulwick); Value Proposition Canvas (Osterwalder); Forces of Progress and switch timeline (Moesta & Spiek); qualitative codebook practice (O'Connor & Joffe 2020) | P4 Coding | coder (A) | core |

**Use when:** `next` issues `SPAWN coder` for `coding/open-assign-vN.json`. That happens once after the first evidence round is merged and verified, and again in revision mode when `agreement` returns revise.

**Why:** Raw quotes can't be counted; coded quotes can. A codebook turns hundreds of complaints into a small set of jobs, outcomes, pains and segments, each with explicit rules. Two coders working independently can then reach the same labels (D14), and every later number (gap map, scores) rests on reproducible categories. Codes describe the customer's progress, never a product idea, which keeps the analysis open to solutions the incumbents missed.

**Inputs**
- `coding/open-assign-vN.json`: a base sample of `coding.open_base_n` (30) verified records from `evidence/ledger.jsonl`, stratified by source type. In revision mode it also lists the codes to revise, their disagreements and both coders' pooled proposals.
- Protocol PICOS (population and job) and the glossary.

**Procedure**
1. Read every record in the base sample before writing any code. For each one, note:
   - the job: what progress the person is trying to make
   - the circumstance
   - the outcome they measure
   - pains and gains
   - the segment
   - for switch stories, the forces and the timeline stage
2. Name jobs (J-) as verb + object + context, without products. A job is "the progress that a person is trying to make in a particular circumstance" (Christensen). Example: J-RECONCILE-PAYMENTS, defined as "reconcile client payments with issued invoices".
3. Place each job on the job map with `job_step`: define, locate, prepare, confirm, execute, monitor, modify or conclude. Use the map as a coverage checklist: for each core job, note which steps have evidence and which have none. Empty steps are leads for D16 and D17, not codes.
4. Write outcome codes (O-) as desired-outcome statements in `outcome_statement`, using direction + metric + object of control + contextual clarifier. Attach each outcome to its job with `parent`. Examples:
   - "Minimize the time it takes to match a bank payment to its invoice when a client pays several invoices at once."
   - "Minimize the likelihood of sending an invoice in the wrong currency to a foreign client."
5. Code pains (P-) and gains (G-) as in the Value Proposition Canvas:
   - Pains are undesired outcomes, obstacles and risks.
   - Gains are required, expected, desired or unexpected benefits.
   
   Keep pains specific (P-MANUAL-ENTRY), never evaluations like "bad UX".
6. Code segments (S-) by shared job, context and buying process, for example S-SOLO-TRANSLATOR or S-AGENCY-5-20. Code a segment only when the record states or clearly implies it; leave an unknown segment uncoded.
7. Do not define X-, F- or T- codes. `codebook freeze` adds the standard set:
   - **Cross-cutting:**
     - X-FRAG: juggling several tools, no single place
     - X-INTEG: tools don't connect
     - X-PRICE: too expensive for the value or the segment
     - X-COMPLEX: too complex for this user
     - X-LANG: language, currency or locale missing
     - X-SUPPORT: support missing or slow
     - X-RELIAB: breaks, loses data, downtime
     - X-SCALE: the pain grows with usage or volume
   - **Forces:** F-PUSH, F-PULL, F-ANX, F-HABIT. People switch when push + pull exceed anxiety + habit.
   - **Switch timeline:** T-FIRST (first thought), T-PASSIVE (passive looking), T-ACTIVE (active looking), T-DECIDE (deciding), T-CONSUME (consuming).
   
   Use them while coding. Propose a new cross-cutting code only when a recurring pattern has no home.
8. For every code, write:
   - `definition`
   - `include`: what qualifies, as a decision rule
   - `exclude`: near-misses and which code they belong to instead
   - 1–3 `examples` (EV ids)
   
   Aim for 20–40 codes of your own. Fewer collapses distinct needs; more makes reliability collapse.
9. Use ids matching `^(J|O|P|G|S|X|F|T)-[A-Z0-9-]{1,24}$`, with the matching `type`:
   - J → job
   - O → outcome
   - P → pain
   - G → gain
   - S → segment
   
   Write the draft to the output path in your assignment (`coding/codebook-draft-vN.json`, one file per version) with `version` = previous version + 1 (1 for the first draft). The orchestrator then runs `gapscan.py codebook freeze RUN`.
10. **Revision mode** (`assign --phase coding-open --revise`). The assignment lists `codes_to_revise` with their α, the `disagreements` (quotes where coders A and B split on that code) and the pooled `proposals` of both coders. For each listed code, read its disagreements, then do one of:
    - sharpen its include/exclude rules
    - split a code that mixes two ideas
    - merge two codes the coders confused
    
    A listed standard code (X-, F-, T-) is sharpened the same way. Copy its entry from the current codebook and change only `include`, `exclude` and `examples`; `codebook freeze` keeps its id, type, label and definition, so runs stay comparable, and carries the sharpening into later versions.

    Then read the proposals, each with up to 5 of its quotes. Treat labels that mean the same thing as one proposal. Add a code for each proposal that at least `coding.min_positives_per_code` (5) records support, especially one both coders raised independently. Leave codes that passed unchanged. Give every changed or new code examples, and increment `version`.

**Output:** `coding/codebook-draft-vN.json` (codebook.schema.json). `codebook freeze` adds the standard codes, validates the codebook and writes the frozen copy `coding/codebook.vN.json`, and records its hash and the changes since the last version in `coding/codebook.lock.json`. A revision that leaves every listed code unchanged is refused.

**Metrics and checks**
- `codebook freeze` rejects ids that don't match the pattern, unknown types, fewer than 5 codes and definitions shorter than 10 characters. Closed coding may only use a frozen version.
- The dossier reports job-map coverage per job: steps with evidence vs. steps without.
- Reliability is measured in D14, but the rules you write here decide it: a code without a usable exclude rule usually fails α.

**Pitfalls**
- **Solution-shaped codes** ("needs AI invoicing"). Code the job and the outcome; solutions come later, in P5 and in validation.
- **Vague pains** ("frustrating"). Ask frustrating because of what: time, errors, cost, risk? Code that.
- **Vendor claims coded as needs.** Vendor pages are supply evidence (D15), not jobs.
- **Hidden segments.** When people disagree about the same feature, check whether they belong to different segments before treating the disagreement as noise. D17's confusion scan depends on segment codes.
- **Too many codes from 30 records.** Keep one-off ideas as proposals and let later records confirm them.

**Done when:** `codebook freeze` has accepted the codebook and `next` has moved on to closed coding, or to recoding after a revision.
