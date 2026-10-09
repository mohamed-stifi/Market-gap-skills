# Indie dev and solo-founder tools: market-gap dossier

Run `indie-dev-tools` · protocol sha256 `1044d8a1ae4b` · generated 2026-10-09 · evidence as of 2026-10-09

> **How to read this dossier**
> - Every number is copied from the script output named in [brackets].
> - Every quote is verbatim from a verified snapshot, and its EV id leads to the source.
> - Product counts are lower bounds.
> - Demand evidence from desk research is capped at **weak** until validation.

## 0. What you asked for, and what desk research can tell you

You asked for a "viral" SaaS that Claude Code can build with a human helper, that earns at least $1,000 a month, with minimal effort and a budget under $300 [protocol.json: founder_fit, ambition.min_arr_usd 12000, notes].

**Desk research cannot predict virality or revenue.** This run can show where people complain, work around, switch or pay, and how crowded the supply is. It cannot show that a product will spread or that anyone will pay *you*. The protocol defines "viral" as a growth loop that is visible in the evidence (output seen by non-users) [protocol.json notes]; every card below lists such a loop only as an untested assumption. Only the validation experiments in section 3.11 (interviews, fake doors, pre-sales) can move demand above **weak**.

**The result is thin.** Of 12 gap cards, 1 survived (GAP-001, marked *weakened* by the red team), 2 were killed by the red team (GAP-003, GAP-004) and 9 had insufficient evidence [output/prisma.json gaps.by_status]. The single survivor has pain certainty **Low**, demand certainty **Very low** and demand strength **weak** [gaps/certainty.json], and its own scoring rationale says reaching $1k MRR against free unlimited tiers is unlikely [gaps/ranking.json right_to_win]. Read it as "the least-bad lead", not as a recommendation to build.

## 1. Bottom line
- **Top opportunity:** GAP-001, Reliable, uncapped visitor chat for solo founders and tiny online businesses: reliable mobile alerts and replying without conversation caps or paid branding removal remain poorly served for 1-5 person online businesses, because incumbents gate volume and branding behind tiers priced for support teams. Score 60.66666666666668, p_top3 1.0 [gaps/ranking.json]. p_top3 is 1.0 only because it is the only ranked gap; it says nothing about absolute quality.
- **Confidence:** pain Low, demand Very low, demand strength weak [gaps/certainty.json].
- **Test first:** At least 4% of 200 landing-page visitors from indie communities will start a paid checkout at 9 USD per month (assumption A2, viability). This is the riskiest assumption: free tiers with unlimited chats exist and the red team judged them the main reason a paid offer fails.
- **Biggest caveat:** the landscape search stopped unsaturated (STOP_UNSATURATED, completeness 0.6087608751279426, coverage 0.6941952678107124) even after the human lowered the saturation targets to 0.50 [landscape/saturation.json; protocol.lock.json amendments 2-3], so the market map is a roughly half-to-two-thirds-complete lower bound, and the GAP-001 category is crowded with free supply.
- **Near-misses worth more evidence (not opportunities):** GAP-005 failed-payment recovery, GAP-002 VAT filing without a merchant of record, GAP-007 subscriptions across several payment providers. Each failed the evidence threshold on source diversity (2 domains, 3 needed); see section 2.1.

## 2. Ranked opportunities
| Rank | Gap | Type / catalyst | Score | p_top3 | Pain | Demand | Red team | Gates |
|---|---|---|---|---|---|---|---|---|
| 1 | GAP-001: Reliable, uncapped visitor chat for solo founders and tiny online businesses | quality (+price) / none | 60.66666666666668 | 1.0 | Low | Very low | weakened | pass (regulatory low, ops medium, buildability partial, platform risk 1, ToS feasible) |

Candidates that did not make the ranking: 9 insufficient, 2 killed, 0 failed a gate (Appendix B) [output/prisma.json, gaps/redteam/, gaps/scores.csv].

### 2.1 Near-misses: leads that need evidence, not opportunities
These cards did **not** pass the evidence threshold and were not scored. They are listed because the evidence they do have is concrete (workarounds, money spent) and the main reason they failed is source diversity, which more searching could fix or refute.

- **GAP-005 · Failed-payment recovery and visibility for small subscription SaaS** (insufficient). Gap map: 11 demand authors, 2 domains, proxy opportunity 11.7, the second highest, no satisfaction data [gaps/cards.jsonl note]. Evidence includes a founder who built a tool after chasing failed payers by hand (EV-000065) and an S4 record on rigid retry rules (EV-000239). Why it is not an opportunity: only 2 domains (ycombinator.com, stackoverflow.com; 3 needed); several Stack Overflow askers use PayPal or Authorize.net and are not clearly solo SaaS founders; 4 records predate 2023; Stripe's built-in retries cover the basic job (EV-000064); supply is broad (19 entities) and recoverable revenue at small accounts is small.
- **GAP-002 · VAT and sales-tax filing for small software sellers who sell without a merchant of record** (insufficient). Gap map: 10 authors, 3 domains, supply 21, proxy opportunity 8.3 [gaps/cards.jsonl note]. Evidence: hand-built quarterly VAT scripts and manual portal entry (EV-000114, EV-000115). The HN "merchant of record" series shows a significant burst (p_value 0.004975124378109453) [evidence/bursts.json], and Stripe Managed Payments (WN-001, WN-007) is the catalyst. Why it is not an opportunity: still 2 qualifying domains for the threshold (ycombinator.com, dev.to); the round-2 WooCommerce TaxJar reviews were not counted (adjacent persona, mostly outside the 730-day window); tax preparation may be treated as regulated or high-liability work; and merchants of record that bundle tax (Stripe now among them) shrink the segment that refuses the bundle.
- **GAP-007 · Running subscriptions across several payment providers** (insufficient). Gap map J-RUN-SUBSCRIPTIONS: 17 authors, supply 30, satisfaction 5.0 [gaps/cards.jsonl note]. Evidence: providers handle failed payments, cancellations and trials differently (EV-000063); unannounced fee increases (EV-000121). Why it is not an opportunity: 2 domains; the core pain (P-PROVIDER-INCONSISTENCY) rests on one record (EV-000063); no record shows a seller actually running several providers; and most sellers use one provider whose subscription engine suffices (EV-000127).

### 2.2 A finding in itself: the crowding pattern
Across the categories this run touched, supply is dense and much of it is new, solo-built and free or cheap. The red team found:
- **Status pages and uptime monitoring:** 39 entities serve outage detection in the gap map, plus at least seven solo-built "status page + uptime for small SaaS" Show HN launches between Oct 2025 and Aug 2026, several of which drew 1-14 points and 0 comments [gaps/redteam/GAP-004.json].
- **Site chat:** 30 serving entities in the gap-map cell, plus 2026 entrants (ChatSpark, GhostChat, Libredesk, Knocket) [gaps/redteam/GAP-001.json].
- **Extension payments:** at least four extension-specific SDKs (ExtensionPay, Addon Pay, crxpay, ExtensionBill) already competing on fee percentage [gaps/redteam/GAP-003.json].
- **Launch directories:** many directories exist and new apps launch daily (EV-000146); the card names Shiplist, Launchy, Appstro and Ranla among them [gaps/cards.jsonl GAP-006].
- **Other cells:** feedback boards 50 entities, subscription billing 30, hosted checkout 30, sales tax 21 [gaps/cards.jsonl].
- **Analytics companions:** the orchestrator also observed many PostHog mobile clients and analytics tools in the landscape. The writer's inputs hold only one verified review of such an app (EV-000021) and no count, so this is reported qualitatively.

The pattern matters for your brief: the kind of product an AI coding agent can build in a weekend is also what many other people are building with the same agents. The red team calls this "commoditised by agent-built clones" and names it as the main threat in every surviving or killed card. A buildable idea is not scarce; distribution and a reason to choose you are.

## 3. Opportunity 1: Reliable, uncapped visitor chat for solo founders and tiny online businesses (GAP-001)

### 3.1 Gap statement and PICOS
Although many chat tools (mobile companions of SMB live-chat suites, free and open-core widgets) let small sellers talk to site visitors, reliable mobile alerts and replying without conversation caps or paid branding removal remain poorly served for solo founders and 1-5 person online businesses, because incumbents gate volume and branding behind tiers priced for support teams. This matters because users report missed or misrouted chats, lockout after caps or cancellation, and switching (EV-000032, EV-000037, EV-000043).

| Population | Intervention | Comparator | Outcomes | Setting |
|---|---|---|---|---|
| Solo founders, indie app and plugin developers and other 1-5 person online businesses that answer their own site visitors (most verified reviewers are general small businesses, not developers) | Conversing with site visitors through an embedded chat widget and a mobile reply app (J-CHAT-WITH-VISITORS) | Crisp, Smartsupp, Chatway, free Tawk.to, Tidio, open-core Chatwoot, Intercom; WhatsApp and email as workarounds (EV-000095) | Fewer missed or misrouted messages; no loss of replying at a plan limit or after cancelling; lower page-speed cost of the widget | Websites, Shopify apps and storefronts run by 1-5 people; global, English; replies mostly from a phone |

Gap type quality (+price) · catalyst none · Robinson reason biased · spotting mode neglect · gap-map cell none · noncustomer tier 1

### 3.2 Evidence
| EV id | Quote | Stance | Strength | Source | Posted |
|---|---|---|---|---|---|
| EV-000032 | "It’s been two years and you till haven’t resolved your mobile app notification issue" | pain | S2 | apple.com | 2022-07-10 |
| EV-000037 | "I’ve been subscribed for some time but after canceling my last subscription I couldn’t text anyone anymore" | pain | S4 | apple.com | 2023-03-05 |
| EV-000043 | "Was using smartsupp paid version and this free version is killing it, I’m going to upgrade" | switch | S4 | apple.com | 2025-04-19 |
| EV-000026 | "We had Intercom, and it was expensive and complicated. Crisp works great for our small business. It’s affordable and much more user friendly." | switch | S4 | apple.com | 2024-06-05 |
| EV-000028 | "When on the app many times chats get mixed up. I respond to one chat it goes to another." | pain | S1 | apple.com | 2026-08-03 |
| EV-000031 | "This requires me to close the crisp website anytime I leave my computer and use my phone." | workaround | S3 | apple.com | 2020-05-09 |
| EV-000056 | "Once you reach your limit, the Chatway widget will remain visible on your website, but you won’t be able to respond to new conversations manually or through APIs." | wtp | S1 | chatway.app (vendor) | 2026-10 |
| EV-000095 | "I usually talk to my clients on whatsapp, but it's super inefficient. They are very vague to describe a problem, and when I ask for screenshots, I get a photo of their screen taken with their phone." | workaround | S3 | ycombinator.com (vendor) | 2026-05-13 |

URLs: EV-000032, EV-000026, EV-000028 https://itunes.apple.com/us/rss/customerreviews/page=1/id=1085770229/sortby=mostrecent/json · EV-000031 https://itunes.apple.com/us/rss/customerreviews/page=2/id=1085770229/sortby=mostrecent/json · EV-000037 https://itunes.apple.com/us/rss/customerreviews/page=1/id=1258723897/sortby=mostrecent/json · EV-000043 https://itunes.apple.com/us/rss/customerreviews/page=2/id=6449775006/sortby=mostrecent/json · EV-000056 https://chatway.app/pricing · EV-000095 https://news.ycombinator.com/item?id=48119687

Note what the evidence does *not* show: EV-000043 and EV-000026 are switches *to* an incumbent that the reviewer is happy with, which is evidence of willingness to pay for chat in general, not for a new product. The S4 "switch" records point at a market that is served.

Counter-evidence: EV-000044 ("Works for any business looking for a channel that connects you to your customers without the price tag."), EV-000045 ("Best live chat assistance app you won't even notice a difference between the paid version and the free version"), EV-000040 (a reviewer pointing to Tawk.to's free service), EV-000051 (a reviewer says Chatway does what they need at a reasonable price), EV-000030 and EV-000033 (praise for Crisp) · Demand signals: none recorded for this card; no burst series [evidence/bursts.json].

### 3.3 Certainty
Pain Low · Demand Very low · demand strength weak [gaps/certainty.json].
Downgrades: risk of bias moderate (share 0.25); inconsistency moderate (share 0.2727272727272727); imprecision moderate (13 authors; prevalence 5 of 11, CI 0.21270957543988045-0.7199122443100118); methodological limitations moderate (provisional code X-COMPLEX); publication bias moderate (low coverage). Indirectness: none. Upgrades: none (no magnitude, no dose-response).

### 3.4 Customer and job (Value Proposition Canvas)
- **ICP:** 1-5 person online businesses that answer their own site visitors from a phone. Most verified reviewers are general small businesses, not developers, so the indie-developer framing of the brief is only partly supported [gaps/cards.jsonl]. Where they gather (from the red-team judgment): Hacker News Show HN (https://news.ycombinator.com/show), the widget's "powered by" badge on customers' sites, the Apple App Store (https://apps.apple.com/); no channel has a recorded size [gaps/judgments.jsonl].
- **Job:** Converse with site visitors and customers (J-CHAT-WITH-VISITORS) · job-map steps affected: monitor (being alerted), execute (replying), conclude (keeping access after a plan change).
- **Outcomes:** Minimize the number of visitor messages missed or sent to the wrong conversation when away from the desk; minimize the likelihood of losing the ability to reply once a plan limit is reached or a plan is cancelled; minimize the page-speed cost of the embedded chat widget. Gap map: 9 demand authors, 4 domains, supply 30, satisfaction proxy 2.0 [gaps/cards.jsonl note].
- **Pains / gains:** P-USAGE-CAP-LOCKOUT, P-BRANDING-PAYWALL, X-RELIAB, X-PRICE, X-SUPPORT, X-COMPLEX · **Pain relievers needed (from the card's assumptions):** reliable mobile notification delivery (A4), no caps or branding paywall at a low flat price (A2).

### 3.5 Competitors, price ladder and strategy canvas
| Competitor | Pricing | Serves job? | Note (red team) | Snapshot |
|---|---|---|---|---|
| Tawk.to | free; branding removal paid add-on | partial | unlimited agents and chats, mobile apps; pricing page blocked | none (blocked) |
| Umnico Live Chat | free | partial | "Unlimited websites, chats and visitors", push apps; vendor claim | f740df4c5e7eade3 |
| Crisp | free / Mini tier | partial | mobile push on low tiers; seat and feature gating | c892a3bb223d9021 |
| Chatwoot | free Hacker plan (500 conversations/month); 19 USD/agent/month | partial | open source self-host removes caps | 19d7826c4fbfac07 |
| ChatSpark (Show HN, 2026-03) | free 50 conversations/month; Pro 12 USD/month | partial | targets solopreneurs exactly | 6f14682c9433e176 |
| Knocket | vendor claim: unlimited seats, no paid gates | partial | positioned for indie developers | 507029f6 |
| GhostChat / Libredesk | free, open source, self-hosted | partial | no caps or branding, needs a server | e04e54cd535c0983 |

Price ladder (min paid tier, USD/month) [gaps/sizing.json sources.arpa_year_usd]: chatim.app 9.0 · revechat.com 14.99 · Smartsupp 17.99 · chatwoot.com 19.0 · easychatdesk.com 21.0 · getfernand.com 29.0 · ThriveDesk 29.0.

Strategy canvas and ERRC: not in the writer's inputs for this card (the card carries no ERRC grid, and `analysis/strategy_canvas.csv` was not assigned). Based on the card's outcomes only: raise mobile-alert reliability; eliminate conversation caps and the branding paywall on the cheapest plan; reduce widget weight. All of these are hypotheses.

### 3.6 Why now and why empty
- **Catalysts:** none. The card has no why-now entries and scores 0 on why-now [gaps/ranking.json].
- **Why empty:** it is not empty. The card says the residual hole is reliability of mobile alerts and cap/branding gating in suites built for multi-agent teams; the red team adds that vendors keep branding on free tiers deliberately because the badge is their own growth loop, and that a solo-sized paid offer is low-ARPA and must beat free tools. Reliability claims could not be tested from desk evidence.

### 3.7 Red team
Verdict **weakened** · existing solutions: 7 partial (table above) · failed attempts: AxonSpear simple chat widget (Show HN 2024-12, 2 points, 2 comments: distribution, not product, is the bottleneck) · Five Forces: rivalry high, new entrants high, substitutes high, buyer power high, supplier power medium · platform risk 1 (APNs/FCM and app-store review for the reply app) · pre-mortem:
1. Free tiers kept solo founders from paying; checkout conversion at 9 USD/month stayed under 1%.
2. Push delivery was no more reliable than incumbents' (APNs/FCM throttling, iOS background limits).
3. Support load from an always-on product exceeded 5 human hours a week.
4. The "powered by" loop brought mostly other free-tier users; MRR stalled far below 1,000 USD (needs about 110 customers at 9 USD).
5. An incumbent or clone removed caps or branding on its cheapest plan, erasing the wedge.

### 3.8 Sizing (bottom-up)
| | Low | Base | High | Source |
|---|---|---|---|---|
| TAM (USD/year) | 2160000 | 22800000 | 66120000 | [gaps/sizing.json] |
| SAM (USD/year) | 216000.0 | 4560000.0 | 19836000.0 | [gaps/sizing.json] |
| SOM (USD/year) | 216.0 | 18240.0 | 238032.0 | [gaps/sizing.json] |

Accounts are **WordPress installs only**: WordPress.org active installs of the crisp (20,000), tawkto-live-chat (100,000) and tidio-live-chat (70,000) plugins. Shopify, Webflow and custom sites are not counted, and installs are sites, not 1-5 person businesses. ARPA comes from the price ladder above. Reachable share, conversion and win rate are assumptions, not data. The SOM range (216.0 to 238032.0 USD/year) is so wide that the base case clearing the 12000 target means little on its own.

Assumptions still to test: conversion (card A2 uses 4% as its pass bar) and win rate against 30 serving entities.

### 3.9 Score breakdown
| Criterion | Score 0-3 | Weight | Rationale [gaps/scores.csv] |
|---|---|---|---|
| Pain | 3 | 0.22 | 13 authors; 4 S3+ workaround/switch authors; 3 S4 authors |
| Pay | 3 | 0.18 | 6 wtp/S4 records from 3 authors; 21 paid incumbents |
| Size | 2 | 0.12 | SOM base 18240.0 vs target 12000 |
| Competition | 1 | 0.14 | red team weakened; cells none |
| Why-now | 0 | 0.1 | 0 catalysts (0 moderate/strong); significant burst: False |
| Reach | 1 | 0.14 | 3 channels (0 sized, 0 marketplace/integration/keyword with evidence) |
| Right-to-win | 1 | 0.1 | no audience, data or reliability edge over free incumbents and 2026 clones; >=1k MRR against free unlimited tiers judged unlikely |

Gates: regulatory low, ops burden medium, agent-buildability partial, platform risk 1, ToS feasible · Sensitivity: p_top3 1.0, median rank 1.0 (only one gap ranked) [gaps/ranking.json]. Note that the Pay score of 3 rests partly on vendor pricing pages (EV-000055/56/57) and switches to incumbents, not on demand for a new tool.

### 3.10 Positioning and Lean Canvas (hypotheses only)
For 1-5 person online businesses who answer site visitors from a phone, current options such as Crisp, Smartsupp, Chatway and Tawk.to can fail because alerts are unreliable and replying is capped or branded on cheap plans. No why-now change was found. A small chat widget with a reliable mobile reply app could remove caps and branding at a low flat price.
Problem + existing alternatives: missed alerts, cap lockout, branding paywall; free Tawk.to, Chatwoot, Chatway, WhatsApp/email · segments + early adopters: solo founders who already run a chat widget and recently hit a cap · unique value proposition: "never miss a visitor, never get capped" (unproven) · solution: widget + inbox + push app (hypothesis) · channels: Show HN, "powered by" badge, App Store listing (all unsized) · revenue: flat monthly plan, ladder 9.0-29.0 USD · costs: hosting, Apple developer account, push infrastructure, human support time · key metrics: notification delivery rate, paid conversion, badge-click sign-ups · unfair advantage: none recorded (only fast agent shipping and building in public).

### 3.11 Assumptions and first experiments
| Assumption | Type | Experiment | XYZ hypothesis | Metric | Human tasks |
|---|---|---|---|---|---|
| A1 | desirability | EXP-01 problem-interviews | At least 30% of 40 solo founders using a site chat tool, recruited in indie communities, will report a missed or misrouted visitor message in the last 30 days. | share reporting a missed/misrouted message | recruit and talk to founders |
| A2 | viability | EXP-02 fake-door | At least 4% of 200 landing-page visitors from indie communities will start a paid checkout at 9 USD per month. | paid-checkout starts / visitors | post in communities; set up checkout account |
| A3 | viability (growth loop) | EXP-03 smoke-test | At least 1% of visitors who click a widget's 'powered by' link will create a free account within 7 days. | sign-ups within 7 days / badge clicks | install the widget on real sites |
| A4 | feasibility | prototype trial (not an experiment type in the handoff schema; listed as an open question) | At least 99% of 1,000 test messages will raise a phone notification within 30 seconds during a 2-week prototype trial. | notifications within 30 s / messages | device testing on real phones |

Run EXP-02 first: it tests the assumption the red team says kills the idea.

### 3.12 MVP scope, go-to-market and kill criteria
- **In scope:** embeddable chat widget; inbox; mobile reply with push notifications; no conversation cap and no branding paywall on the paid plan · **Out of scope:** multi-agent team routing, AI chatbots, helpdesk ticketing, CRM · **Agent-buildable:** partial (widget, inbox and backend are routine; a reliable native push app needs device testing by the human) [gaps/judgments.jsonl].
- **First channels:** Show HN, the widget's "powered by" badge, App Store listing. None has a recorded size, and the red team found that simple-widget Show HN launches draw almost no attention.
- **Kill criteria:** EXP-02 upper confidence bound below 4% paid-checkout starts; EXP-01 upper bound below 30% reporting a missed message; push delivery below 99% within 30 s in the prototype; support load above 5 human hours a week during the trial; an incumbent removes caps or branding on its cheapest plan.

## 4. Coverage and limitations
- **Landscape:** at least about 171 entities counted in the estimator (Chao2 280.8984725965858, 95% CI 236.06379514698216-356.62818617909534), completeness 0.6087608751279426, coverage Ĉ 0.6941952678107124, verdict **STOP_UNSATURATED** (marginal yield 0.221 in round 4, needed <= 0.05), probe not run (null) [landscape/saturation.json]. 395 included and verified entities in total, of which 224 were found only by snowballing and are not in the estimator [output/prisma.json]. All estimates are lower bounds.
- **Saturation targets were lowered by the human.** The protocol originally used the ~90% overlap rule. After the user said "if 90 hard to achieve let say accept 60-70%" the targets went to 0.65 (amendment 2), and after "or just let see 50% for now" to 0.50 (amendment 3), with reliability thresholds and the marginal-yield rule unchanged [protocol.lock.json]. Even at 0.50 the marginal-yield rule was not met, so the run stopped unsaturated. The landscape and themes are roughly half-complete lower bounds.
- **Themes and coding:** theme Ĉ 0.9511112172065599, 54 themes observed (estimate 68.17301038062284, CI 58.3808187389924-99.85312363219218), completeness 0.7921023246370926, Guest–Namey–Chen run test saturated (base 20, run 10, threshold 0.05) [coding/themes.json]. Coding agreement verdict **provisional** on codebook v3 after 2 revisions; provisional codes (α .667-.80): F-PULL, T-CONSUME, X-COMPLEX, X-INTEG; 16 codes not assessable (too few positives); evidence strength α 0.8503600960256068 between coders but 0.593313462240678 against the miners' own strength labels (status revise) [coding/agreement.json]. X-COMPLEX is on GAP-001 and is one reason for its downgrade. 16 singleton codes, several still proposed (NEW:), were not folded into the codebook.
- **Screening reliability:** double screening of 162 units, α 0.9002254965557718 (accept), 10 disagreements [landscape/screening-audit.json].
- **Independence:** the saturation script records scout independence as **full** (mean pairwise Jaccard 0.21031592520954223, correlated scouts false) [landscape/saturation.json]. Separately, the orchestrator reported an independence slip among the evidence miners. Its details are in the run's event log, which was not assigned to the writer, so its effect on the evidence counts cannot be stated here. Treat author and domain counts as possibly less independent than they appear.
- **Coverage gaps** [coverage-gaps.jsonl, doctor.json]:
  - GitHub was unavailable: `gh` was not logged in (and its config was unreadable in the sandbox), and the web query blocks naming GitHub (QB-041, QB-053, QB-057, QB-065, QB-069) were refused by the session's shell guard. GitHub alternatives and open-source tools are under-sampled, and every red-team GitHub search failed.
  - The directories unit R02-B3-directories was not searched: tier-0 web search was denied by the host permission classifier.
  - Wikipedia pageviews were skipped (MGD_CONTACT not set). All tier-2 sources (Reddit, Product Hunt, SaaSHub, X, Google Trends, keyword tools) had no keys, so no search-volume data exists.
  - Page snapshots failed for many URLs: 122 robots.txt disallows, 28 HTTP 403, 15 network errors, 13 incomplete reads, 8 HTTP 429. The Tawk.to pricing page (a key GAP-001 incumbent) was blocked. Apple review feeds were intermittently empty (3 times).
- **Excluded sources:** Reddit, G2 and Capterra (excluded or tier 2), so review-site and Reddit complaints are missing.
- **Evidence concentration:** round 1 evidence came overwhelmingly from Hacker News and App Store reviews. GAP-001 rests almost entirely on App Store reviews of chat apps plus vendor pricing pages. The targeted round 2 (amendment 4, chosen by the human after the first card check found 1 pass and 11 insufficient) added wordpress.org, Stack Overflow, dev.to, Atlassian and Stack Exchange records for the near-miss cards, but it added no new chat evidence.
- **Stale or single-source evidence:** GAP-003 has only 2 of 27 dated records in the 730-day window; GAP-004's Server Fault records date from 2011-2017 and its demand rests on one author's S4 records; GAP-005 has 4 records before 2023; GAP-007's core pain rests on one record (EV-000063). GAP-001 includes 2020-2022 reviews (EV-000031, EV-000032, EV-000034), and the report check flags that most of GAP-001's supporting evidence is older than 12 months [output/report-check.json].
- **Large evidence pools:** 13 pools were over the pool minimum and all 13 were truncated without a stopping test [output/prisma.json].
- **Post-landscape discoveries:** 19 entities first appeared in evidence, after the landscape closed (for example dom:quaderno.io, dom:pingdom.com, dom:mollie.com, dom:senja.io, dom:trustsqueezy.com), so the landscape missed them [output/prisma.json].
- **Sizing:** accounts are WordPress plugin installs only (see 3.8), and conversion, reachable share and win rate are assumptions.
- **Protocol amendments** [protocol.lock.json]: (1) payments/communities clarification: software-seller billing, merchant-of-record, dunning and license tools in scope; general processors that hold funds or need KYC out; communities and directories kept as reach channels, not competitors; (2-3) saturation targets 0.65 then 0.50 by human directive; (4) one targeted evidence round for the near-miss cards; (5) budget raised to 100 subagents after the user approved 20 more (HT-003); (6) coding batch size raised to 100 records so the v3 recode needed 3 coders instead of 5.
- **Desk-only cap:** demand strength stays weak until validation. Nothing in this dossier predicts virality or revenue.

## 5. PRISMA flow

### Landscape

| Stage | Count |
|---|---|
| Records identified (all units) | 1198 |
| Duplicates merged | 398 |
| Unique entities | 789 |
| Screened | 789 |
| Excluded | 261 |
| Unsure (not counted) | 124 |
| Included | 404 |
| Included and verified | 395 |
| Counted in saturation | 171 |

Exclusions by reason: EX-DEAD 40, EX-DUPLICATE 4, EX-NOT-FOUND 12, EX-NOT-SOFTWARE 3, EX-OUT-OF-SCOPE 202

### Evidence

| Stage | Count |
|---|---|
| Records submitted by miners | 298 |
| Rejected at merge | 1 |
| Duplicates | 8 |
| In ledger | 289 |
| Quote verified | 289 |

### Gaps

| Stage | Count |
|---|---|
| Cards proposed | 12 |
| Insufficient evidence | 9 |
| Killed by red team | 2 |
| Gated out | 0 |
| Ranked | 1 |

### Searches (PRISMA-S log)

- apple-reviews (gapscan fetch): 14
- apple-search (gapscan fetch): 38
- atl-reviews (gapscan fetch): 1
- atl-search (gapscan fetch): 77
- directories (agent-web-search): 11
- hn (agent-reported): 2
- hn (gapscan fetch): 175
- hn-counts (gapscan fetch): 2
- se (gapscan fetch): 56
- vendor (agent-reported): 5
- web (agent-web-search): 96
- wp-plugin (gapscan fetch): 3
- wp-reviews (gapscan fetch): 4
- wp-search (gapscan fetch): 47
- yc (gapscan fetch): 53

## 6. Watchlist
Re-check every 90 days (details in `output/watchlist.json`):
- GAP-001 incumbents' cheapest plans (Crisp, Chatwoot, Chatway, Smartsupp, Tawk.to, ChatSpark): any removal of caps or branding kills the wedge.
- Near-miss leads: re-run evidence searches for failed-payment recovery, VAT/OSS filing and multi-provider subscriptions on new domains (Reddit, Indie Hackers, dev.to, GitHub issues) once those sources are available.
- Signal SIG-hn-merchant-of-record and Stripe Managed Payments (WN-001, WN-007) for the payments leads.
- Before any re-run: log in `gh`, set MGD_CONTACT, and search the directories unit that was skipped.

## Appendix A. Evidence index
| EV id | URL | Snapshot | Stance | Strength | Cited in |
|---|---|---|---|---|---|
| EV-000021 | https://itunes.apple.com/us/rss/customerreviews/page=1/id=6477490339/sortby=mostrecent/json | e6e5b27969f4f5c8 | praise | S2 | 2.2 |
| EV-000026 | https://itunes.apple.com/us/rss/customerreviews/page=1/id=1085770229/sortby=mostrecent/json | 3aef31132aa4596f | switch | S4 | 3.2 |
| EV-000028 | https://itunes.apple.com/us/rss/customerreviews/page=1/id=1085770229/sortby=mostrecent/json | 3aef31132aa4596f | pain | S1 | 3.2 |
| EV-000030 | https://itunes.apple.com/us/rss/customerreviews/page=1/id=1085770229/sortby=mostrecent/json | 3aef31132aa4596f | praise | S2 | 3.2 |
| EV-000031 | https://itunes.apple.com/us/rss/customerreviews/page=2/id=1085770229/sortby=mostrecent/json | cceb3a65cd9563a9 | workaround | S3 | 3.2, 4 |
| EV-000032 | https://itunes.apple.com/us/rss/customerreviews/page=1/id=1085770229/sortby=mostrecent/json | 3aef31132aa4596f | pain | S2 | 3.1, 3.2, 4 |
| EV-000033 | https://itunes.apple.com/us/rss/customerreviews/page=1/id=1085770229/sortby=mostrecent/json | 3aef31132aa4596f | praise | S2 | 3.2 |
| EV-000034 | https://itunes.apple.com/us/rss/customerreviews/page=1/id=1085770229/sortby=mostrecent/json | 3aef31132aa4596f | pain | S2 | 4 |
| EV-000037 | https://itunes.apple.com/us/rss/customerreviews/page=1/id=1258723897/sortby=mostrecent/json | aa9c97cfc016f0e9 | pain | S4 | 3.1, 3.2 |
| EV-000040 | https://itunes.apple.com/us/rss/customerreviews/page=1/id=1258723897/sortby=mostrecent/json | aa9c97cfc016f0e9 | contra | S1 | 3.2 |
| EV-000043 | https://itunes.apple.com/us/rss/customerreviews/page=2/id=6449775006/sortby=mostrecent/json | 95bfe2c7d7048ab8 | switch | S4 | 3.1, 3.2 |
| EV-000044 | https://itunes.apple.com/us/rss/customerreviews/page=2/id=6449775006/sortby=mostrecent/json | 95bfe2c7d7048ab8 | contra | S1 | 3.2 |
| EV-000045 | https://itunes.apple.com/us/rss/customerreviews/page=1/id=6449775006/sortby=mostrecent/json | 5288f503eedb57bc | contra | S1 | 3.2 |
| EV-000051 | https://itunes.apple.com/us/rss/customerreviews/page=2/id=6449775006/sortby=mostrecent/json | 95bfe2c7d7048ab8 | wtp | S2 | 3.2 |
| EV-000055 | https://chatway.app/pricing | 5d122ab7d8a8073e | wtp | S1 | 3.9 |
| EV-000056 | https://chatway.app/pricing | 5d122ab7d8a8073e | wtp | S1 | 3.2, 3.9 |
| EV-000057 | https://www.smartsupp.com/pricing/ | 8e115af1479c58cc | wtp | S1 | 3.9 |
| EV-000063 | https://news.ycombinator.com/item?id=49154300 | 19a491f6cd416235 | pain | S1 | 2.1, 4 |
| EV-000064 | https://news.ycombinator.com/item?id=48894374 | 19a491f6cd416235 | contra | S0 | 2.1 |
| EV-000065 | https://news.ycombinator.com/item?id=46752629 | 19a491f6cd416235 | workaround | S3 | 2.1 |
| EV-000095 | https://news.ycombinator.com/item?id=48119687 | a5b0ea4aaa2baf33 | workaround | S3 | 3.1, 3.2 |
| EV-000114 | https://news.ycombinator.com/item?id=43339334 | 512f327e3e3ed52a | workaround | S3 | 2.1 |
| EV-000115 | https://news.ycombinator.com/item?id=43339636 | 512f327e3e3ed52a | workaround | S3 | 2.1 |
| EV-000121 | https://news.ycombinator.com/item?id=41354412 | 342b57025e49c950 | pain | S4 | 2.1 |
| EV-000127 | https://news.ycombinator.com/item?id=49201407 | 5de9fb55f4898229 | praise | S1 | 2.1 |
| EV-000239 | https://stackoverflow.com/questions/70936939/authorize-net-how-to-retry-failed-arb-transactions | 950493fb4032a3db | pain | S4 | 2.1 |

EV-000146 is cited from the GAP-006 card text in 2.2; it is in the ledger and verified like all 289 records.

## Appendix B. Discarded candidates
| Card | Status | Reason |
|---|---|---|
| GAP-003 Charging for browser extensions and verifying paid access | killed | Red team: crxpay, ExtensionPay and Addon Pay fully cover the job (entitlements, trials, multi-browser); the 2020 Chrome payments shutdown (WN-005) is an expired catalyst; only 2 of 27 dated records are recent; fee race of 2.5-5% on small extension revenue makes 1k MRR implausible; platform risk 3. |
| GAP-004 Accurate, low-noise outage alerts and public status pages | killed | Red team: Pulsetic and OnePageStatus deliver multi-region confirmed alerts and status pages free; updown.io prices per check; a wave of 2026 solo-built clones drew little attention; developers build their own monitor with AI agents in an hour (EV-000152, EV-000168); one says nobody looked at his status page (EV-000170). |
| GAP-005 Failed-payment recovery | insufficient | 2 domains (need 3); see 2.1. |
| GAP-002 VAT and sales-tax filing | insufficient | 2 qualifying domains (need 3); possible regulated-advice risk; see 2.1. |
| GAP-007 Subscriptions across several providers | insufficient | 2 domains; core pain on one record; see 2.1. |
| GAP-006 First users for a new launch | insufficient | 1 domain, 1 source type, no wtp or S4 record. |
| GAP-008 Consolidating scattered feedback | insufficient | 2 records, 1 domain. |
| GAP-009 Multi-language App Store listing updates | insufficient | 4 records, 1 domain, no wtp or S4 record. |
| GAP-010 Merchant-of-record access for rejected sellers | insufficient | 2 domains; likely out of scope (fund custody, KYC). |
| GAP-011 Card-testing fraud protection | insufficient | 2 records, 1 author; touches payment data. |
| GAP-012 Bare-minimum hosted checkout | insufficient | 2 records, 1 domain. |

## Appendix C. Method trail
- Methods applied (from cards and outputs): D16-D20 card synthesis and evidence threshold, D19 variations (GAP-003, GAP-009), red team on GAP-001, GAP-003 and GAP-004, D25 reporting. Saturation by Chao2 over 72 sampling units; double coding on codebook v3; double screening audit.
- Protocol amendments 1-6: see section 4.
- Human tasks recorded in the amendments: HT-003 (approval of 20 more subagents). Doctor warning: MGD_CONTACT not set (HT-001).
- Two evidence rounds: round 1 (general), round 2 (targeted at near-miss cards, by human directive).
