# Post and outreach drafts — {{EXPERIMENT_ID}}

Drafts only. The human reviews, adapts and sends them from their own account, through a human task (card V08). Each draft:
- starts with the affiliation disclosure
- states its channel's UTM link
- names the community rule that allows it

Fill one section per channel in the card, and save the result as `validation/assets/{{EXPERIMENT_ID}}/posts.md`.

---

## Channel: {{CHANNEL_ID}} (utm_source={{CHANNEL_ID}})
- **Where:** {{COMMUNITY_NAME}}, {{COMMUNITY_URL}}
- **Rule checked:** {{COMMUNITY_RULE}} (for example "self-promotion only in the weekly thread", or "no links; ask the moderators first")
- **Fallback if not allowed:** {{FALLBACK_CHANNEL}}

**Community post**
> Disclosure: I'm {{HUMAN_FIRST_NAME}}, and I'm building a small tool for this. {{SEGMENT_PLURAL}}: how do you {{JOB_IN_THEIR_WORDS}} today?
> I keep hearing that {{PAIN_IN_THEIR_WORDS}}. I'd love to know whether that's true for you, and what you do about it.
> If it's a real pain, there's a waitlist here: {{UTM_LINK}}. Nothing is built or for sale yet. "No, it's fine" is a useful answer too.

**Reply to comments (keep it short, never argue)**
> Thanks, that's really useful. Can I ask what you did the last time that happened?

---

## Outreach message (email or DM from the human's own account)
- **To:** people with a plausible interest only (for example, people who publicly described this problem), one message and at most one follow-up.

> Subject: Quick question about {{JOB_IN_THEIR_WORDS}}
>
> Hi {{FIRST_NAME_OR_HANDLE}},
> I'm {{HUMAN_FIRST_NAME}}, and I'm building a tool for {{SEGMENT_PLURAL}} who {{JOB_IN_THEIR_WORDS}}. Disclosure: this is my own project.
> I saw your post about {{PUBLIC_CONTEXT}}. Would you be open to a 25-minute call about how you handle it today? I'm not selling anything on the call.
> If not, no problem at all, and I won't follow up more than once.
> {{HUMAN_FIRST_NAME}}

## Letter-of-intent request (B2B, `loi` cards only)
> Thanks for the conversation. As discussed, {{PRODUCT_NAME}} doesn't exist yet. If it did what we talked about ({{OUTCOMES}}) at around {{PRICE_POINT}} per month, would you sign a short, non-binding letter saying you intend to try it? It commits you to nothing, and it helps me decide whether to build it.

## Pre-sale message (`presale` cards only; payment link from the human's task)
> {{PRODUCT_NAME}} isn't built yet. If you'd like to reserve early access at {{PRICE_POINT}}, you can pay here: {{PAYMENT_LINK}}.
> We plan to deliver by {{DELIVERY_DATE}}. If we don't, or if you change your mind before then, we refund you in full ({{REFUND_HOW}}).
