# NOTICE — self-hosted Meta (Facebook/Instagram) Ads MCP

This `meta-ads-mcp/` server is the Meta counterpart of `gads-mcp/`. It is the
in-house Meta Ads connector for Mad Minds: a remote HTTP MCP server, **per-user
Facebook OAuth**, that exposes reporting + safe management of Meta ad accounts
and routes every write through the `/ad-actions` spend-gate.

It is **not** a vendored third party (unlike `claude-ads/`). It was built to
mirror `gads-mcp/` so Meta behaves exactly like Google Ads in Mad Minds: same
READONLY safety flag, same `handle_errors` shape, same Tier 1 / Tier 2 gate, the
same one-Connect-and-done custom-connector delivery. It replaces the earlier
approach of wiring Meta's official hosted MCP (`mcp.meta.com/ads/<business-id>`)
per Business Manager.

## How it works

1. **Auth → per-user Facebook OAuth proxy** (`facebook_provider.py`). FastMCP has
   no built-in Facebook provider, so `FacebookProvider` subclasses FastMCP's
   generic `OAuthProxy` with Facebook's OAuth endpoints, and `FacebookTokenVerifier`
   validates the opaque user token via Meta's Graph `debug_token`. Each marketer
   signs in with their **own Facebook account**, so they only touch ad accounts
   they already manage — there is no shared service account. One Facebook **App
   ID + App Secret** is the server-side secret (one app for the whole org).

2. **Long-lived tokens.** Facebook's code exchange returns a ~1-hour token and
   **no refresh token**. `FacebookProvider.exchange_authorization_code` swaps it
   for a ~60-day long-lived token (`grant_type=fb_exchange_token`) before it is
   stored, so marketers re-Connect roughly every 60 days rather than hourly. The
   swap is idempotent and fails closed to the short-lived token.

3. **Transport → remote HTTP** via `server.py` (FastMCP, DiskStore persistence so
   sign-in survives restarts, always-on container). Tools build a **fresh**
   `FacebookAdsApi` per request from the caller's token (never the SDK global
   singleton — that would leak one user's token into another's concurrent
   request).

## Tools

Reporting + listing: `list_ad_accounts`, `server_status`, `get_campaigns`,
`get_ad_sets`, `get_ads`, `get_performance` (Insights; any date range).
Writes (READONLY-gated): `pause_entity`, `enable_entity`, `update_budget`
(campaign or ad-set, daily or lifetime).

Meta has no keywords or search-terms report (so no `get_keywords` /
`get_search_terms` analogue), and ad **creation** is intentionally omitted in
this version — a Meta ad needs a Page-linked creative + asset hashes, too much
to do safely as one tool today.

## Safety

- `READONLY_MODE` (default **"true"**) makes all write tools **simulate** — they
  report what they would change without touching Meta. Flip to `"false"` only
  when you're ready for real writes.
- Real writes are *additionally* gated by the **/ad-actions Tier 1 / Tier 2
  spend-gate** in Mad Minds (typed accept-phrase for spend increases).

## Verified (sandbox, no live Meta account)

Built and tested on `fastmcp 2.14.7` + `facebook-business 25.0.2`,
Python 3.11/3.12. 24 unit tests pass (time-range builder, account-id
normalization, money conversion, Insights param assembly). `FacebookProvider`
constructs against the real `OAuthProxy`; `debug_token` verification and the
short→long-lived token swap are unit-verified with mocked HTTP. All nine tools
register on the FastMCP server.

## NOT verified here (needs a real Facebook App + a live ad account)

The live Graph API calls (Insights reads, status/budget mutates) and the
end-to-end Facebook OAuth round-trip from Claude's Connect button. The plumbing
is correct; confirm live during the runbook's verify step — expect a short debug
pass like GSC/Google Ads had.

See `META-SELF-HOST-RUNBOOK.md` for deployment on a VPS with plain Docker.
