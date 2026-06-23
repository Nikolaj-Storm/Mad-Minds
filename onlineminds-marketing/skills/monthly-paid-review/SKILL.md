---
name: monthly-paid-review
description: Produce OnlineMinds' monthly paid-media performance review for a brand across Google Ads, Meta Ads, Thribee, and (where applicable) Google Merchant Center for Shopping/PMax feed health. Reads house KPIs and the Drive folder map from account-conventions, pulls last month's spend/conversions/ROAS from the ad-platform connectors (or cleaned data in the hub), surfaces product-feed issues that may have dragged performance (disapprovals, missing GTINs, price mismatches) for feed-based brands, compares to prior month and target, and writes a finished, templated report into the Marketing Hub. Use when asked for a monthly paid review, paid-media report, monthly ads summary, or "how did paid do last month" for any brand.
argument-hint: "<brand> [month, e.g. 2026-05]"
---

# Monthly Paid Review

> First, load **account-conventions** for the brand list, KPI definitions, currency, attribution window, and Drive paths. Everything below depends on it.

## Trigger

User runs `/monthly-paid-review`, names a brand, or asks for a monthly paid-media report / ads summary.

## Step 1 — Scope

1. **Brand** — must be one of the portfolio brands. If not given, ask.
2. **Month** — default to the most recently completed calendar month. Accept `YYYY-MM`.
3. **Channels** — Google Ads, Meta Ads, and Thribee by default. Include others if the brand runs them (check the brand's entry in account-conventions).

## Step 2 — Get the data (in priority order)

1. **Cleaned hub data:** check `03_Data/cleaned/` for a file matching the brand + month. Use it if present.
2. **Raw exports:** check `03_Data/raw_exports/<YYYY-MM>/` for platform dumps.
3. **Live pull:** if connectors are authenticated, query Google Ads and Meta Ads for the month. Pull per-channel: spend, impressions, clicks, CTR, CPC, conversions, conversion value, CPA, ROAS. Pull the prior month too for comparison.
   - For Google Ads, pass the **exact month as `start_date`/`end_date`** (e.g. `start_date=2026-05-01`, `end_date=2026-05-31`). The connector supports any custom range, so you are not limited to presets like `LAST_MONTH` — pull whichever month or quarter was asked for, no matter how far back it is.
4. **Thribee live pull:** call `thribee_get_spend` (or `thribee_get_all_spend` for portfolio reviews) for the month and prior month. Thribee returns spend in native market currencies — convert to the house reporting currency using the currency map (UK=GBP, SE/AT=EUR, BR=BRL, all others=USD). Include in the blended and per-channel views.
5. **Fallback:** if no connector data is available, ask the user to paste the numbers.

Always record which source was used and the exact date range, and state it at the top of the report.

## Step 3 — Compute against the house standard

Using the KPI definitions and targets from account-conventions (and the brand's overrides):
- Month-over-month change for each metric (absolute and %).
- Actual vs. target for ROAS, CPA, conversion rate.
- Status flag per metric: on track / at risk / off track.
- Blended view across channels, plus per-channel breakdown.
- Convert everything to the house reporting currency.

## Step 4 — Analyze

- Top 3 wins (with the numbers) and a hypothesis for each.
- Top 3 problems (with the numbers) and a hypothesis for each.
- Notable shifts: a campaign or audience that moved materially MoM, creative fatigue (rising frequency + falling CTR), wasted spend signals (if large, recommend running `/wasted-spend-audit`).
- One non-obvious insight from the data.

## Step 5 — Write the report into the hub

1. Open the template `04_Reports/_templates/monthly-paid-review-template.md` (if missing, generate using the structure below and save it as the template for next time).
2. Fill it in.
3. Save to `04_Reports/monthly/` as `YYYY-MM-DD_<brand>_monthly-paid-review.md` (date = report run date).
4. Confirm the saved path to the user.

### Report structure

1. **Header** — brand, month, data source + date range, currency, attribution window.
2. **Executive summary** — 3 sentences: headline result, biggest win, biggest concern.
3. **KPI dashboard** — table: Metric | This month | Prior month | MoM change | Target | Status.
4. **Per-channel breakdown** — Google Ads, Meta Ads, and Thribee each, same metric set. For Thribee, report spend and available metrics; note any gaps (Thribee is spend-focused; conversion data comes from Google/Meta).
5. **What worked** — 3 wins + hypotheses.
6. **What needs fixing** — 3 problems + hypotheses + recommended fix.
7. **Recommendations** — prioritized by impact × effort; mark each immediate / next month / later.
8. **Next month focus** — top 3 priorities + any tests to run.

## Step 6 — Offer follow-ups

Ask whether to: draft a Slack/email summary for the team, run a wasted-spend audit, build a slide-ready version, or set up the scheduled data pull so next month's data is already in `03_Data/`.
