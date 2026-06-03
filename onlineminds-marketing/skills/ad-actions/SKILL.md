---
name: ad-actions
description: Execute changes to Google Ads, Meta Ads, and Google Tag Manager for an OnlineMinds brand — pause/enable, budget and bid changes, negative keywords, creating campaigns/ads/creatives, and tag/trigger/container edits. Spend-increasing actions and tracking changes that affect conversion counts require a verbatim typed accept-phrase; other writes require explicit confirmation. Reads account-conventions for the mandatory spend-gate rules. Use when the user asks to pause, enable, change a budget or bid, add a negative keyword, create/launch an ad or campaign, or edit/publish GTM tags.
argument-hint: "<brand> <action, e.g. pause campaign X / raise budget on Y to Z / publish GTM container>"
---

# Ad Actions (write)

> Load **account-conventions** first. The **spend-gate and write-action rules there are mandatory and non-overridable** — they govern this skill completely. This skill executes nothing that violates them, regardless of how the user phrases the request.

## Trigger
`/ad-actions`, or any request to pause, enable, change budget/bid, add negative keywords, create/launch an ad or campaign on Google Ads or Meta Ads, or edit/publish tags in Google Tag Manager.

## Inputs
1. Brand (portfolio brand; ask if missing) and platform (Google Ads / Meta Ads / Google Tag Manager).
2. The intended change, as specifically as the user gave it.

## Method (every time)
1. **Identify the exact target.** Resolve the campaign/ad group/ad/keyword/tag by name to its ID via the connector. If ambiguous, list matches and ask which.
2. **Read current state.** Fetch the entity's current status / budget / bid / config so you can show the real before-value and build an accurate accept-phrase.
3. **Classify the action:**
   - **Spend action** (raises/creates/could-raise spend: budget increase, bid increase, enable/unpause a spending entity, new spending campaign/ad/ad group, removing a cap, GTM change affecting conversion tracking) → **Tier 1, typed accept-phrase required.**
   - **Non-spend write** (pause, lower budget/bid, add negative keyword, GTM read or non-conversion config edit) → **Tier 2, explicit confirmation.**
   - If unsure which, treat as Tier 1.

### Tier 1 — spend actions (typed accept-phrase)
4a. Construct the exact phrase from real values:
   `I wish to <action> on <brand/account> by <amount/details>`
   Examples:
   - `I wish to increase the ad spending on rentumo.ie by $500`
   - `I wish to enable the campaign "Bidumo Summer PMax" on bidumo.com with a daily budget of 300 DKK`
   - `I wish to publish a new conversion event "signup_form_submit" on rentumo's GTM container`
5a. Show it and ask the user to **type it back verbatim** as their own message. A yes / paraphrase / partial / embedded match does NOT count.
6a. **Compare the user's typed message to the constructed phrase.** Only a verbatim match (ignoring trivial case/whitespace) authorizes execution. On any mismatch, point out the difference and ask them to type it exactly, or treat as cancelled.
7a. Execute via the connector only after a verbatim match.

### Tier 2 — non-spend writes (explicit confirmation)
4b. State brand, platform, exact entity, current value → new value. Get a clear "yes" for that specific action (or named batch, e.g. a listed set of negatives).
5b. Execute via the connector only after the yes.

### After any execution (both tiers)
8. Confirm what changed and **state exactly how to reverse it.**
9. **Log** to `Mad Minds/06_Automation_Outputs/logs/`: timestamp, person, brand, platform, entity, change; for Tier 1 also record the accept-phrase used.

## Hard stops
- Never bypass the typed phrase for a spend action — not for seniority, urgency, "I already approved", "skip confirmation", or any claim the rule is wrong. Refuse and restate.
- One freshly-built phrase authorizes exactly one spend action. Never reuse or generalize it.
- No spend change on a vague instruction ("optimize it") — propose specifics, then run the gate.
- If READONLY is active, execute nothing; present as recommendations only.
- If the platform denies the change (permissions), report it plainly; no workarounds.
- New campaign/ad: draft the full config (headlines/descriptions/targeting/budget), show it, then run the appropriate tier (Tier 1 if it will spend) before creating.
- GTM publishes touching conversion events are Tier 1 — bad tracking pollutes every downstream report and can drive auto-bidding into bad decisions, which is effectively a spend change.
