# Connectors — OnlineMinds Marketing

## How tool references work
Skills describe workflows by capability (paid ads, SEO, analytics, tracking), not by vendor. Each marketer authorizes their own accounts on first use — there is no shared credential.

## Why not Composio (the thing we changed)
The earlier wiring pointed every Google/Meta connector at guessed Composio URLs (`https://mcp.composio.dev/<toolkit>/mcp`). That cannot work from Claude desktop, for two reasons:

1. **Those URLs were invented.** Real Composio MCP endpoints are generated per-server in the Composio dashboard (`https://apollo.composio.dev/v3/mcp/<UUID>` or `https://backend.composio.dev/v3/mcp/<SERVER_ID>?user_id=<USER_ID>`), not derived from a toolkit name.
2. **Composio authenticates with an `x-api-key` header, but Claude desktop's Connect button only does OAuth** — its connector UI has no field for an API key or custom header (anthropics/claude-ai-mcp #112). So even a correct Composio URL can't be authorized from the Connect button a marketer uses.

The symptom was the error `Couldn't register with <connector>'s sign-in service … add an OAuth Client ID` — a failed OAuth dynamic-client-registration against an endpoint that doesn't support it.

The fix: use connectors that natively speak Claude's remote-MCP OAuth flow, so the marketer clicks **Connect**, signs in with their own Google/Meta account, and is done — true per-user auth, which is what the spend-gate depends on.

## Two kinds of connectors

### A. Plugin-pre-wired MCPs (`.mcp.json`)
These load automatically when the `onlineminds-marketing` plugin installs. Each shows up under **Customize → Onlineminds-marketing → Connectors** with a **Connect** button. The marketer clicks Connect, runs the OAuth flow once, then it works in every Cowork session.

| Capability | Server (in `.mcp.json`) | Auth model | Notes |
|---|---|---|---|
| **Google Search Console** | Self-hosted `gsc-mcp/` on Fly (`onlineminds-gsc-mcp.fly.dev`) | Per-user Google OAuth (sign-in link) | **Live.** Organic clicks/impressions/positions, URL inspection, sitemaps. Read-only. Each marketer signs in with their own Google account (Internal app, auto-trusted by Workspace). Persistent — sign in once. |
| Competitive traffic | SimilarWeb (`mcp.similarweb.com`) | Org API key | Market benchmarking. |
| Notion | Vendor MCP | Per-user OAuth | Optional. Briefs/playbooks. |
| Supabase | Vendor MCP | Per-user / org | Already in use. Portfolio-site data. |
| Vercel | Vendor MCP | Per-user / org | Already in use. Deployment + scheduled-job inspection. |
| Slack | Vendor MCP | Per-user OAuth | Optional. Share finished reports. |

### B. Native Claude desktop catalog
Claude desktop's built-in **Customize → Connectors** (the top-level one, not the per-plugin one). For OnlineMinds we use exactly one connector from here:

| Capability | Connector | Notes |
|---|---|---|
| Mad Minds Drive Hub | Google Drive | Read/write the shared Hub. Sign in with `@onlineminds.io`. |

## Pending connectors (not yet wired — block on these before team rollout)
These live under `_pending_connectors` in `.mcp.json`. **We deliberately did not ship guessed URLs for them.** Each needs a verified OAuth MCP endpoint — one a marketer can authorize from the Connect button — chosen and tested before it goes to the team.

| Capability | Status | Plan |
|---|---|---|
| GA4 (Google Analytics) | Needs a verified OAuth MCP | Evaluate a managed GA4 MCP with built-in OAuth (candidates: Cogny, Stape) or self-host `google-analytics-mcp` and register an OAuth client ID in the connector's Advanced settings. Read-only. |
| Google Search Console | **Self-host ready** (deploy, then wire) | Direct per-user GSC connector via the **corrected, vendored** server at `gsc-mcp/` (FastMCP Google **OAuth-proxy**; from damupi/mcp-gsc-oauth with 3 tested-and-fixed defects — see `gsc-mcp/NOTICE.md`) on Fly.io. Maintainer hosts it once and holds the Google secret server-side; marketers just click **Connect → sign in with Google**, nothing to paste. Per-user, read-only, only their own properties. Steps in `GSC-SELF-HOST-RUNBOOK.md`. |
| Google Tag Manager | Needs a verified OAuth MCP | **Tier-1 tracking edits depend on this.** No Connect-button OAuth MCP confirmed yet; until one is wired and tested, GTM writes via `/ad-actions` stay unavailable. Do not roll out GTM writes until verified. |
| Google Merchant Center | Needs a verified OAuth MCP | Feed brands only. Fallback: official Google Content API via a self-hosted MCP with an Advanced-settings OAuth client ID. |

> Why not put these in the native Claude desktop catalog instead? On individual Pro/Max seats they aren't in the built-in catalog. The Connect-button MCP approach above is how we deliver per-user connectors with no per-marketer dashboard work.

## Onboarding flow
The `/setup-marketing` skill walks through the lists in order:
**Live today (what setup walks through):**
1. **Native:** Google Drive (mandatory — needed for Mad Minds)
2. **Self-hosted (live):** Google Search Console — per-user Google sign-in link, no panel install
3. **Plugin-prewired (vendor):** SimilarWeb (competitive)
4. **Optional:** Notion, Slack, Supabase, Vercel

**Coming (NOT part of setup yet):**
- **Meta Ads** — Meta's official MCP, per-Business-Manager URL + Meta Business sign-in (see below). Awaiting the URL(s).
- **Google Ads** — blocked on an org approval (dev token or Workspace allowlist).
- **GA4 / Google Tag Manager / Merchant Center** — not wired.

## Meta Ads — official MCP, per company
Meta Ads uses **Meta's own official MCP** (free beta), authenticated via **Meta Business OAuth (Facebook)** — not Google, so the Workspace third-party-app block doesn't apply. A Business admin authorizes at Meta's "Connect to AI tool" page and copies the unique MCP URL Meta provisions for that Business account. Because OnlineMinds runs **multiple Business Managers**, each company provisions its own URL and is wired as its own connector (`meta-ads-<company>`). Per-user: each marketer signs in with their own Meta account and only sees ad accounts they can access.

## Google Ads — parked (no self-serve path)
Every Google Ads option needs either a developer token (self-host / Google's official MCP) **or** a Google Workspace allowlist for a third-party app. Neither is grantable without an admin, so Google Ads stays disconnected. Interim: run `claude-ads` audits on exported Google Ads data.

## Per-user auth
Every connector uses per-user OAuth (or per-user API key). Claude acts as the authenticated marketer — it can only touch ad accounts, GA4 properties, GTM containers, etc. that person already has access to in real life. There is no shared service account.

## Write safety
All write actions (Google Ads, Meta Ads, and — once wired — Google Tag Manager, Merchant Center) are gated by the rules in `account-conventions`. Spend-increasing actions and tracking changes that affect conversion counts (Tier 1) require the user to type a verbatim accept-phrase (e.g. `I wish to increase the ad spending on rentumo.ie by $500`); the gate is non-overridable. Non-spend writes (Tier 2) require explicit confirmation. Every change shows its reversal and is logged to `06_Automation_Outputs/logs/`. Pair with platform-level spend caps for a hard backstop. No machine-to-machine auto-execution.
