# D19 · Change-one-dimension variation

| Origin | Phase | Roles | Status |
|---|---|---|---|
| The research method of replicating a study with one dimension changed (population, setting, method); morphological analysis (Zwicky); application spotting (Sandberg & Alvesson 2011) and geographic arbitrage | P5 Gaps | orchestrator (runs), synthesizer (judges) | core |

**Use when:** `next` issues `RUN gapscan.py variants RUN` at the start of P5, and later when you work the synthesis assignment.

**Why:** Replicating a strong study in a new population or setting is a classic doctoral gap. The market version is a proven product moved to a new segment, language, platform, price tier, delivery mode or integration, or rebuilt AI-native. A morphological box enumerates those variants systematically instead of relying on inspiration. The evidence threshold keeps the enumeration honest: a variant becomes a gap only when the run's own verified evidence shows demand for it.

**Inputs**
- `protocol.json` → `variation_dimensions`: segment, language, platform, price_tier, delivery, integration, ai_native.
- `landscape/entity-attributes.jsonl` (including `signals`: installs, ratings_count, rating_avg, stars), `analysis/supply.jsonl`, `analysis/competitor_matrix.csv`.
- Coded, verified evidence and the why-now log.

**Procedure**
1. **Orchestrator:** run `gapscan.py variants RUN`. It:
   - picks the `variation.top_products` (10) strongest proven products, by adoption signals and verified praise
   - varies one dimension at a time, using the values listed in `protocol.variation_dimensions`
   - drops combinations an included entity already covers
   - writes at most `variation.max_candidates` (200) variants, with ids `VAR-NNN`, to `gaps/variants.jsonl` in a seeded, reproducible order
2. **Synthesizer:** for each variant, search the verified ledger and the coded evidence for demand in the varied setting:
   - records whose segment, language, platform or price complaint matches the new value (S- codes, X-LANG, X-PRICE, X-INTEG, the `platform` field)
   - workarounds people use in that setting
   - why-now entries that unlock it (for `ai_native`)
3. If a variant has verified supporting evidence, write it as a gap card (D20) with:
   - `variant_of: VAR-NNN`
   - `sa_mode: application`
   - the original product in `incumbents`
   - the varied dimension reflected in `gap_type` (segment, language, access, price, integration or feature)
   
   `cards check` then decides whether it meets the thresholds.
4. If a variant has no verified supporting record, do not write a card. `cards check` lists every variant id without a card as discarded for lack of evidence, so the whole enumeration stays auditable.
5. Change exactly one dimension per variant. With two simultaneous changes you can't tell which one the evidence supports. If the evidence points to a combination, write two cards and link them in their statements.

**Output**
- `gaps/variants.jsonl`, written by the script.
- Variant-based cards in `gaps/cards.jsonl`, written by the synthesizer.

**Metrics and checks**
- The PRISMA flow (D25) reports how many variants became cards and how many of those passed `cards check`.
- A high pass rate with thin evidence per card is a warning sign of overreach. Check that each card's evidence really concerns the varied setting.

**Pitfalls**
- **Generating gaps from the box alone.** The box proposes; evidence decides. A plausible variant without verified evidence is discarded, not "promising".
- **Language and geography variants without local evidence.** "No French version exists" is supply evidence only. You also need French-speaking users asking for it: X-LANG records or local workarounds.
- **Ignoring why a variant is absent.** Local regulation, payment rails or platform rules may explain it. Record the reason in the card's `why_empty` so the red team (D21) can test it.

**Done when:** `variants` has run, and every variant is either a card or listed as discarded by `cards check`.
