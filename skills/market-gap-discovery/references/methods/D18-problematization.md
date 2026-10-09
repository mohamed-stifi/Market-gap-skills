# D18 · Problematization, ERRC and Six Paths

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Problematization methodology (Alvesson & Sandberg 2011); ERRC grid, Six Paths framework and noncustomer tiers (Kim & Mauborgne, Blue Ocean Strategy) | P5 Gaps | synthesizer | core |

**Use when:** you are working the synthesis assignment, alongside D17, and especially when strategy-canvas value curves look alike or gap spotting has found only incremental leads.

**Why:** Gap spotting fills holes inside the incumbents' frame; problematization questions the frame itself. Alvesson and Sandberg found that most published research questions are gap-spotting. Challenging the assumptions a field shares produces more interesting and more influential work. In markets, the same move creates a new value curve (Blue Ocean) instead of a slightly cheaper copy. It is still evidence-based: an assumption is challenged only when coded evidence contradicts it.

**Inputs**
- Everything D17 uses, especially `analysis/strategy_canvas.csv`, `analysis/price_ladder.csv` and `landscape/classification.json` (competing factors).
- Coded evidence (`coding/codes-A.jsonl`, `evidence/ledger.jsonl`) and `evidence/why-now.jsonl`.

**Procedure**
1. **Identify the domain:** the category and its competing factors, from classification.json and the strategy canvas.
2. **Articulate the assumptions incumbents share.** Write each as a falsifiable sentence, and look first at pricing model, target user, delivery mode and workflow. Use Alvesson and Sandberg's types:
   - in-house: conventions of this product category ("invoicing tools are sold per seat")
   - root metaphor: how the category pictures the user or job ("the user is an accountant")
   - paradigm: how the job is done ("data entry happens inside the tool")
   - ideology: what is assumed valuable ("more features means more value")
   - field: assumptions shared with adjacent categories ("small businesses buy self-serve")
3. **Evaluate each assumption against coded evidence.** Look for records that contradict it: X-PRICE against seat pricing, X-COMPLEX against feature bloat, workarounds that reveal a different workflow, a segment code the category ignores. An assumption with no contradicting evidence stays.
4. **Develop alternative assumptions** for the contradicted ones, and fill the ERRC grid for the resulting offer. Base each entry on strategy-canvas levels and cite EV ids:
   - eliminate: factors the industry takes for granted that users don't value
   - reduce: factors over-served relative to the evidence
   - raise: factors under-served
   - create: factors no incumbent offers
5. **Consider the audience:** which segment holds the alternative assumption? Is it noncustomer tier 1 (about to leave), tier 2 (refused the category) or tier 3 (never considered it)?
6. **Evaluate the alternative:** is there demand evidence from that segment, and does a known business model support it? If not, record it as an assumption to test, not as a fact.
7. **Run the Six Paths as extra lenses.** Each is a question asked of the evidence:
   - alternative industries: what do people use instead, from other categories?
   - strategic groups: what makes people trade up or down between tiers?
   - buyer chain: users vs. payers vs. influencers — whose pains are ignored?
   - complementary offerings: what happens before, during and after the job? The job map (D13) helps here.
   - functional–emotional appeal: would the opposite appeal win a segment?
   - time: which trend in the why-now log will change how the job is done?
8. Write each alternative that has verified support as a gap card (D20), with:
   - `sa_mode: problematization`
   - the grid in `errc` (`eliminate`, `reduce`, `raise`, `create` arrays)
   - `origin_methods` including D18
   - assumptions typed desirability, viability or feasibility

**Output:** gap cards in `gaps/cards.jsonl` with `errc` filled in.

**Metrics and checks**
- Every challenged assumption and every ERRC entry cites at least one verified EV id or strategy-canvas factor.
- `gapscan.py cards check RUN` applies the D20 thresholds.

**Pitfalls**
- **Contrarianism without evidence.** "Everyone uses subscriptions, so sell one-time licences" is a guess unless records show subscription fatigue in the target segment.
- **Eliminating table stakes.** A factor every incumbent offers may be a must-have. Check pain records about its absence before eliminating it.
- **Treating a reframing as validated.** Problematized cards usually have weaker desirability evidence at the start. List that as the riskiest assumption so validation tests it first.

**Done when:** the assumptions, the ERRC grid and the Six Paths questions have been worked through, and each alternative with verified support is written as a card.
