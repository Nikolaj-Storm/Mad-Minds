# Meta Ads MCP — `get_conversion_lag` (attribution-window proxy)

**Status: code shipped to GitHub, deploy NOT yet verified live.** Date: 2026-08-13 ·
Owner: Nikolaj / OnlineMinds. See "Still open" at the bottom before treating this as done.

---

## 1. What this is, in one line

Adds a `get_conversion_lag` tool to `meta-ads-mcp` — the Meta counterpart to the Google
Ads MCP's `get_conversion_lag` — so Meta can get the same kind of "how much of a cohort's
conversions have already landed by day N" treatment that Google got on 2026-08-12. It is
**not the same kind of measurement** as the Google tool; see §3.

## 2. Why this needed a code change, not just a new pull

Google Ads exposes `segments.conversion_lag_bucket`, a true per-click day-by-day lag
histogram. Meta's Insights API has no equivalent segment — checked directly against the
existing `meta-ads-mcp` connector (`get_performance` has no breakdown parameter at all)
and confirmed via Meta's own Marketing API surface. The only lever Meta exposes is
`action_attribution_windows` on `AdAccount.get_insights()`, which changes **which actions
get credited** for a given click-through window, not a direct elapsed-time distribution.
Since the connector didn't support that parameter, there was no way to pull this without
adding a tool — so that's what this ships.

## 3. How it works, and what it is NOT

```
for each window in [1d_click, 7d_click, 28d_click]:
    pull get_insights(action_attribution_windows=[window], same date range)
    extract the count for one action_type (default "complete_registration")

pct_of_widest[window] = 100 * counts[window] / counts[widest_window]
```

`widest_window` (28d_click by default) is used as the denominator — Meta's best
available count, standing in for "eventual."

**Read this before trusting a number out of it:**

- **Coarse resolution.** Only 1d/7d/28d click (or view) windows exist. Google's tool has
  18 day-buckets out to day 240; this has 3 milestones, at most.
- **Not a strict lag distribution.** A wider attribution window can credit a *different*
  click entirely (someone who clicked two different ads on two different days), not just
  the same population converting later. Attribution-window growth and pure lag growth are
  correlated but not identical — this is a proxy, not a histogram.
- **28d_click is a ceiling, not "settled."** Unlike the house model's day-240 chain-ladder
  or even Google's day-45 native curve, there's no way to query further out. Treat
  `pct_of_widest` as "how much of the 28-day count had already showed up," not "how much
  of the eventual total."
- **Same date-window caveat as every other lag tool in this project:** filters by
  **click** date. A recent window under-reports every milestone simply because time
  hasn't passed yet.

**Bottom line:** this is real signal, worth having, but it's a materially weaker
instrument than what was built for Google on 2026-08-12. It should not be used to replace
Meta's house chain-ladder completion curve the way Google's was — see
`GOOGLE-NATIVE-COMPLETION-SPEC.md` for why that swap was justified for Google (day-45
settle vs day-240) and why the same argument does not hold here (no settle point to swap
to).

## 4. Interface

```python
get_conversion_lag(
    action_type: str = "complete_registration",  # Meta has no universal "conversions" field
    date_preset: str = "last_30d",
    account_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    windows: list[str] | None = None,             # default ["1d_click","7d_click","28d_click"]
) -> dict
```

Returns `{action_type, windows_requested, counts, widest_window, pct_of_widest, note}`.
`note` repeats the caveats above in the payload itself, so they survive even if a
downstream script only logs/stores the dict.

`action_type` defaults to `"complete_registration"`, matching the existing "META REP."
column convention elsewhere in this dashboard (see `platform-reported-conv.md` /
`DASHBOARD-ARCHITECTURE.md` §8d). **Not yet verified against every market's actual pixel
event name** — if a market's Meta pixel fires a different event for trial signups, this
tool will silently return zero counts for that market instead of erroring. Sanity-check
per account before trusting it.

## 5. What changed, where

| File | Change |
|---|---|
| `meta-ads-mcp/src/meta_ads_mcp/insights.py` | +113 lines: `get_conversion_lag`, `_ALLOWED_LAG_WINDOWS`, `_LAG_WINDOW_DAYS`, `DEFAULT_LAG_WINDOWS` |
| `meta-ads-mcp/src/meta_ads_mcp/server.py` | +2 lines: import + tool registration, same pattern as every other tool there |

No other files touched — `client.py` (and its `build_time_params`/`get_api`/
`resolve_account_id` helpers, which the new tool reuses) is untouched, so the existing
`tests/test_time_params.py` coverage is unaffected by this change. (`pytest` isn't
installed on the orchestrator box, so the suite wasn't actually re-run — worth doing from
a machine that has it, low risk given no shared code was touched.)

**Commit:** `b031a4b` — "meta-ads-mcp: add get_conversion_lag (attribution-window proxy
for days-to-conversion)", pushed to `Nikolaj-Storm/Mad-Minds` `main` from
`~/Documents/OM/Mad-Minds` on the Mac (the orchestrator box has no git identity/GitHub
credentials configured — a fresh commit attempt there failed with "Author identity
unknown"; the box's local copy still has an uncommitted, functionally-identical patch
sitting in its working tree from that failed attempt — reconcile it, see §7).

**Known minor nit:** the box's copy got a one-line cosmetic fix (blank line between
`get_performance` and the new function) via a manual `sed` before the failed commit; the
version that actually shipped from the Mac does **not** have that blank line — purely
cosmetic (PEP8 spacing), confirmed syntax-valid either way, not worth a second deploy
round-trip on its own.

## 6. Deploy mechanism

`meta-ads-mcp` has its own `vercel.json` and is its own Vercel project root (confirmed:
`gads-mcp` and `gsc-mcp` each have their own `vercel.json` too, all three living in the
same `Mad-Minds` monorepo). No local `.vercel` link exists on the orchestrator box, so
deployment is via Vercel's GitHub integration — pushing to `main` should trigger a rebuild
of both `meta-ads-rentumo` and `meta-ads-onlineminds` (they're two separate Vercel
projects/Facebook Apps pointed at the same `meta-ads-mcp/` root, one per Business
Manager).

## 7. Still open

1. **Deploy not verified.** Both Meta MCP connector instances were unreachable from the
   session that shipped this (pre-existing, unrelated to this change — confirmed down
   *before* any code was touched). Confirm via the Vercel dashboard (deployment
   triggered by commit `b031a4b`, build succeeded) or by calling `get_conversion_lag()`
   for real once a connector session is live.
2. **`action_type` default unverified per-market.** Confirm `"complete_registration"` is
   the actual pixel/CAPI event name Rentumo fires for trial signups on every market's
   Meta account — a silent zero is indistinguishable from "this market just converts
   less" without checking.
3. **Orchestrator box out of sync.** `~/Mad-Minds/meta-ads-mcp` on `mcp@37.27.23.202` has
   the same patch sitting uncommitted (never pushed — see §5). Reconcile with:
   ```bash
   ssh -i ~/.ssh/storm_om_new mcp@37.27.23.202 '
   cd ~/Mad-Minds/meta-ads-mcp
   git fetch origin
   git reset --hard origin/main
   rm -f meta_conversion_lag_patch.py src/meta_ads_mcp/*.bak*
   '
   ```
4. **No PR/review.** Shipped as a direct commit to `main`, matching the precedent set by
   `78e8d27 gads-mcp: add get_conversion_lag` (also a direct commit) rather than the
   PR-based pattern most other work in this repo uses. Worth a second pair of eyes given
   it's a shared connector other marketers use.
