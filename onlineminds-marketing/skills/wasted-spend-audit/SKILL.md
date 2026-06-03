---
name: wasted-spend-audit
description: Find wasted ad spend across Google Ads, Meta Ads, and (for feed-based brands) Google Merchant Center for an OnlineMinds brand. Surfaces underperforming keywords, audiences, placements, AND product-level spend in Shopping/PMax (products spending without converting, low-impression products burning budget, disapproved-but-active SKUs). Produces an uploadable exclusion/negative list, a per-product action list for the feed where applicable, and a savings estimate. Reads account-conventions for KPI thresholds and Drive paths. Use when asked to cut wasted spend, find underperforming keywords/audiences/placements/products, clean up an account, or reduce CPA.
argument-hint: "<brand> [lookback, e.g. last 90 days]"
---

# Wasted Spend Audit

> Load **account-conventions** first (brand, KPI targets, currency, Drive paths).

## Trigger
`/wasted-spend-audit`, or a request to find/cut wasted spend, clean up an account, or reduce CPA.

## Inputs
1. Brand (portfolio brand; ask if missing).
2. Lookback window (default last 90 days).
3. Channels (Google Ads + Meta Ads default).

## Method
Pull from the connectors (or hub data) and flag spend that produced poor or no return against the brand's CPA/ROAS targets:

**Google Ads**
- Search terms with spend above [threshold from conventions] and zero conversions → negative keyword candidates.
- Keywords below target ROAS with meaningful spend.
- Low Quality Score keywords driving cost.
- Placements (Display/PMax) burning budget with no conversions.

**Meta Ads**
- Ad sets / audiences below target ROAS with material spend.
- Creatives with high frequency + falling CTR (fatigue).
- Placements with poor efficiency.

For each flag: entity, spend, conversions, the metric that failed, and recommended action (pause / negative / reduce budget / refresh creative).

## Output
1. A summary table grouped thematically, sorted by potential savings.
2. An **uploadable negative-keyword / exclusion list** (CSV) saved to `03_Data/cleaned/`.
3. A short report saved to `04_Reports/ad-hoc/YYYY-MM-DD_<brand>_wasted-spend/` with total estimated monthly savings and a prioritized action list.
4. State the data source and date range at the top. Do not auto-apply changes; recommend and let a human execute unless explicitly asked to apply.
