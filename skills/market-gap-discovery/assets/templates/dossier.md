# {{title}}: market-gap dossier

Run `{{run_id}}` · protocol sha256 `{{protocol_sha256_first12}}` · generated {{generated_at}} · evidence as of {{as_of}}

> **How to read this dossier**
> - Every number is copied from the script output named in [brackets].
> - Every quote is verbatim from a verified snapshot, and its EV id leads to the source.
> - Product counts are lower bounds.
> - Demand evidence from desk research is capped at **weak** until validation.

## 1. Bottom line
- **Top opportunity:** {{GAP-ID}}, {{title}}: {{one-sentence gap statement}}. Score {{score}}, p_top3 {{p_top3}} [gaps/ranking.json].
- **Confidence:** pain {{pain_certainty}}, demand {{demand_certainty}}, demand strength {{weak}} [gaps/certainty.json].
- **Test first:** {{EXP-01 XYZ hypothesis}} (assumption {{A-id}}).
- **Biggest caveat:** {{the most important limitation from section 4}}.

## 2. Ranked opportunities
| Rank | Gap | Type / catalyst | Score | p_top3 | Pain | Demand | Red team | Gates |
|---|---|---|---|---|---|---|---|---|
| {{1}} | {{GAP-ID}}: {{title}} | {{primary}} / {{catalyst}} | {{score}} | {{p_top3}} | {{pain}} | {{demand}} | {{verdict}} | {{pass}} |

Candidates that did not make the ranking: {{n_insufficient}} insufficient, {{n_killed}} killed, {{n_gated}} failed a gate (Appendix B) [gaps/card-check.json, gaps/redteam/, gaps/scores.csv].

## 3. Opportunity {{rank}}: {{title}} ({{GAP-ID}})
<!-- Repeat this section for each ranked opportunity. -->
### 3.1 Gap statement and PICOS
{{statement}}

| Population | Intervention | Comparator | Outcomes | Setting |
|---|---|---|---|---|
| {{population}} | {{intervention}} | {{comparator}} | {{outcomes}} | {{setting}} |

Gap type {{primary}} (+{{secondary}}) · catalyst {{catalyst}} · Robinson reason {{reason}} · spotting mode {{sa_mode}} · gap-map cell {{egm_type}}

### 3.2 Evidence
| EV id | Quote | Stance | Strength | Source | Posted |
|---|---|---|---|---|---|
| {{EV-000000}} | "{{verbatim quote}}" | {{stance}} | {{S0-S4}} | {{domain}} | {{date}} |

Counter-evidence: {{EV ids and one-line summary}} · Demand signals: {{series ids, burst results}} [evidence/bursts.json]

### 3.3 Certainty
Pain {{label}} · Demand {{label}} · demand strength {{weak}}. Downgrades: {{list}}. Upgrades: {{list}} [gaps/certainty.json].

### 3.4 Customer and job (Value Proposition Canvas)
- **ICP:** {{description}} · where they gather: {{channels with URLs}}
- **Job:** {{job}} · job-map steps affected: {{steps}}
- **Outcomes:** {{ODI statements with proxy opportunity rank (ranking only)}}
- **Pains / gains:** {{codes with evidence counts}} · **Pain relievers / gain creators needed:** {{from the card's assumptions}}

### 3.5 Competitors, price ladder and strategy canvas
| Competitor | Pricing | Serves job? | Weakness codes | Snapshot |
|---|---|---|---|---|
| {{entity}} | {{model, min paid/month}} | {{yes/partial/no}} | {{codes}} | {{sha}} |

Value curve versus incumbents on {{factors}} [analysis/strategy_canvas.csv] · ERRC: eliminate {{…}} · reduce {{…}} · raise {{…}} · create {{…}}

### 3.6 Why now and why empty
- **Catalysts:** {{WN ids: factor, change, date, job unlocked}}
- **Why empty:** {{card's why_empty, plus the red team's view}}

### 3.7 Red team
Verdict {{verdict}} · existing solutions {{name: covers}} · failed attempts {{name: lesson}} · Five Forces {{ratings}} · platform risk {{0-3}} · pre-mortem: {{reasons}}

### 3.8 Sizing (bottom-up)
| | Low | Base | High | Source |
|---|---|---|---|---|
| TAM / SAM / SOM ({{currency}}/year) | {{…}} | {{…}} | {{…}} | [gaps/sizing.json] |

Assumptions still to validate: {{conversion, win rate}}.

### 3.9 Score breakdown
| Criterion | Score 0-3 | Weight | Evidence |
|---|---|---|---|
| Pain / Pay / Size / Competition / Why-now / Reach / Right-to-win | {{…}} | {{…}} | {{EV ids}} |

Gates: {{regulatory, ops, buildability, platform, ToS}} · Sensitivity: p_top3 {{…}} [gaps/scores.csv]

### 3.10 Positioning and Lean Canvas
For {{target customer}} who {{need}}, current options such as {{competitors/workarounds}} fail because {{reason}}. Now that {{why-now change}}, {{solution concept}} can {{benefit}} at {{price/access}}.
Problem + existing alternatives {{…}} · segments + early adopters {{…}} · unique value proposition {{…}} · solution {{…}} · channels {{…}} · revenue {{…}} · costs {{…}} · key metrics {{…}} · unfair advantage {{…}}

### 3.11 Assumptions and first experiments
| Assumption | Type | Experiment | XYZ hypothesis | Metric | Human tasks |
|---|---|---|---|---|---|
| {{A1}} | {{desirability}} | {{EXP-01 type}} | At least {{X}}% of {{Y}} will {{Z}} | {{metric}} | {{HT}} |

### 3.12 MVP scope, go-to-market and kill criteria
- **In scope:** {{…}} · **Out of scope:** {{…}} · **Agent-buildable:** {{yes/partial/no}}
- **First channels:** {{…}}
- **Kill criteria:** {{…}}

## 4. Coverage and limitations
- **Landscape:** at least about {{S_obs}} entities (Chao2 {{estimate}}, 95% CI {{lo}}-{{hi}}), completeness {{…}}, coverage Ĉ {{…}}, verdict {{SATURATED / STOP_UNSATURATED}}, probe new-share {{…}}, snowball yield {{…}} [landscape/saturation.json]
- **Themes and coding:** theme Ĉ {{…}}, run test {{…}}, α per code {{range}}, provisional codes {{list}} [coding/themes.json, coding/agreement.json]
- **Independence:** {{full / degraded}}
- **Coverage gaps:** {{sources blocked or unreachable and why}} [coverage-gaps.jsonl, doctor.json]
- **Excluded sources:** {{list}} · **Stale or single-source evidence:** {{flags}}
- **Desk-only cap:** demand strength stays weak until validation.

## 5. PRISMA flow
{{insert output/prisma.md}}

## Appendix A. Evidence index
{{EV id → url, snapshot sha, stance, strength, cited in sections}}

## Appendix B. Discarded candidates
{{GAP-ID or variant → status (insufficient / killed / gated) → reason}}

## Appendix C. Method trail
{{method cards applied, protocol amendments with reasons, human tasks and outcomes}}
