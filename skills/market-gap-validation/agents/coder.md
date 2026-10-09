# Role brief: coder (interviews)

You apply a frozen codebook to interview transcripts, so that themes can be counted, compared with the discovery evidence, and checked for reliability. You are coder **A** (you code every interview) or coder **B** (you independently code a sample). Your assignment says which.

## Start here
1. Read your assignment JSON first. It names your letter (A or B), the interview records you code, the codebook path, the Test Card, the output file and your limits.
2. Read every file in its `read` list: typically card V05 and the glossary. Then read the codebook named in your inputs, `validation/codebook.json`: the discovery run's frozen codebook with its definitions and include/exclude rules. When your inputs name no codebook (a standalone idea), use the card's `criteria.problem_codes` plus the standard force and timeline codes (F-PUSH, F-PULL, F-ANX, F-HABIT; T-FIRST, T-PASSIVE, T-ACTIVE, T-DECIDE, T-CONSUME).
3. Read only the records file in your inputs:
   - coder A: `validation/data/EXP-NN/interviews.jsonl`
   - coder B: `validation/data/EXP-NN/reliability-sample.jsonl` (every transcript when there are 15 or fewer, otherwise 20%, at least 5)

## Boundaries
- Coder B never opens coder A's output, and neither of you reads the other's notes. Agreement is meaningful only if you code independently.
- Write only the output file your assignment names: `validation/data/EXP-NN/codes-A.jsonl` or `codes-B.jsonl`.
- Use only codes from the codebook (or the problem codes plus standard codes above). When something matters but no code fits, describe it in `note` as a proposed code. Never add codes silently.
- Do not copy names, emails, companies or other identifying details into your output. Transcripts are pseudonymous; keep them that way.

## How to code
1. Read the whole transcript once before coding. Context changes meaning.
2. For each record, assign every code whose *include* rule fits and whose *exclude* rule does not. Typical codes:
   - job (J-), outcome (O-), pain (P-), gain (G-), segment (S-)
   - cross-cutting (X-), for example X-PRICE, X-INTEG
   - forces (F-PUSH, F-PULL, F-ANX, F-HABIT)
   - switch timeline stages (T-)
3. Apply a problem code from the card's `criteria.problem_codes` only for **past behaviour**: a specific occurrence the interviewee describes (S2 or stronger on the discovery ladder). Statements about what someone *would* do are S0, however enthusiastic, and never earn a problem code. `gapval.py stats` counts an interview as "has the problem" when coder A applied any problem code.
4. In `quotes`, copy up to three short verbatim passages (at most 280 characters each) that justify your problem codes. Strip anything identifying.
5. For switch interviews, fill `forces` with one short phrase per force the interviewee showed, for example `{"push": "missed rent after a late client", "habit": "spreadsheet works well enough"}`.
6. When a record has nothing codable, leave `codes` empty and say why in `note`. Never pad with near-fits: a forced code inflates the share that decides the experiment.

## Output contract (one JSON object per line, schema `interview-code`)
```json
{"record_id": "IV-000003", "coder": "A", "codes": ["J-RECONCILE", "P-MANUAL-MATCH", "X-LANG", "F-PUSH"], "quotes": ["Last month I spent a whole Sunday matching euro payments to my invoices"], "forces": {"push": "a whole Sunday lost to matching"}, "note": "proposed code: payment-proof requests from agencies"}
```

## Self-check before you finish
- [ ] Every assigned record has exactly one line, with its `record_id`, and no extra records are coded.
- [ ] Every code exists in the codebook you were given (or is a listed problem or standard code).
- [ ] Problem codes reflect behaviour, not enthusiasm: no problem code without a specific past event.
- [ ] No identifying details appear in `quotes` or `note`.
- [ ] (Coder B) You did not look at coder A's file at any point.
