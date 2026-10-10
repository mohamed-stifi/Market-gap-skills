# D26 · Opportunity lenses

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Opportunity recognition as pattern recognition (Baron 2006); innovative imitation (Levitt 1966; Shenkar 2010, *Copycats*); new combinations (Schumpeter 1934); bundling and unbundling (Bakos & Brynjolfsson 1999); low-end disruption (Christensen & Raynor 2003); Drucker's sources of innovation (1985: the unexpected, incongruities, industry and market change); app-store mining (Harman et al. 2012; Martin et al. 2017) | P5 (deep), after the map (scan) | orchestrator (runs), synthesizer, miner, red-team | core |

**Use when:** `next` issues `RUN gapscan.py opportunities scan RUN`: in scan runs right after the landscape map, and again after each evidence round; in deep runs after `variants`. Synthesizers, miners and red-teamers read this card whenever their assignment names a lens.

**Why:** A gap (a need nobody serves) is the hardest opportunity to prove: the evidence must show demand and the absence of supply at once, and a red team kills it the moment one product turns up. Most small software businesses start from something easier to evidence. A product people already install and pay for, with a fix they keep asking for. Two tools people glue together. A proven model moved to a platform that lacks it. Paul Graham's test applies: "A crowded market is actually a good sign, because it means both that there's demand and that none of the existing solutions are good enough" (How to Get Startup Ideas, 2012). Each lens is a deterministic rule over data the run already holds, so generating many options costs no subagent; the funnel (D28) then spends evidence only on the best.

**Inputs:** `protocol.json` (`lenses`, `variation_dimensions`, `founder_fit`, `ambition`), `landscape/entity-attributes.jsonl`, `landscape/traction.jsonl` (D27), `analysis/supply.jsonl` and `analysis/gapmap.json` when they exist, the verified ledger, codes and `evidence/why-now.jsonl`.

**The nine lenses**

| Lens | Rule that generates it (script) | Evidence that confirms it | Red-team question | Kill when |
|---|---|---|---|---|
| `gap` | gap-map cell absolute or synthesis (D16) | D20 thresholds | Does anything already do this? | A product fully serves the job for the segment |
| `clone-wedge` | Proven product (top traction third of its store) that is poorly rated (bottom third) or draws complaints; the wedge is the most-named complaint (price, simplicity, reliability, support, language, integration, limits, privacy) | Complaints that name the wedge from 2+ domains; switch or WTP records | Would users switch for this wedge? Can the incumbent copy it fast? | A product already sells this wedge to this segment |
| `bundle` | Two categories linked by integrations or co-mentions, with at most one product doing both jobs | Users who run both tools and complain about switching, syncing or paying twice | Do they want one tool, or best-of-breed? Which incumbent is one feature away? | A product already does both well |
| `unbundle` | A proven suite (3+ jobs) whose single job has 2 or fewer focused products; or 2+ authors who use one part of a product | Users who use one part and resent price or complexity | Is the part separable, or valued because it is bundled? | A focused product already does the part well |
| `port` | A category with 3+ products on a platform, language or segment and at most 1 on another named in `variation_dimensions` | Requests from the target users; the leader has no version there | Why hasn't the leader ported? Is the target big enough? | The target already has a good product |
| `down-market` | A category whose cheapest paid plan costs more than most entry prices in other categories, with few free tiers | Price complaints from small buyers; people who never started paying | Will the low end pay anything? Can the incumbent add a cheap tier? | A cheap, good-enough tier exists |
| `replace` | A why-now record or 2+ authors about a shutdown, acquisition, price rise or platform withdrawal | Users leaving, and where they go | Who already captured the migrants? | Migrants have settled on an alternative |
| `hosted-oss` | Open-source or self-hosted server product (not a plugin or marketplace app) whose license is not blocked | Requests for a hosted version; self-hosting pain; the license text | Do the maintainers sell hosting? Does the license or trademark allow it? | The license forbids hosting as a service (SSPL, Elastic License 2.0, BSL production limits, Commons Clause), or the official cloud already serves this segment |
| `productize` | 2+ authors who pay a freelancer, agency or assistant for the job | What the person does, how often, for how much | Is the service bought for human judgment software cannot give? | Software already does the job and people still prefer people |

**Procedure**
1. **Orchestrator:** run `gapscan.py opportunities scan RUN`. It applies every lens in `protocol.lenses` (default all), keeps at most `opportunity.max_per_lens` options per lens and `opportunity.max_candidates` in all, and writes `opportunities/candidates.jsonl` with stable ids `OPP-NNN`. Each option carries:
   - `prior` (0-1): the mean of its lens's structural signals, with unknown parts counted as 0.5. It never includes evidence.
   - `why`, `needs` (the evidence that would confirm it), `base_entities` (the proven products it builds on), `twist` (what changes), linked `evidence_ids`, `flags` and `ambition` (paying customers needed at the incumbents' median entry price to reach the protocol's ambition).
   - Flags: `regulated-risk`, `platform-dependency`, `license-check`, `license-duty` (AGPL: modified versions must offer source to network users) and `excluded: ...` (matches `founder_fit.exclusions` or `scope.out`).
2. Options persist once generated: if a rule stops firing, the option stays with the flag `rule no longer fires`, because evidence may already cite its id.
3. **Synthesizer (deep runs):** write cards for any lens in `protocol.lenses`, not only gaps. For a lens other than gap, set `lens`, `opportunity_id`, `base_entities` and `wedge`. `cards check` then counts proven base products (D27) as the demand leg of triangulation; pain and supply still need verified records.
4. **Red team:** apply the lens's question and kill rule from the table. For lenses other than gap, incumbents are the premise, not a kill.
5. **Clones are legal only as reimplementations.** Copy the job and the idea, never code, text, brand, trade dress or screenshots. Note it in the card's assumptions.

**Output:** `opportunities/candidates.jsonl` (`opportunity.schema.json`), `opportunities/ids.json`, `opportunities/scan.json` (inputs used, options per lens, lenses that could not fire and why); lens fields on gap cards.

**Metrics and checks**
- Options per lens and evidence tier go into PRISMA (D25) and dashboard chart 13.
- Scoring (D23): for lenses other than gap, competition tops out at 2 (they enter markets with incumbents by design), and 2+ proven products with paid plans count as willingness to pay (market spend).
- Certainty (D22): the same market spend can upgrade demand certainty one step, never above Moderate.

**Pitfalls**
- **Clone without a wedge.** "Same as X but mine" is not an opportunity. The wedge must come from complaints, not taste.
- **Proven means measured.** Products without marketplace numbers are never ranked as proven; unknown traction counts as neutral, not strong.
- **Language ports from thin data.** Most mapped products list one UI language, so "no German product" is weak evidence unless the category's language data shows variety (the rule then counts absence as unknown).
- **Plugins are not self-hostable servers.** A WordPress plugin or Jira app runs inside its host; hosting it for others is not an option.
- **Regulated categories.** Tax, payments as merchant of record, health, legal or financial advice: the flag routes them to the gates (D23), which usually exclude them for a solo founder.

**Done when:** `opportunities/candidates.jsonl` lists the options from every lens in the protocol, and `scan.json` explains each lens that generated nothing.
