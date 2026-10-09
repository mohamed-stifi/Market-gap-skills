# V07 · Smoke test / fake door landing page

| Origin | Phase | Roles | Status |
|---|---|---|---|
| Smoke tests (Ries, *The Lean Startup*); pretotyping and the XYZ hypothesis (Savoia); fake-door testing (product analytics practice); honest-disclosure and consent norms (GDPR, fake-door ethics) | V3 assets, V5 collect | builder (page), human (deploy and traffic), analyst (reading) | conditional: a `smoke-test` or `fake-door` card is frozen |

**Use when:** a frozen card has `type: smoke-test` or `fake-door`.

**Why:** A smoke test measures what people *do* when you show them the promise: do they leave an email to get it? That is stronger evidence than any survey answer. It is also a small deception unless you handle it honestly. Disclose the truth right after the click and ask for consent, and the test is respectful, legal and still informative.

**Inputs:** the frozen card (Y, Z, channels, thresholds, `exposure_limit`); `validation/opportunity.json` (top quotes in the ICP's own words, outcomes, pricing hypothesis, MVP scope); `assets/templates/landing.html` and `privacy.md`.

**Procedure**
1. **Copy (builder).** Fill in `landing.html` and save it as `validation/assets/EXP-NN/landing.html`:
   - `{{HEADLINE}}`: the outcome in the ICP's own words, taken from top quotes.
   - `{{SUBHEAD}}`: who it is for and the job.
   - `{{BENEFITS}}`: three to five benefits, each mapped to a desired outcome.
   - `{{PRICE_TIERS}}`: from the pricing hypothesis or the card's `price_point_month_usd`.
   - `{{EXPERIMENT_ID}}`.
   - Promise only what the MVP scope can deliver.
2. **Honesty elements.** Keep all of them from the template:
   - A disclosure block (`id="disclosure"`) shown right after any call-to-action click. It says the product is not built yet and offers the waitlist.
   - An email field with a required consent checkbox (`id="consent"`).
   - A link to the privacy notice. Use `privacy.html` for `{{PRIVACY_URL}}`; the notice from `privacy.md` ships next to the page.
   - `data-experiment="EXP-NN"` on the page.
   - No payment form. Payment fields are allowed only on `presale` or `deposit` cards, and then only with explicit charge, authorisation and refund wording.
   - No fabricated social proof: no testimonials, "trusted by", "join 1,000", ratings or customer logos.
   - No leftover `{{…}}` placeholders. When the form backend does not exist yet, write the literal `FORM_ACTION_PENDING` for `{{FORM_ACTION}}`; the deploy task tells the human to replace it.
3. **Check.** Run `gapval.py assets check RUN EXP-NN` and fix every finding before deployment is requested.
4. **Launch (human).** Deploying the page, connecting the form backend and analytics, and posting or advertising are outward actions. `gapval.py next` turns each `required_ht` slug into a blocking human task (card V08), in the card's order, so the deploy task comes first. The agent may deploy only after the human approves the task and puts a deploy token in an environment variable.
5. **Tracking.** When the deploy task is closed with the live URL in its note, `gapval.py next` returns `DO V07`: run `gapval.py utm RUN --experiment EXP-NN --base-url URL --channels a,b,c` with exactly the card's channels. Each channel gets its own link, so per-channel rates can be judged separately. Posting tasks come after this, and their drafts use these links.
6. **Run.** Leave the copy unchanged until `min_n` or `duration_days` is reached, whichever the card names. Stop early only if the `exposure_limit` is hit or harm appears; record either as a human task. A "quick headline tweak" mid-test is a new experiment.
7. **Collect.** The human exports visitors per channel (analytics, unique visitors by UTM source) and consented sign-ups per channel (form service), as counts, to the paths in the "export results" task: `validation/data/EXP-NN/visits.csv` (channel, visitors) and `signups.csv` (channel, signups). A fake door exports `clicks.csv` (channel, clicks, visitors). Channel names must match the card's channels. Counts must be non-negative whole numbers, and sign-ups or clicks never exceed visitors in a channel. `gapval.py next` then runs the ingest, for example:
   - `gapval.py ingest RUN --experiment EXP-NN --kind visits --file validation/data/EXP-NN/visits.csv`
   - `gapval.py ingest RUN --experiment EXP-NN --kind signups --file validation/data/EXP-NN/signups.csv`
8. **Judge.** `gapval.py stats RUN --experiment EXP-NN` reports a Wilson interval per channel and pooled, and applies the frozen rule:
   - PASS if the lower bound ≥ `success_threshold`.
   - FAIL if the upper bound < `kill_threshold`.
   - INCONCLUSIVE otherwise, and whenever the pooled n is below `min_n`.
   
   Judge the assumption on the pooled result unless the card names a single channel. Channel differences are hypotheses for the next round, possibly a PIVOT, not post-hoc wins.

**Output:**
- `validation/assets/EXP-NN/landing.html`, `privacy.md`, `posts.md`, `utm.json`
- ingested counts in `validation/data/EXP-NN/`
- `validation/results/EXP-NN.json`

**Metrics and checks**
- Wilson 95% interval: for 20 sign-ups from 100 visitors, it is 13.3–28.9%. That is a PASS against X = 10%, INCONCLUSIVE against X = 15%, and a FAIL against a kill threshold of 30%.
- Consented emails are the numerator. Clicks alone are click-level evidence and cannot validate desirability, which needs at least email level (`verdict.desirability_min_level`).

**Pitfalls**
- **Non-ICP traffic.** Friends, a generic startup forum or bought clicks measure curiosity, not the ICP's need.
- **Counting clicks as sign-ups.** Report clicks, but do not judge on them.
- **Several calls to action.** Two different promises on one page make the metric ambiguous.
- **Bots and duplicates.** Have the human filter obvious bot traffic in the analytics export. Note the filter in the ingest file.
- **Hiding the disclosure.** A fake door that never tells the truth erodes trust in you and in the result.

**Done when:** the page has run to `min_n` or `duration_days`, both exports are ingested, and `gapval.py stats` has written the result.
