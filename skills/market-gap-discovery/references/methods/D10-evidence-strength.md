# D10 · Evidence strength grading

| Origin | Phase | Roles | Status |
|---|---|---|---|
| The Mom Test (Fitzpatrick): specifics about the past beat opinions and hypotheticals; Testing Business Ideas (Bland & Osterwalder): evidence strength, doing over saying, facts over opinions; source-credibility flags as a risk-of-bias input (GRADE) | P3 Evidence (re-graded during P4 coding) | miner, coder | core |

**Use when:** on every evidence record. Miners grade it when they write the record; coders re-grade it during closed coding.

**Why:** Not all evidence is equal. "Someone should build X" costs nothing to say, while "we pay a freelancer every month to do X" shows the problem already costs money. Founders and agents alike over-weight enthusiastic opinions, which is exactly the trap The Mom Test warns about.

Grading every record on a fixed ladder has three effects:
- Scripts can weight demand by what people did, not what they said (`evidence.strength_weights`).
- Certainty can rise when money is involved (D22).
- Desk research stays honest. However many S4 records exist, desk-only demand remains "weak" until validation produces behaviour toward your own offer.

**Inputs**
- The quote, plus its surrounding text in the snapshot `.txt`.
- The record's `stance`.
- The rules in D09.

**Procedure**
1. Read the quote in its context, but grade only what the quote itself shows.
2. Pick the highest level the quote supports. The examples are illustrative.
   - **S0, hypothetical or opinion:** future, conditional or general statements. "I would pay for a tool that…", "Someone should build…", "It would be nice if…".
   - **S1, generic complaint:** experience with no specific episode. "Invoicing in X is clunky." "Chasing payments is a pain."
   - **S2, a specific past event:** a concrete situation with a time, a number or a consequence. "Last month I lost two days matching 300 payments because X can't import my bank file."
   - **S3, workaround effort:** time or tools spent getting around the problem. "I keep a Google Sheet with twelve formulas to…", "we wrote a script that…", "every Friday I export the CSV and fix it by hand."
   - **S4, money spent or a paid switch:** a purchase, a hire or a paid switch for the job. "We pay a freelancer $400 a month to…", "switched from X to Y at twice the price because…", "bought a $29 template for…". A job post that hires someone to do the job by hand also counts as S4, because money is being spent on the job.
3. Write a `strength_note` (at most 200 characters) naming the words that justify the level. Example: "'every Friday I export…' = recurring manual workaround".
4. Set `credibility`:
   - `independent`: a user or buyer with no visible tie to a vendor.
   - `vendor`: written by the vendor or its staff (blog posts, staff replies, product pages, case studies).
   - `incentivized`: the author received something for writing it (a free licence, a gift card, "sponsored", a review campaign).
   - `affiliate`: listicles or posts with referral links or commissions.
   - `unknown`: you cannot tell.
5. Set `indirect` to true when either applies:
   - The speaker is an adjacent persona rather than the protocol's population (an enterprise IT admin when the protocol targets freelancers).
   - The quote states a preference rather than a behaviour. Most S0 records are like this.
6. Keep stance and strength separate. Praise can be S2 ("it saved me three hours yesterday"). A wish is usually S0, but becomes S3 when the same post shows the workaround the person built.
7. **Coders:** re-grade strength in closed coding (`code-assignment` field `strength`) without looking at the miner's grade. The double-coded sample makes strength part of the reliability check (D14).

**Output:** the fields `strength`, `strength_note`, `credibility` and `indirect` on each evidence record, plus `strength` on each code assignment.

**Metrics and checks**
- Demand weights (`evidence.strength_weights`) are S0 0.25, S1 0.5, S2 1.0, S3 1.5 and S4 2.0. The gap map (D16) uses them for strength-weighted counts of distinct authors.
- Scoring anchors for Pain and Pay rely on S3 and S4 counts (D23). The certainty upgrade for magnitude needs S4 evidence from at least `certainty.magnitude_min_authors` (3) authors (D22).
- The share of `vendor`, `incentivized` and `affiliate` records drives the risk-of-bias downgrade (`certainty.bias_moderate` 0.15, `certainty.bias_serious` 0.3).
- Records older than `evidence.stale_months` (12) months are flagged as stale in reports.

**Pitfalls**
- **Grading by tone.** An angry quote is not behaviour.
- **Upgrading by inference** ("they probably pay for…"). Grade only what is written.
- **Counting a vendor's case study as S4 user evidence.** It is `vendor` credibility, whatever it claims.
- **Treating a pile of S0 wishes as demand.** They are mostly indirect, and the weights already discount them.

**Done when:** every record you wrote has a strength with a justifying note, a credibility flag, and the `indirect` flag wherever it applies.
