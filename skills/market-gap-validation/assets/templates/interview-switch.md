# Switch interview guide — {{JOB}} ({{EXPERIMENT_ID}})

Jobs-to-be-Done switch interview (Moesta & Spiek). Interview people who **recently switched** to or from a solution for {{JOB}}: ideally within the last 3–6 months, while they still remember the details. Goal: reconstruct the timeline of the switch and the four forces behind it. Plan for about 30–40 minutes.

## 0. Consent (read word for word)
"Thanks for helping. I'm studying how people decide to change the way they handle {{JOB}}. I'm not selling anything. It takes about 35 minutes, you can skip any question or stop at any time, and my notes are anonymous."
- Recording, asked separately: "May I record, only for accurate notes? It's deleted afterwards." Record only if they say yes.

## 1. Anchor the switch
- "You started using {{NEW_SOLUTION}} (or stopped using {{OLD_SOLUTION}}). When exactly was that? Where were you?"

## 2. Walk the timeline backwards and forwards
| Stage | Ask | Code |
|---|---|---|
| First thought | "When did you first think 'there must be a better way'? What was happening?" | T-FIRST |
| Passive looking | "Before you actively searched, what did you notice? Ads, colleagues, posts?" | T-PASSIVE |
| Event 1 | "What happened that made you start looking seriously?" | trigger |
| Active looking | "Where did you look? What did you compare? Who did you ask?" | T-ACTIVE |
| Event 2 | "What made you decide *now* rather than later?" | trigger |
| Deciding | "What almost stopped you? What made you sure enough?" | T-DECIDE |
| Consuming | "What happened the first week? What surprised you? What did you pay?" | T-CONSUME |

## 3. Probe the four forces
People switch when push + pull exceed anxiety + habit.
- **Push of the situation (F-PUSH):** "What was going wrong with the old way? What did it cost you?"
- **Pull of the new solution (F-PULL):** "What did you hope the new way would let you do?"
- **Anxiety of the new (F-ANX):** "What worried you about switching? Price, learning curve, data, risk?"
- **Habit of the present (F-HABIT):** "What did you like about the old way, or find hard to give up?"

## 4. Money
- "What did you pay before, and what do you pay now? How did you decide it was worth it?"
- "Who approved the spend?"

## Rules while you talk
- Stay in the past and the specific: dates, places, people, numbers.
- Don't ask "would you…" or describe your own idea.
- Silence is useful: let them fill it.
- Discard compliments and generalisations as evidence.

## Notes template
- Interview id: INT-__ · date · old solution → new solution · months since the switch
- Timeline (stage → what happened, with dates):
- Forces: push / pull / anxiety / habit, each with a verbatim quote:
- Money: before / after / who decided:
- Strongest quote (verbatim):

## Transcript file for `gapval.py ingest --kind interviews`
One plain-text file per interview (`INT-NN.txt`) in `validation/data/{{EXPERIMENT_ID}}/interviews/`. Label turns `I:` and `P:`, and remove names, emails, company names and other identifying details.
