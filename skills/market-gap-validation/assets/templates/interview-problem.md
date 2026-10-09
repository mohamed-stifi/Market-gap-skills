# Problem interview guide — {{JOB}} ({{EXPERIMENT_ID}})

Mom Test problem interview (Fitzpatrick; Maurya's problem interview). Goal: learn whether **{{SEGMENT}}** really has the problem behind **{{JOB}}**, how often, what they do about it today, and what it costs them. You are not selling, and you do not describe your idea. Plan for about 25–30 minutes.

## 0. Consent (read word for word)
"Thanks for your time. I'm researching how people like you handle {{JOB}}. I'm not selling anything in this conversation. It takes about 25 minutes, you can skip any question or stop at any time, and I'll keep anonymous notes with no names or company details. Is that okay?"
- Recording, asked separately: "May I record the call, only to write accurate notes? The recording is deleted after the notes are made." Record only if they say yes.

## 1. Context (3 min)
- "Tell me about your work. What does a normal week look like?"
- "Where does {{JOB}} fit into that?"

## 2. The last time (10 min). This is the core.
- "Talk me through the last time you had to {{JOB}}. When was it?"
- "What happened first? Then what?"
- "What was the hardest part? Why was that hard?"
- "What did you do about it?"
- "How long did it take? What did it cost, in time, money or mistakes?"

## 3. Workarounds and spending (7 min)
- "What else have you tried?" (tools, spreadsheets, templates, freelancers, scripts)
- "What do you pay for today to deal with this, if anything?"
- "Why did you stop using what you tried before?"
- "Who else is involved when this goes wrong?"

## 4. Priority (3 min)
- "Where does this rank among the problems you deal with each month?"
- "If it disappeared tomorrow, what would change for you?"

## 5. Wrap-up (2 min): ask for a commitment or an advancement
- "Is there anyone else who deals with this whom I should talk to?" (an introduction)
- "Can I follow up in a few weeks when I've learned more?" (time)
- "Would you like to hear if something comes out of this?" Only add them to a list with their explicit consent.

## Rules while you talk
- **Ask:** specifics in the past ("the last time…", "what did you do…").
- **Don't ask:**
  - "Would you buy…?", "How much would you pay?"
  - "Do you think this is a good idea?", "Would you use…?"
- **Discard as evidence:** compliments, fluff ("always", "usually", "would", "might"), hypotheticals.
- **Feature request?** Ask "Why do you want that? What would it let you do?"
- Talk less than a third of the time.

## Notes template (fill in during or right after the call)
- Interview id: INT-__ · date · segment fit: yes / partial / no
- Last-time story (facts, in order):
- Workarounds and tools (named), with time and money spent:
- Strongest quote (verbatim):
- Commitment or advancement obtained:
- Surprises:

## Transcript file for `gapval.py ingest --kind interviews`
- One plain-text file per interview, named `INT-01.txt`, `INT-02.txt`, … in `validation/data/{{EXPERIMENT_ID}}/interviews/`.
- Label each turn `I:` (interviewer) or `P:` (participant).
- Remove names, emails, company names and anything that identifies the person before saving.
