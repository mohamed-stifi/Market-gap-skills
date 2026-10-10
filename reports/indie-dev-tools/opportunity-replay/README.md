# Opportunity replay: indie-dev-tools

This folder shows what the opportunity lenses (method card D26) and traction (D27) find in the data of the first live deep run (`reports/indie-dev-tools/`), **without a new run and without new subagents**. On a copy of that run folder, `gapscan.py traction RUN --offline`, `gapscan.py opportunities scan RUN`, `score`, `rank`, `report` and `viz` were run on 2026-10-10.

Read `opportunities.md` first, then `dashboard/index.html`.

## What it shows
- **Traction for free:** the run's saved marketplace responses gave installs or rating numbers for 127 of 151 marketplace products.
- **51 options from 8 lenses:** gap 2, clone-wedge 10, bundle 6, unbundle 2, port 12, down-market 2, replace 5, hosted-oss 12. The gap lens alone, all the deep run looked for, gives 2.
- **Leads the gap framing could not express:**
  - "Cheaper alternative to Tidio, Zoho SalesIQ" and "More reliable alternative to Tidio, Zoho SalesIQ" (live chat), built from price and reliability complaints in App Store reviews. The ambition math: 100 paying customers at $10/month reach $1,000/month.
  - "Migration target for Lemon Squeezy users" after its acquisition by Stripe (two authors).
  - "Low-cost revenue recovery (paid plans start at 99/month)": the deep run's best near-miss (failed-payment recovery), re-found from price data alone.
  - Proven but poorly rated products, the raw material for clones (chart 15): Tawk.to, Zendesk Support for Jira, Smartsupp, New Relic.

## How to read it (limits of a replay)
- **Evidence tiers come from the deep run's ledger,** linked to options through their rules. There were no scan miners, so 43 of 51 options are "untested". A real scan would test the best 8, then the better half again.
- **No red-flag check ran,** so the "Red flag" column reads "not checked".
- **The "Subagents used: 91" tile** is the deep run's spend, copied with the run folder. The replay itself used none.
- **The protocol was switched to `depth: scan`** on the copy only, so the dashboard shows the scan charts.
- `next-runs/` holds three narrow deep-run protocol drafts (OPP-048, OPP-032, OPP-033). In a real scan you would start one with `gapscan.py init gap-runs/NEW --from-run SCAN_RUN --opportunity OPP-032`.
