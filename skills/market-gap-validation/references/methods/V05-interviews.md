# V05 · Problem and switch interviews

| Origin | Phase | Roles | Status |
|---|---|---|---|
| *The Mom Test* (Fitzpatrick); switch interviews and Forces of Progress (Moesta & Spiek, JTBD); problem interviews before solution interviews, ≥10 good interviews (Maurya, *Running Lean*); thematic saturation (Guest, Namey & Chen 2020); Krippendorff's alpha | V3 assets, V5 collect | builder (guide), coder (A and B), human (conducts) | conditional: an interview card is frozen |

**Use when:** a frozen card has `type: problem-interviews` or `switch-interviews`.

**Why:** Interviews are the cheapest way to learn whether the problem is real, frequent and costly. They also give you the customer's own words for the landing page. They work only when you ask about **past behaviour, not opinions about your idea**: people are kind, and kindness is not evidence. Switch interviews go further. Someone who already changed tools can tell you what pushed them, what pulled them, and what almost stopped them.

**Inputs:** the frozen card, `validation/opportunity.json` (job, outcomes, segment, top quotes), `assets/templates/interview-problem.md` or `interview-switch.md`, and `validation/codebook.json` (the discovery run's frozen codebook, copied by `init`) when it exists.

**Procedure**
1. **Guide (builder).** Copy the matching template to `validation/assets/EXP-NN/interview-guide.md`. Tailor it with the job, outcomes and segment words from `opportunity.json`. Keep the consent script and the recording-consent question word for word.
2. **Recruiting and conducting (human).** Interviews are outward actions, so the human recruits, schedules and talks to people through human tasks (card V08). Interview only people who match the card's Y; friends and fans are not your ICP.
3. **Mom Test rules for the conversation:**
   - Talk about their life, not your idea.
   - Ask about specifics in the past, not generalities or the future.
   - Talk less and listen more.
   
   Good questions:
   - "Talk me through the last time this happened."
   - "What did you do about it?"
   - "What else have you tried?"
   - "What does it cost you in time or money?"
   - "Who else is involved?"
   - "Why was that hard?"
   
   Bad questions:
   - "Would you buy a tool that…?"
   - "How much would you pay?"
   - "Do you think this is a good idea?"
   - "Would you use…?"
   
   In the notes, discard compliments, fluff ("always", "usually", "would", "might") and feature requests. Dig for the reason behind a request instead. A good interview ends with a commitment or an advancement: an intro to a colleague, a follow-up slot, a pre-order.
4. **Switch interviews.** Walk the timeline: first thought → passive looking → the event that started active looking → active looking → the event that triggered the decision → deciding → consuming (buying and using). Then probe the four forces. People switch when push + pull exceed anxiety + habit.
   - **Push** of the situation
   - **Pull** of the new solution
   - **Anxiety** about the new
   - **Habit** of the present
5. **Transcripts.** The human saves one plain-text file per interview in `validation/data/EXP-NN/interviews/`, the folder named in the experiment's "export results" task. Name each file by a pseudonymous id (`INT-01.txt`, `INT-02.txt`, …) and remove names, emails, phone numbers and company names before saving: ingest rejects any transcript with an email address or phone number. `gapval.py next` then runs `gapval.py ingest RUN --experiment EXP-NN --kind interviews --file validation/data/EXP-NN/interviews/`, which turns each file into an `IV-NNNNNN` record in `validation/data/EXP-NN/interviews.jsonl`.
6. **Coding.** `gapval.py assign RUN --phase interview-coding` creates coder A's assignment; `gapval.py assign RUN --phase interview-reliability` creates coder B's.
   - Coder A codes every record in `interviews.jsonl` into `codes-A.jsonl` (schema `interview-code`), using `validation/codebook.json`. Without a codebook (a standalone idea), use the card's `criteria.problem_codes` plus the standard force and timeline codes (F-PUSH, F-PULL, F-ANX, F-HABIT; T-FIRST, T-PASSIVE, T-ACTIVE, T-DECIDE, T-CONSUME).
   - Coder B codes `reliability-sample.jsonl` into `codes-B.jsonl` without seeing A's codes. The sample is every transcript when there are 15 or fewer, otherwise 20% (at least 5).
   - Anything the codebook lacks goes into the record's `note` as a proposed code, never as a silent new code.
   - Run `gapval.py agreement RUN`. Per code, α ≥ `interviews.alpha_accept` (0.80) is accepted; 0.667–0.80 is provisional; below that, revise. A code needs at least `interviews.min_positives_per_code` (3) positives to be judged. A code coder A used that often but that coder B's sample never measured is reported in `unmeasured_codes` and makes the verdict provisional, never accept.
7. **Saturation.** Run `gapval.py themes RUN`. It applies Guest–Namey–Chen with base `interviews.gnc_base` (4), run `interviews.gnc_run` (2) and threshold `interviews.gnc_threshold` (≤5% new themes). Stop interviewing only after at least `interviews.min_interviews` (10) good interviews *and* saturation. Report it as k⁺ʳ, for example 8⁺².
8. **Decision.** The card's metric is the share of coded ICP interviews that show a target code. Pre-register the codes that count in `criteria.problem_codes`, with `success_threshold` and `kill_threshold` as shares of interviews, `xyz.x` equal to `success_threshold`, and `min_n` ≥ 10. Coders apply a problem code only when the interviewee describes a specific past occurrence (S2 or stronger), never for opinions. Then `gapval.py stats RUN --experiment EXP-NN` counts the interviews where coder A applied any problem code and judges the share with the Wilson rule; it reports the saturation point and agreement alongside.

**Output:**
- `validation/assets/EXP-NN/interview-guide.md`
- transcripts in `validation/data/EXP-NN/interviews/`, ingested as `interviews.jsonl`
- `validation/data/EXP-NN/codes-A.jsonl`, `reliability-sample.jsonl` and `codes-B.jsonl`
- `validation/agreement.json`, `validation/themes.json`, `validation/results/EXP-NN.json`

**Metrics and checks**
- α per code, κ reported alongside, and Landis–Koch bands.
- The saturation point k⁺ʳ.
- Share of interviews showing the target codes, with a Wilson interval. Ten interviews give a wide interval; that is honest, not a flaw.

**Pitfalls**
- **Pitching.** Once you describe your solution, every later answer is contaminated. Save solution interviews for after the problem is confirmed.
- **Leading questions.** "Isn't it annoying when…?" manufactures agreement.
- **Counting enthusiasm.** "That sounds amazing!" is S0. "I paid a freelancer €300 last month to do this" is S4.
- **A coder B who has seen A's codes.** That measures copying, not reliability.
- **Identifiable transcripts.** Store pseudonymous ids only. Retention follows `privacy.retention_days`.

**Done when:**
- at least 10 good interviews are coded
- saturation is reached, or its absence is documented
- agreement is accepted or provisional
- `gapval.py stats` has written the result
