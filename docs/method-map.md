# Method map

This map traces every method from the two original answers (how researchers find research gaps, and how founders find market gaps) to where it now lives in the skills. For each method it gives the method card(s), the script command(s) and a status. Commands are shortened to `gapscan.py …` (market-gap-discovery) and `gapval.py …` (market-gap-validation); run them as `python3 SKILL_DIR/scripts/<script> …`.

Contents
1. Legend
2. Research-gap answer → skills
3. Market-gap answer → skills
4. Added methods (not in the original answers)
5. Summary counts

## 1. Legend
| Status | Meaning |
|---|---|
| core | Runs in every discovery run |
| conditional | Runs when its trigger holds, for example a source being reachable or a key being set |
| validation | Lives in the validation skill and needs real respondents or the human operator |
| deferred | Belongs to a future skill (build / launch / monitor) or is optional; the reason is given |
| excluded | Deliberately not used; the reason and any replacement are given |

Method cards are `D01–D25` (discovery, in `skills/market-gap-discovery/references/methods/`) and `V01–V10` (validation, in `skills/market-gap-validation/references/methods/`).

## 2. Research-gap answer → skills

### 2.1 Gap types (Miles 2017) → gap-card fields
| Gap type | Where it lives | Status |
|---|---|---|
| Evidence (contradictory) gap | D17 confusion spotting; D20 `robinson_reason: inconsistent`; contra evidence feeds D22 inconsistency | core |
| Knowledge gap | D17 neglect spotting; D16 absolute gap; D20 `robinson_reason: insufficient` | core |
| Practical-knowledge gap | D20 `robinson_reason: wrong-information` (supply addresses the wrong job or outcome) | core |
| Methodological gap | D16 approach axis (every product uses the same approach) → D18 problematization | core |
| Empirical gap | D20 `assumptions` → tested in V02–V04 | core / validation |
| Theoretical gap | D18 problematization (challenge the incumbents' shared assumptions) | core |
| Population gap | D20 `gap_type.primary: segment` / `language`; D19 segment and language variation | core |

### 2.2 Methods A1–E27
| # | Method | Card(s) | Command(s) | Status | Note |
|---|---|---|---|---|---|
| A1 | Systematic literature review (PRISMA 2020) | D01, D06, D25 | `gapscan.py protocol freeze`, `prisma` | core | The run is a PRISMA-style review of a market |
| A2 | Scoping review (Arksey & O'Malley; JBI) | D01 | `gapscan.py init`, `protocol check` | core | Frames the whole discovery pipeline |
| A3 | Systematic mapping study (Petersen) | D07 | `gapscan.py assign --phase mapping`, `merge --phase mapping` | core | Keywording → classification scheme |
| A4 | Evidence gap maps (3ie, Campbell) | D16 | `gapscan.py gapmap` | core | Jobs × solution approaches; absolute vs synthesis gaps |
| A5 | Concept matrix (Webster & Watson) | D15 | `gapscan.py matrix` | core | Becomes the competitor matrix |
| A6 | Robinson et al. 2011 (PICOS + reasons) | D01, D20 | `gapscan.py cards check` | core | PICOS question and the gap card's `robinson_reason` |
| B7 | Harvest "Limitations" / "Future work" | D08 | `gapscan.py fetch gh-issues`, `fetch wp-reviews`, `fetch apple-reviews`, `fetch atl-reviews`, `snapshot` | core | Market equivalents: 1–3★ reviews, public roadmaps, feature-request boards, enhancement issues, changelogs |
| B8 | Review articles and research agendas | D12, D16 | `gapscan.py snapshot` | conditional | Analyst and investor theses count only as weak why-now signals; comparison content counts as "synthesis" in the gap map |
| B9 | Calls for papers / special issues | D12 | `gapscan.py snapshot` | conditional | YC Requests for Startups and accelerator or grant calls, as weak signals |
| B10 | Recent PhD theses | D03 | `gapscan.py fetch hn --tags show_hn`, `fetch yc` | core | Recent launches show what others are trying now |
| C11 | Bibliometric analysis (co-words, bursts, counts) | D11, D16 | `gapscan.py fetch hn-counts`, `fetch se-counts`, `fetch wiki-views`, `bursts`, `gapmap` | core / conditional | VOSviewer and CiteSpace measures reimplemented in the standard library (Kleinberg bursts, association strength) |
| C12 | Citation-mapping tools (Connected Papers, ResearchRabbit, Litmaps, Inciteful) | D05 | `gapscan.py assign --phase snowball`, `merge --phase snowball` | core | The tools are replaced by snowballing over alternatives, "vs" and integration pages, plus co-mentions |
| C13 | Scite.ai (supporting / contrasting citations) | D08, D20, D22 | `gapscan.py verify`, `certainty` | core | Replaced by the evidence `stance` field and `counter_evidence`, which feed the inconsistency rating |
| C14 | Topic modeling (LDA, BERTopic) | D13, D14 | `gapscan.py agreement`, `themes` | excluded | Replaced by a double-coded codebook checked with Krippendorff's α; more transparent and auditable, and standard-library only |
| C15 | AI research assistants (Elicit, Consensus, Semantic Scholar) | D09 | `gapscan.py verify` | core | The agents are the assistants. Their "verify everything" lesson became snapshot-based quote verification; the academic search tools themselves are not used |
| D16 | Gap-spotting (confusion, neglect, application) | D17 | `gapscan.py cards check` | core | Recorded in the gap card's `sa_mode` |
| D17 | Problematization | D18 | — | core | Incumbent assumptions → ERRC grid |
| D18 | "Change one dimension" | D19 | `gapscan.py variants` | core | Generated systematically with a morphological box |
| D19 | Replication and extension | D19, D17 | `gapscan.py variants` | core | Application spotting: a proven model in a new segment, language or platform |
| E20 | Supervisor and the lab's research program | D01 | `gapscan.py hq done`, `protocol amend` | core | The founder-fit fields plus gated approvals by the human operator |
| E21 | Journal clubs / lab meetings | D02, D14, D21 | `gapscan.py assign --phase press`, `agreement`, `assign --phase redteam` | core | PRESS review, an independent coder B and the red team stand in for group critique |
| E22 | Unexpected or "failed" results | D17, D21 | `gapscan.py certainty` | core | Contradictions become confusion-spotting candidates and counter-evidence |
| E23 | New tools or techniques | D12, D19 | `gapscan.py variants` | core | Technology and platform catalysts in the why-now log; an AI-native variation dimension |
| E24 | Conferences (Q&A, panels, keynotes) | — | — | excluded | Low value for agents: mostly video and hard to verify. A talk can still appear as a weak why-now item through web search |
| E25 | Practitioners and industry | V05 | `gapval.py ingest --kind interviews`, `agreement`, `themes` | validation | Problem and switch interviews, recruited by the human |
| E26 | Expert consensus (Delphi, James Lind Alliance) | V05 | `gapval.py ingest --kind interviews` | deferred | Needs real experts. An LLM-simulated panel would be prediction, not evidence; optional as structured expert interviews |
| E27 | Funding calls and policy priorities | D12 | `gapscan.py snapshot` | core | Political and legal PESTLE factors; regulation as a catalyst |

### 2.3 The 10-step PhD workflow
| Step | Where it lives | Status |
|---|---|---|
| 1 Read broadly | D02 independent lexicon harvest (`assign --phase lexicon`) | core |
| 2 Narrow down with the supervisor | D01 protocol plus a gated approval task (`hq done`) | core |
| 3 Search systematically | D03 scouting, D04 saturation (`saturation`), D05 snowballing | core |
| 4 Build the concept matrix | D15 (`matrix`) | core |
| 5 Extract limitations and future work | D08 (`assign --phase evidence`) | core |
| 6 Visualize (VOSviewer) | D16 gap map and association strength (`gapmap` CSVs) | core |
| 7 List 3–5 candidate gaps, labelled by type | D17–D20 (`cards check`) | core |
| 8 Validate each gap | D21 red team, D22 certainty, D23 gates and score, D24 sizing | core |
| 9 Discuss with the supervisor | Gated shortlist approval task | core |
| 10 Google Scholar alerts | D25 `output/watchlist.json` for the future monitor skill | deferred: monitoring is a later skill |

### 2.4 Validation tests and gap statement
| Test | Where it lives | Status |
|---|---|---|
| Is it real? | D21 adversarial search for existing solutions (other languages, open source, recent launches) | core |
| Does it matter ("so what")? | D23 Pain and Pay criteria; D20 triangulation and a statement explaining why the setting differs | core |
| Is it feasible? | D23 gates (agent-buildability, human-ops burden, regulatory load, ToS) | core |
| Is it the right size? | D24 (`size`) and the D23 Size criterion | core |
| Gap statement template | D20 `statement`, glossary §1 | core |

## 3. Market-gap answer → skills

### 3.1 Gap types → `gap_type.primary`
| Original gap type | Field value / location | Status |
|---|---|---|
| Underserved segment | `segment` | core |
| Non-consumption | `non-consumption`, plus D17 noncustomer tiers 1–3 | core |
| Price gap | `price`, plus the D15 price ladder | core |
| Quality / experience gap | `quality` | core |
| Feature gap | `feature` | core |
| Access / distribution gap | `access`; split into a separate `integration` value (marketplace or app-store gaps) | core |
| Geographic gap | `language` (language, currency, local compliance), plus D19 language variation | core |
| Trust / information gap | `trust` | core |
| "Why now" gap | `gap_type.catalyst`, plus the D12 why-now log. It modifies any gap rather than being a type of its own | core |

### 3.2 Methods 1–37
| # | Method | Card(s) | Command(s) | Status | Note |
|---|---|---|---|---|---|
| A1 | Jobs-to-be-Done | D13 | `gapscan.py codebook freeze` | core | J- codes |
| A2 | Outcome-Driven Innovation | D13, D16, V06 | `gapscan.py gapmap`, `gapval.py stats` | core + validation | The desk proxy is used for ranking only; real survey thresholds (10/12/15) apply only in V06 |
| A3 | The Mom Test interviews | D10, V05 | `gapval.py ingest --kind interviews` | core + validation | Also grades desk evidence: past behaviour outranks hypotheticals (S0–S4) |
| A4 | Customer Development (Blank) | V01–V10 | `gapval.py next` | validation | Shapes the validation skill: discovery → validation |
| A5 | Observation and workaround hunting | D08, D10 | `gapscan.py fetch gh-repos`, `snapshot` | core | `workaround` stance; S3 strength. Direct observation of people happens in V05 |
| A6 | Customer journey mapping | D13 | `gapscan.py codebook freeze` | core | Becomes the 8-step job map |
| A7 | Value Proposition Canvas | D13, D25 | `gapscan.py validate --report` | core | Pain and gain codes; the canvas appears in the dossier |
| A8 | Kano surveys | V06 | `gapval.py ingest --kind survey-kano`, `stats` | validation | Only with n ≥ 200, otherwise labelled directional |
| A9 | Van Westendorp pricing | V06, D15 | `gapval.py ingest --kind survey-vw`, `stats`; `gapscan.py matrix` | validation | Desk pricing evidence comes from the price ladder |
| B10 | Review mining | D08 | `gapscan.py fetch apple-reviews`, `wp-reviews`, `atl-reviews` | core | G2, Capterra, GetApp and TrustRadius are excluded by their terms; Google Play and Chrome Web Store review pages by robots.txt |
| B11 | Forums and communities | D08 | `gapscan.py fetch hn`, `fetch se`, `fetch gh-issues` | core | Reddit only through an approved tier-2 key; Indie Hackers excluded (blocks AI bots); login-walled groups not used |
| B12 | Search-demand analysis | D11 | `gapscan.py fetch wiki-views`, `fetch hn-counts`, `bursts` | conditional | Free proxies by default; Trends alpha, Keyword Planner, SerpApi and DataForSEO via a human-provided key |
| B13 | Social-listening tools | D11, D08 | — (tier-2 key) | conditional | Paid tools and the X API only when the human enables and funds them |
| B14 | Internal data (support tickets, churn) | — | `gapval.py ingest` | deferred | A new venture has none; human-provided exports belong to the future monitor skill |
| C15 | Competitor feature matrix | D15 | `gapscan.py matrix` | core | |
| C16 | Perceptual / positioning map | D15 | `gapscan.py matrix` | core | Built from the price ladder × the classification facets |
| C17 | Blue Ocean (strategy canvas, ERRC, Six Paths, noncustomer tiers) | D15, D18, D17 | `gapscan.py matrix` | core | |
| C18 | Porter's Five Forces | D21 | `gapscan.py merge --phase redteam` | core | SaaS adaptation: platform supplier power, substitutes |
| C19 | Failed-startup analysis | D21 | `gapscan.py merge --phase redteam` | core | `failed_attempts` in the red-team record |
| C20 | Investor signals | D03, D12 | `gapscan.py fetch yc` | core | YC directory via the yc-oss mirror; Crunchbase and Dealroom are paid and not used |
| D21 | PESTEL | D12 | `gapscan.py snapshot` | core | A why-now log with dated evidence |
| D22 | Regulation tracking | D12 | `gapscan.py snapshot` | core | The legal and political factors |
| D23 | Technology shifts | D12, D19 | `gapscan.py variants` | core | Technological and platform factors; AI-native variation |
| D24 | Trend tracking | D11 | `gapscan.py bursts` | conditional | Kleinberg bursts on free series; Exploding Topics is not used (paid, unclear access) |
| D25 | Demographic shifts | D12 | `gapscan.py snapshot` | core | The social factor |
| D26 | Geographic arbitrage | D19, D20 | `gapscan.py variants` | core | Language and geography variation; `language` gap type |
| E27 | Market segmentation | D13, D16 | `gapscan.py gapmap` | core | S- codes; segment × pain association strength |
| E28 | Supply–demand mismatch | D16 | `gapscan.py gapmap` | core | Demand vs supply per gap-map cell |
| E29 | Value chain analysis | D13 | `gapscan.py codebook freeze` | core | Manual steps and middlemen show up in the job-map steps |
| E30 | TAM / SAM / SOM | D24 | `gapscan.py size` | core | Bottom-up only, never "x% of TAM" |
| F31 | Scratch your own itch | D01, D23 | `gapscan.py score` | core | Founder-fit fields → the right-to-win criterion |
| F32 | Schlep blindness | D01, D21, D23 | `gapscan.py score` | core | `schlep_tolerance`; less competition in tedious problems shows up in the competition criterion |
| F33 | Industry insiders | V05 | `gapval.py ingest --kind interviews` | validation | Recruited by the human operator |
| G34 | Smoke test / landing page | V07 | `gapval.py utm`, `assets check`, `ingest --kind visits`, `stats` | validation | Honest fake door, judged by the pre-registered Wilson rule |
| G35 | Concierge / Wizard-of-Oz MVP | V03 | `gapval.py prereg new --type concierge` | validation | Optional; needs heavy human involvement |
| G36 | Pre-sales / letters of intent | V03, V04 | `gapval.py ingest --kind loi`, `ingest --kind presale` | validation | The strongest evidence on the ladder |
| G37 | Sean Ellis PMF survey | V10 | `gapval.py ingest --kind ellis`, `stats` | deferred | Needs real users after launch: planned in the watchlist for the future monitor skill |

### 3.3 The 9-step market workflow
| Step | Where it lives | Status |
|---|---|---|
| 1 Choose a domain | D01 protocol (topic, scope, founder fit) | core |
| 2 Scan macro changes (PESTEL) | D12 | core |
| 3 Listen (reviews, forums, search data) | D08, D11 | core |
| 4 Map competitors | D03–D07, D15 | core |
| 5 Interview 15–30 customers | V05: at least 10 good interviews, stopping at Guest–Namey–Chen saturation | validation |
| 6 Score each candidate gap | D16 proxy opportunity score, D23 rubric (`score`) | core |
| 7 Size the market | D24 (`size`) | core |
| 8 Test (landing page, manual MVP, pre-sales) | V03–V09 | validation |
| 9 Decide go / pivot / drop | V10 `gapval.py verdict` → GO / ITERATE / PIVOT / KILL | validation |

### 3.4 Validation tests and gap statement
| Test | Where it lives | Status |
|---|---|---|
| Pain | D23 Pain criterion (strength levels, distinct authors and domains), D22 certainty | core |
| Pay | D23 Pay criterion (S4 / WTP evidence, price ladder); V06 Van Westendorp; V03 LOI / pre-sale | core + validation |
| Size | D23 Size criterion, D24 | core |
| Why is it empty? | D21 `why_empty` and failed attempts | core |
| Why now | D12, D11 bursts, D23 why-now criterion | core |
| Reach | D23 Reach criterion (`reach_channels` in the judgment), `gtm_channels` in the handoff | core |
| Right to win | D23 right-to-win (judgment), D01 founder fit | core |
| Gap statement template (Moore positioning) | D20 `statement`, D25 dossier positioning | core |

## 4. Added methods (not in the original answers)
| Method | Where | Why it was added |
|---|---|---|
| PRISMA-P protocol pre-registration | D01 `protocol freeze`, `protocol amend` | Freezing the plan before searching stops goalposts from moving and makes runs auditable and comparable |
| PRESS peer review of the search strategy | D02 `assign --phase press`, `lexicon apply-press` | Catches query errors (missing synonyms, bad operators) before costly sampling |
| Sampling units + Chao2 + sample coverage | D03, D04 `saturation` | Turns the doctoral "~90% overlap" rule into an estimate that corrects raw overlap's bias toward stopping early |
| Holdout probe scout | D04 `assign --phase probe` | A direct empirical check that copies of the same model did not just agree with each other |
| Wohlin snowballing | D05 | Finds what keyword search misses (alternatives, "vs" and integration pages), with a defined stop rule |
| Dual screening audit | D06 `screen-audit` | Measures how reliable include/exclude decisions are, as PRISMA practice requires |
| Petersen systematic mapping | D07 | Produces the classification scheme the gap map needs |
| Callaghan statistical stopping | D08 `stoptest` | Safe early stopping on large ranked pools; "N irrelevant in a row" missed targets in about 39% of runs |
| Guest–Namey–Chen thematic saturation | D14 `themes`, V05 `gapval.py themes` | A reportable rule for when to stop collecting pains or interviews |
| Krippendorff's α per code | D14 `agreement` | Per-code reliability for multi-label coding; an independent second coder is the agent version of a second reviewer |
| GRADE-CERQual certainty | D22 `certainty` | Separates "how sure are we" from "how big is it"; caps desk-only demand evidence at weak |
| Kleinberg burst detection | D11 `bursts` | Finds emerging terms (why-now evidence) with a significance test |
| Association strength | D16 `gapmap` | Finds segment-specific pain clusters, normalised for frequency |
| Universal job map (8 steps) | D13 | Checks coverage of a job step by step |
| Forces of Progress + switch timeline | D13 (F- and T- codes) | A coding frame for switching stories found in reviews and forums |
| Morphological box (Zwicky) | D19 `variants` | Makes "change one dimension" systematic instead of ad hoc |
| Pre-mortem (Klein) | D21 | A structured way to surface failure modes before investing |
| Dirichlet weight sensitivity (`p_top3`) | D23 `score` | Shows whether the ranking survives reasonable disagreement about weights |
| Webster–Kemp + rank-biased overlap | `gapscan.py compare` | Reproducibility check between two independent runs |
| Opportunity Solution Tree | V01 `ost check` | At least 3 solutions per opportunity prevents fixating on the first idea |
| Assumption mapping (+ ICE tie-break) | V02 `assumptions rank` | Tests the riskiest, least-evidenced assumptions first |
| Test Cards / Learning Cards | V04 `prereg new`, `prereg freeze`; V10 | Structured hypotheses and an audit trail of what was learned |
| XYZ hypothesis (Savoia) | V04 | Falsifiable numeric thresholds, with X derived from unit economics |
| Wilson decision rule | V09 `stats` | Honest pass / fail / inconclusive calls at small samples |
| Opportunity lenses: innovative imitation, new combinations, bundling and unbundling, low-end disruption, ports, replacements, hosted open source, productized services | D26 `gapscan.py opportunities scan` | A gap is the hardest opportunity to evidence; most small software businesses start from proven demand (a crowded market is a good sign: Graham 2012). Each lens is a script rule over the run's own data |
| App-store traction (installs, ratings) as revealed use | D27 `gapscan.py traction` | Demand evidence at zero subagent cost from responses the scouts already saved; within-store percentiles |
| Stage-gate screening + successive halving | D28 `assign --phase scan-evidence`, `opportunities score` | A cheap scan ranks many options and spends evidence only on the better half; deep runs then start from one sharp question |

## 5. Summary counts
| Source | Items mapped | Core | Conditional | Validation | Deferred | Excluded |
|---|---|---|---|---|---|---|
| Research-gap methods A1–E27 | 27 | 21 | 2 | 1 | 1 | 2 |
| Market-gap methods 1–37 | 37 | 25 | 3 | 7 | 2 | 0 |

Rows marked "core + validation" or "core / conditional" are counted under their first status. In addition, sub-parts of some core methods are excluded on legal grounds: G2, Capterra and similar review mining, Upwork and Fiverr scraping (HN "Who is hiring" is used instead), unauthenticated Reddit, and Google Play / Chrome Web Store review pages. The source registry is `skills/market-gap-discovery/assets/channels.json`.
