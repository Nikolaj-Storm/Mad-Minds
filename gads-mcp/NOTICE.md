# NOTICE — self-hosted Google Ads MCP

This `gads-mcp/` server is adapted from the internal **OnlineMinds local Google Ads MCP** (the `google_ads_to_claude` package). The **tool logic is unchanged** (`campaigns.py`, `performance.py`, `ads.py`, `keywords.py` — list/pause/enable/budget, performance, search terms, ad groups, create RSA, keyword bids). Two things were changed to make it a **remote, multi-user** connector like `gsc-mcp/`:

1. **Auth → per-user OAuth proxy.** `client.py:get_client()` no longer loads a static `google-ads.yaml` refresh token. It builds a `GoogleAdsClient` per request from:
   - the **caller's own Google access token** (FastMCP Google OAuth-proxy — each marketer signs in with their own account, so they only touch accounts they already have), plus
   - a server-side **developer token** (`GOOGLE_ADS_DEVELOPER_TOKEN`) — one for the whole org, set as a Fly secret, and
   - an optional `GOOGLE_ADS_LOGIN_CUSTOMER_ID` (manager account) for MCC access.
2. **Transport → remote HTTP** via `server.py` (FastMCP `GoogleProvider`, `adwords` scope, DiskStore persistence, `require_authorization_consent=False`, always-on machine) — identical pattern to `gsc-mcp/`.

## Safety
- `READONLY_MODE` (fly.toml `[env]`, default **"true"**) makes all write tools **simulate** — they report what they would change without touching Google Ads. Flip to `"false"` only when you're ready for real writes.
- Real writes are *additionally* gated by the **/ad-actions Tier 1 / Tier 2 spend-gate** in Mad Minds (typed accept-phrase for spend increases).

## Verified (sandbox)
Boots on `fastmcp 2.14.7` + `google-ads 31`; `/health` 200; OAuth metadata advertises `/authorize`, `/token`, `/register` (DCR) and PKCE `S256`; `adwords` scope present; `/mcp` returns 401 without a token. `GoogleAdsClient` constructs from an access-token credential + developer token.

## NOT verified here (needs the real dev token + a live account)
The actual Google Ads API calls (GAQL reads, mutates). The auth plumbing is correct; confirm live once a **Basic Access** developer token is in place — expect a short debug pass like GSC had.

See `GADS-SELF-HOST-RUNBOOK.md` for deployment.
