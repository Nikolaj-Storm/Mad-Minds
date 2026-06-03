---
name: content-brief
description: Produce an OnlineMinds content brief for a brand — blog post, landing page, marketing email, or social — grounded in the brand's voice and target market. Reads account-conventions and the brand-voice file, applies SEO/GEO guidance, and saves the brief into the Marketing Hub. Use when asked to brief, plan, or draft a piece of content for any portfolio brand.
argument-hint: "<brand> <content type> <topic>"
---

# Content Brief

> Load **account-conventions** and the brand's `01_Knowledge_Base/brand/<brand>/brand-voice.md` before writing anything customer-facing.

## Trigger
`/content-brief`, or a request to brief/plan/draft content for a brand.

## Inputs
1. Brand (portfolio brand; ask if missing) and market/language (Danish for DK assets, else English unless specified).
2. Content type: blog post / landing page / marketing email / social.
3. Topic, target audience/persona (pull from `01_Knowledge_Base/ICP-and-personas/` if present), and primary goal (traffic, signups, sales).
4. Target keyword/intent (optional — can derive from Ahrefs).

## Output
A brief containing: working title + 3 headline options, target keyword + search/AI intent, audience and angle, key messages, required sections/outline, internal links to other brand pages, CTA, tone notes from the brand voice, and SEO/GEO notes (schema, citable facts to include). 

If the user asks, follow the brief with a full draft in the brand voice. Save the brief (and draft if produced) to `05_Plans_and_Strategy/content-calendars/` or `04_Reports/ad-hoc/` as `YYYY-MM-DD_<brand>_content-brief_<slug>.md`. Confirm the saved path.
