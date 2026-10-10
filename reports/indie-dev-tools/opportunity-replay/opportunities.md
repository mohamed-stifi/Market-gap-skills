# Opportunity scan: indie-dev-tools-replay

**Question.** Which jobs of indie developers, solo founders and micro-SaaS teams (1-5 people) are under-served by current developer and founder software and workarounds, and which could a small SaaS, built mostly by an AI coding agent and run with about 5 human hours a week and a budget under $300, serve profitably (>= $1,000 MRR) with growth built into the product?

51 options generated from 335 products; 8 tested with evidence; 1 promising; 0 excluded (protocol, red flags or gates).

## Top options

| # | Option | Kind | Evidence | Red flag | Customers for target |
|---|---|---|---|---|---|
| 1 | Unmet: Faster outage detection (OPP-048) | Unmet need (gap) | promising: 4 records, 3 authors, 3 domains | not checked | - |
| 2 | Cheaper alternative to Tidio, Zoho SalesIQ - Live Chat App (Live chat and help desk) (OPP-032) | Proven product + one improvement | thin: 4 records, 4 authors, 1 domains | not checked | 100 at $10/mo |
| 3 | More reliable alternative to Tidio, Zoho SalesIQ - Live Chat App (Live chat and help desk) (OPP-033) | Proven product + one improvement | thin: 3 records, 3 authors, 1 domains | not checked | 100 at $10/mo |
| 4 | Migration target for Lemon Squeezy users (OPP-012) | Replacement after a shutdown, price rise or platform change | thin: 2 records, 2 authors, 1 domains | not checked | 71 at $14/mo |
| 5 | Migration target for TaxJar users (OPP-013) | Replacement after a shutdown, price rise or platform change | thin: 2 records, 2 authors, 2 domains | not checked | 26 at $39/mo |
| 6 | More reliable alternative to License Manager for WooCommerce, Serial Numbers - Ultimate License Manager (License managem (OPP-036) | Proven product + one improvement | thin: 2 records, 2 authors, 1 domains | not checked | 122 at $8/mo |
| 7 | Just the block payment fraud part of Lemon Squeezy, done simply (OPP-042) | One part of a suite, done simply | thin: 2 records, 2 authors, 1 domains | not checked | 71 at $14/mo |
| 8 | Unmet: Collect product feedback (OPP-050) | Unmet need (gap) | thin: 2 records, 2 authors, 1 domains | not checked | 1011 at $1/mo |
| 9 | Better-rated alternative to Easy Digital Downloads, SureCart (Digital storefront) (OPP-001) | Proven product + one improvement | untested: 0 records, 0 authors, 0 domains | not checked | 61 at $17/mo |
| 10 | Better-rated alternative to SlimStat Analytics, WP Statistics (Web analytics) (OPP-002) | Proven product + one improvement | untested: 0 records, 0 authors, 0 domains | not checked | 143 at $7/mo |

### 1. Unmet: Faster outage detection (OPP-048)

- **Kind:** Unmet need (gap).
- **Why it showed up:** gap-map cell synthesis: 3 demand authors, supply 37.
- **Proven products it builds on:** Uptime.com Website Monitoring, Datadog, Grafana.
- > "An uptime check is only as honest as the endpoint it hits, and a cached 200 is the most common lie." (EV-000175, pain S1)
- > "Pay for monitoring when the cost of a missed outage exceeds the subscription, and for most small products that line is crossed the first time a customer reports the outage before your monitor does." (EV-000177, wtp S0)
- > "are short outages that may not be noticed because they occour between the checks" (EV-000182, pain S1)
- **Still needed:** a red-team search for existing solutions.
- **Deep run:** `gapscan.py init gap-runs/opp-048-unmet-faster-outage-detection --from-run gap-runs/indie-dev-tools-replay --opportunity OPP-048` (protocol draft: `output/next-runs/OPP-048.protocol.json`).

### 2. Cheaper alternative to Tidio, Zoho SalesIQ - Live Chat App (Live chat and help desk) (OPP-032)

- **Kind:** Proven product + one improvement.
- **Why it showed up:** 8 proven product(s) in the top traction third of their store; 4 author(s) complain about price.
- **Proven products it builds on:** Tidio, Zoho SalesIQ - Live Chat App, Crisp.
- **Ambition math:** 100 paying customers at $10/month reach $1,000/month.
- > "We had Intercom, and it was expensive and complicated. Crisp works great for our small business. It’s affordable and much more user friendly." (EV-000026, switch S4)
- > "all features of the app is restricted to paid version only which makes the non paid version useless and the cost of service (premium) is on the high side." (EV-000038, pain S1)
- > "I will definitely support them with future clients and projects that take advantage of their upgraded tier. The upgrade pricing is very competitive and affordable." (EV-000047, wtp S0)
- **Still needed:** complaints that name the wedge, from at least 2 domains; switch or willingness-to-pay records; a check that no product already sells this wedge.
- **Deep run:** `gapscan.py init gap-runs/opp-032-cheaper-alternative-to-tidio-z --from-run gap-runs/indie-dev-tools-replay --opportunity OPP-032` (protocol draft: `output/next-runs/OPP-032.protocol.json`).

### 3. More reliable alternative to Tidio, Zoho SalesIQ - Live Chat App (Live chat and help desk) (OPP-033)

- **Kind:** Proven product + one improvement.
- **Why it showed up:** 8 proven product(s) in the top traction third of their store; 3 author(s) complain about reliability.
- **Proven products it builds on:** Tidio, Zoho SalesIQ - Live Chat App, Crisp.
- **Ambition math:** 100 paying customers at $10/month reach $1,000/month.
- > "When on the app many times chats get mixed up. I respond to one chat it goes to another." (EV-000028, pain S1)
- > "It’s been two years and you till haven’t resolved your mobile app notification issue" (EV-000032, pain S2)
- > "We contacted the developer and it has been over 2 weeks now stuck with an app that doesn’t work and they refused to help no matter how many times we asked." (EV-000042, pain S2)
- **Still needed:** complaints that name the wedge, from at least 2 domains; switch or willingness-to-pay records; a check that no product already sells this wedge.
- **Deep run:** `gapscan.py init gap-runs/opp-033-more-reliable-alternative-to-t --from-run gap-runs/indie-dev-tools-replay --opportunity OPP-033` (protocol draft: `output/next-runs/OPP-033.protocol.json`).

### 4. Migration target for Lemon Squeezy users (OPP-012)

- **Kind:** Replacement after a shutdown, price rise or platform change.
- **Why it showed up:** 2 author(s) mention Lemon Squeezy shutting down, being acquired or raising prices.
- **Proven products it builds on:** Lemon Squeezy.
- **Ambition math:** 71 paying customers at $14/month reach $1,000/month.
- > "Lemon Squeezy - it was very popular until being acquired by stripe. Full of serious bugs, bad support." (EV-000111, pain S1)
- > "Lemon Squeezy is owned by Stripe and development is discontinued" (EV-000129, pain S1)
- **Still needed:** how many users are leaving; which alternatives they already chose.

### 5. Migration target for TaxJar users (OPP-013)

- **Kind:** Replacement after a shutdown, price rise or platform change.
- **Why it showed up:** 2 author(s) mention TaxJar shutting down, being acquired or raising prices.
- **Proven products it builds on:** TaxJar.
- **Ambition math:** 26 paying customers at $39/month reach $1,000/month.
- > "TaxJar, acquired by Stripe, they ended up doubling the price" (EV-000130, pain S1)
- > "It’s literally printing novels of PHP Deprecated warnings in my debug log. Considering switching because of it." (EV-000228, switch S1)
- **Flags:** regulated-risk.
- **Still needed:** how many users are leaving; which alternatives they already chose.

## Limitations

- A scan is a breadth sample: one landscape round, single screening, no codebook and no double coding. Treat each opportunity as a lead to test, not a finding.
- Landscape search stopped before saturation (STOP_UNSATURATED): product counts are lower bounds.
- Traction numbers exist for 151 of 335 products (marketplace listings only); products without them are never ranked as proven.
- 211 coverage gaps logged (blocked or empty sources); see coverage-gaps.jsonl.
