---
name: campaign-plan
description: Build an OnlineMinds campaign brief for a brand — objectives, audience, channel mix across paid (Google/Meta) and organic, week-by-week content calendar, budget allocation, and success metrics tied to house KPIs. Reads account-conventions for brands, KPI definitions, and Drive paths. Use when planning a launch, promotion, lead-gen push, or any multi-channel marketing campaign.
argument-hint: "<brand> <goal> [timeline] [budget]"
---

# Campaign Plan

> Load **account-conventions** first (brand, KPI definitions, currency, Drive paths).

## Trigger
`/campaign-plan`, or a request to plan a campaign, launch, or promotion.

## Inputs
1. Brand (ask if missing) and market(s).
2. Goal stated as a measurable outcome (e.g. "500 signups").
3. Timeline and budget range (currency per conventions).
4. Audience/persona (pull from knowledge base if present).

## Output
A campaign brief: objective + measurable KPIs (defined per account-conventions), audience segmentation, core messages per segment, channel strategy (paid Google/Meta + organic/SEO + email), a week-by-week content calendar with dependencies, budget allocation by channel with expected CPA/ROAS, and the tracking/measurement plan. End with risks and a go/no-go checklist.

Save to `05_Plans_and_Strategy/campaign-briefs/` as `YYYY-MM-DD_<brand>_campaign-plan_<slug>.md`. Confirm the path. Offer to generate the matching content briefs via `/content-brief`.
