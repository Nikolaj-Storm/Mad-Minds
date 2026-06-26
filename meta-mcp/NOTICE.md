# NOTICE — self-hosted Meta (Facebook/Instagram) Ads MCP

This `meta-mcp/` server is the **Meta sibling of `gads-mcp/`**. It deliberately
mirrors that server's structure, conventions, and safety model so the two are
maintained the same way:

| Concern | gads-mcp | meta-mcp |
|---|---|---|
| Per-request client | `client.get_client()` (GoogleAdsClient) | `client.get_client()` (`GraphClient`) |
| Reporting | `performance.py` (GAQL) | `performance.py` (Insights edge) |
| Manage | `campaigns.py` pause/enable/budget | `campaigns.py` pause/enable/budget |
| Listing | campaigns / ad groups / keywords | campaigns / ad sets / ads |
| Safety flag | `READONLY_MODE` (writes simulate) | `READONLY_MODE` (writes simulate) |
| Date window | `build_date_filter` (GAQL `segments.date`) | `build_insights_params` (`date_preset` / `time_range`) |
| Error handling | `handle_errors` -> readable dict | `handle_errors` -> readable dict |

## Tool surface
Reads: `list_accounts`, `get_campaigns`, `get_ad_sets`, `get_ads`,
`get_performance`, `server_status`.
Writes (gated): `pause_entity`, `enable_entity`, `update_budget`.

## Where Meta differs meaningfully from Google Ads
These are intentional and called out in the code:

1. **Auth provider.** gads uses FastMCP's first-class `GoogleProvider`. FastMCP
   ships no first-class Meta/Facebook provider, so `auth.py` wires the generic
   `OAuthProxy` to Facebook's `dialog/oauth` + `oauth/access_token` endpoints and
   verifies tokens online via Graph `/debug_token`.
2. **Org secret = a Facebook App, not a developer token.** `META_APP_ID` /
   `META_APP_SECRET` are used only during the OAuth handshake — there is no
   per-call developer-token header like Google Ads has.
3. **Token longevity / no refresh tokens.** Facebook does not issue refresh
   tokens. A short-lived user token (~1–2h) is exchanged for a **long-lived user
   token (~60 days)**; after that the marketer reconnects. There is no silent
   indefinite refresh. (A **System User** token from Business Manager can be
   effectively non-expiring, but that is a *shared* credential and breaks the
   per-user model the spend-gate relies on, so we use per-user user tokens.)
4. **App Review / Business Verification.** `ads_management` (and `ads_read` for
   anyone who isn't an admin/dev/tester of the app) require Meta **App Review**
   with **Advanced Access**, which in turn requires **Business Verification**.
   Until then the app only works for users with a role on it — fine for a pilot,
   blocking for team rollout. This is the Meta analogue of Google's "Basic Access
   developer token" gate.
5. **Money units.** Meta amounts (budgets, spend) are **minor currency units**
   (e.g. cents/øre) — divide by 100. Google Ads uses micros (÷ 1,000,000).
6. **Budget location.** Google Ads budgets are always campaign-level. Meta budget
   lives on the campaign (Campaign Budget Optimization) **or** the ad set, so
   `update_budget` targets a node id at whichever level owns it.
7. **Conversions aren't one metric.** Insights returns an `actions` array;
   `performance.py` sums the conversion action types rather than reading a single
   `conversions` field.
8. **Ad-account id form.** Meta paths use `act_<id>`.

## Safety
- `READONLY_MODE` (default **"true"** in `.env.example` / compose) makes all write
  tools **simulate** — they report what they would change without touching Meta.
  Flip to `"false"` only when ready for real writes.
- Real writes are *additionally* gated by the **/ad-actions Tier 1 / Tier 2
  spend-gate** in Mad Minds (typed accept-phrase for spend increases).

## Deployment
Plain Docker (no Fly.io): `Dockerfile` + `docker-compose.yml` (named volume
`meta_data` for persisted sign-ins, env via `.env`). A TLS reverse proxy in front
provides the public HTTPS URL the custom connector needs. See
`../META-SELF-HOST-RUNBOOK.md`.

## Verified (sandbox, no live Meta credentials)
- **Dependency install + import.** `requirements.txt` installs cleanly and the
  server imports under real **FastMCP 2.14.7**; all **9 tools register**.
- **Auth construction.** With dummy app creds, `build_auth()` constructs a real
  `OAuthProxy` against Facebook's endpoints; `MetaTokenVerifier` subclasses
  FastMCP's `TokenVerifier` and exposes `required_scopes` (the OAuthProxy kwargs
  and the `mcp.server.auth.provider.AccessToken` import path are confirmed against
  the pinned version — an earlier `required_scopes=` kwarg bug was caught and
  fixed this way).
- **Graph wiring (live, auth-less).** `graph.facebook.com/v25.0` reachable;
  `/debug_token` and error responses return exactly the JSON the verifier and the
  `handle_errors` parser expect (error codes 190 / 2500 / 4 / 200 checked against
  real responses). v25.0 confirmed as the newest live Graph version.
- **Logic + safety.** `tests/` — **45 passing, no network**: the date/window
  builder, id/money helpers, Insights request assembly, every write tool's
  READONLY simulate path + validation, the Graph error parser, and cursor
  pagination. `ruff` clean.

## NOT verified here (needs a real app + live account)
The live Facebook OAuth handshake end-to-end and the actual authenticated Graph
reads/mutates (they need real `ads_read`/`ads_management` and an ad account). The
plumbing is constructed and exercised against real Graph error/`debug_token`
shapes; expect only a short debug pass like GSC/gads had once an approved app is
in place.
