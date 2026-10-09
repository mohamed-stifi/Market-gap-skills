# Ethics of validation experiments

Validation asks real people for attention, data and sometimes money before a product exists. These rules keep that honest, legal and respectful. They also keep the evidence clean: deceived visitors and spammed communities produce numbers that mean nothing. `gapval.py assets check` and `gapval.py prereg check` enforce the mechanical parts. The rest is your judgment, and when in doubt, raise a blocking `judgment` human task.

## 1. Honest fake doors
- **Show the truth right after the click.** When a visitor clicks a call to action or chooses a plan, show the disclosure block (`id="disclosure"`) right away: the product is not built yet, and here is the waitlist. Never let someone believe they bought, booked or signed up for something that exists.
- **Offer something real in return:** a waitlist, early access, or a reply from the human. Never a dead end.
- **Limit exposure.** Every card has an `exposure_limit` (visitors, days or spend). Stop when it is reached, even if the result is not "clean".
- **No fabricated social proof:** no testimonials, customer logos, user counts, ratings or press mentions you do not actually have. They deceive visitors and contaminate the metric.
- **No deceptive pricing.** Shown prices are the prices you intend to charge. No fake discounts, countdown timers or "only 3 spots left".

## 2. Money
- **Never charge without explicit consent.** A `presale` or deposit card needs:
  - clear text stating that the product does not exist yet, what is being paid for and when it ships
  - a refund promise and how to claim it
  - a payment link the human creates and controls
- **No payment forms on smoke tests or fake doors.** `gapval.py assets check` rejects payment fields unless the card's `evidence_level` is `presale` or `deposit` and the page has explicit charge, authorisation or refund wording.
- **Refund promptly** if the product is not delivered as described, or the experiment is killed.

## 3. Consent and privacy (GDPR basics)
- **Lawful basis.** Collect emails only with consent: an unticked checkbox (`id="consent"`) whose label says what you will send and how often.
- **Privacy notice.** Link it from every page and survey (`assets/templates/privacy.md`). It names the controller (the human), the purpose, the services used (form backend, analytics), the retention period and how to withdraw consent.
- **Data minimisation.** Ask only for what the test needs: an email for a waitlist, never a phone number or company size "just in case". Surveys use pseudonymous respondent ids.
- **Retention.** Delete raw respondent data after the decision, and no later than `privacy.retention_days` (180 days).
- **Where data lives.** Emails stay in the human's form service (`privacy.store_emails_in_repo` is false). The run folder holds only aggregates and pseudonymous ids. `gapval.py ingest` rejects exports with personal-data columns (email, name, phone, address, ip) or any email address, and transcripts that contain an email address or phone number.
- **Analytics.** Prefer privacy-friendly, cookie-less analytics. If cookies are used, the human adds the consent banner their jurisdiction requires.

## 4. Communities and outreach
- **Disclose affiliation** in every post and message: "I'm building this". The drafts in `assets/templates/post-drafts.md` start with it.
- **Follow each community's rules.** Many forbid self-promotion outside designated threads or require approval from a moderator. The human-task steps cite the rule; if it forbids the post, use the fallback channel.
- **No spam or astroturfing:**
  - no identical posts across many groups
  - no fake accounts
  - no friends or paid posters pretending to be customers
  - no "is there a tool for X?" posts written to be answered by yourself
- **Outreach** goes from the human's own account, to people with a plausible interest, with an easy way to say no. Stop after one follow-up.

## 5. Interviews
- **Informed consent** at the start: purpose, duration, what notes are kept, that they can stop anytime, and that nothing is being sold in this conversation.
- **Recording** only with explicit consent, asked separately from the interview consent.
- **Pseudonymise transcripts** (`INT-01.txt`) and strip names, emails, phone numbers and company names before they enter the run folder.
- **No pitching under the cover of research.** If you later want to sell, ask permission for a separate follow-up.

## 6. Stopping for harm
Stop an experiment early, through a blocking `judgment` human task, when any of these happen:
- visitors are confused about whether they paid, or complain about being misled
- a moderator or platform warns about the posts
- personal data was collected or stored outside these rules
- spending exceeds `budget_usd`
- vulnerable groups are reached unintentionally

To close a stopped experiment, the human declines its open export task with the reason (`gapval.py hq decline RUN HT-NNN --note "..."`). The verdict lists it as NOT_RUN, and the report says why. If its data should still be judged, the human exports what exists instead; below `min_n` the result is INCONCLUSIVE.
