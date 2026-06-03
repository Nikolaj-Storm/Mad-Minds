---
name: report-builder
description: Generic OnlineMinds report assembler — turns any provided or hub-stored marketing data into a clean, templated report or a slide-ready summary, saved into the Marketing Hub with house formatting. Reads account-conventions for templates, naming, and Drive paths. Use when asked to format data into a report, build a deck-ready summary, or reuse a report template, when no more specific skill fits.
argument-hint: "<brand> <what to report on>"
---

# Report Builder

> Load **account-conventions** first (templates location, naming, Drive paths). Prefer a more specific skill (monthly-paid-review, seo-geo-audit, competitor-scan) when one fits.

## Trigger
`/report-builder`, or a request to format data into a report or deck-ready summary that no specific skill covers.

## Inputs
1. Brand and subject.
2. Data — from a hub file, a connector, or pasted by the user.
3. Output format — markdown report (default) or slide-ready outline.
4. Cadence/destination — weekly / monthly / quarterly / ad-hoc.

## Method
Pick the matching template from `04_Reports/_templates/` (create and save one if none fits). Apply house KPI definitions and currency. Lead with an executive summary, show every metric with prior-period/target context, and end with prioritized recommendations.

## Output
Save to the matching cadence folder under `04_Reports/` with house naming `YYYY-MM-DD_<brand>_<type>.md`. If slide-ready was requested, produce a per-slide outline (title + 3-5 bullets each). Confirm the saved path and state data source/date at the top.
