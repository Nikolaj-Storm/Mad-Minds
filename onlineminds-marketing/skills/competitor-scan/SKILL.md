---
name: competitor-scan
description: Research competitors for an OnlineMinds brand and market and produce a positioning, messaging, traffic, and ad-creative comparison with gaps and opportunities. Reads account-conventions; uses public Meta/Google ad libraries and web research where available (no third-party traffic/keyword data source is connected). Use when asked for a competitor scan, competitive brief, market analysis, or positioning comparison.
argument-hint: "<brand> [market] [competitor list]"
---

# Competitor Scan

> Load **account-conventions** first (brand, markets, Drive paths).

## Trigger
`/competitor-scan`, or a request for competitive/market analysis or a positioning comparison.

## Inputs
1. Brand + market (ask if missing).
2. Competitor set — use the provided list.

## Method
For each competitor: positioning and core messaging, content/positioning gaps vs. the brand, and ad creative/messaging patterns from public Meta/Google ad libraries where accessible. (Quantified traffic/keyword data needs a paid SEO/traffic tool, which is not currently connected.)

## Output
A comparison report: a positioning matrix, a messaging comparison table, content/keyword gaps the brand could own, ad-creative patterns and angles competitors use, and a prioritized list of opportunities and threats. Save to `04_Reports/ad-hoc/YYYY-MM-DD_<brand>_competitor-scan_<market>/`. State sources and dates at top.
