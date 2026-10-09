# Human operations for validation

The agent prepares; the human acts in the world. Every outward action is a human task, whatever the run's autonomy setting: publishing a page, posting, emailing, interviewing, advertising, paying or creating accounts. Tasks live in `RUN/human-tasks.json`, with a readable view in `RUN/human-tasks.md`, and are managed with `gapval.py hq`.

## Commands
- List open and closed tasks: `gapval.py hq list RUN`
- Close a task: `gapval.py hq done RUN HT-NNN --note "what was done, URLs, dates, env var name"`, or `gapval.py hq decline RUN HT-NNN --note "why"`
- Add an extra task the cards missed: `gapval.py hq add RUN --type TYPE --title TEXT --why TEXT --steps TEXT --returns TEXT [--phase P] [--blocking] [--fallback TEXT]`
- `gapval.py next RUN` returns `BLOCKED HT-NNN` while a blocking task is open. Stop there.

Secrets never go into notes or files. The human puts tokens in environment variables, and the note records only the variable's *name*.

## What `next` creates automatically
- **Plan approval.** Once every Test Card is frozen: one blocking `judgment` task listing each experiment's type, X, `min_n` and budget. A decline with a note means revise (new cards, new ids); a new approval request follows.
- **Launch tasks.** One blocking task per `required_ht` slug of each frozen card, in the card's order, titled "EXP-NN: slug". The type comes from the words in the slug, as in the catalogue below.
- **Export task.** One blocking "EXP-NN: export results" task per experiment, naming the exact paths: `validation/data/EXP-NN/<kind>.csv`, or `validation/data/EXP-NN/interviews/` with one `.txt` per interview.
- **UTM links.** When a launch task is closed with the live URL in its note, `next` returns `DO V07` to run `gapval.py utm` before any posting task. That is why the deploy slug comes first on landing-page cards.

Declining any launch or export task closes that experiment: the verdict lists it as NOT_RUN. A fallback channel needs a new card.

## Task catalogue
| Operation (`required_ht` slug) | Type (from the slug's words) | Typical steps for the human | Returns |
|---|---|---|---|
| plan approval (automatic) | judgment | Review the cards' hypotheses, thresholds, channels, budget and exposure limits | approve, or decline with notes |
| `deploy-landing` | account | Deploy the checked page, or create a deploy token: `export DEPLOY_TOKEN=…` | the live URL, or the env var name |
| `hosting` / `domain` | account | Create the hosting project or point a subdomain | the project URL |
| `form-backend` | account | Create a form endpoint that stores emails and consent; replace `FORM_ACTION_PENDING` | the form action URL |
| `analytics` | account | Set up privacy-friendly analytics with UTM reporting | the dashboard name and how to export |
| `publish-page` | outward-action | Publish the checked `landing.html` with its `privacy.html` | the live URL |
| `privacy-review` | legal | Read `privacy.md`, fill in the controller details, publish it | the privacy URL |
| `post:<community>` | outward-action | Check the community rules; post the draft from `posts.md` with its UTM link | post URL and date |
| `outreach:<list>` | outward-action | Send the outreach drafts from your own account; one follow-up at most | number contacted |
| `ad-budget-<N>usd` | payment | Run the ad set with the card's UTM link, capped at N USD | spend, impressions, clicks |
| `stripe-payment-link` | payment | Create a payment link with the refund terms shown | the link (not secret) |
| `recruit-interviews` | outward-action | Recruit ICP interviewees and schedule calls with consent | the number scheduled |
| `conduct-interviews` | outward-action | Run the guide; save pseudonymous transcripts as `INT-NN.txt` | the folder path |
| export results (automatic) | account | Export pseudonymous counts or responses with the CSV columns in `references/cli.md` to the paths named in the task | the files at those paths |

Slug words map to types: deploy, hosting, domain, form, analytics → `account`; stripe, payment, presale, deposit, ads, budget → `payment`; post, outreach, email, recruit, publish → `outward-action`; legal, privacy → `legal`; anything else → `outward-action`.

## Example of an extra task
Use `hq add` only for operations the cards missed, such as a scoped deploy token:
```
gapval.py hq add RUN --type key --phase V4 --blocking \
  --title "Deploy token for EXP-01 landing page" \
  --why "The agent can deploy the checked page only with your token" \
  --steps "Create a token scoped to one project in your hosting account; run: export DEPLOY_TOKEN=<token>" \
  --returns "The env var name (DEPLOY_TOKEN). Never paste the token itself." \
  --fallback "You deploy landing.html yourself and send the live URL"
```

## Rules of thumb
- One slug per operation. Small tasks are easy to approve and easy to decline.
- Write steps the human can follow without opening the run folder: exact text, exact links, exact limits.
- Put the live URL in the deploy task's note, so the UTM links can be made before posting.
- Record `hq done` only when the human confirms the task, either by running the command or by telling you in the conversation. Never mark a task done on an assumption. After that, `gapval.py next RUN` continues.
