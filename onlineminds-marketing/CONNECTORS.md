# Connectors — OnlineMinds Marketing

## How tool references work
Skills describe workflows by capability (paid ads, SEO, analytics, tracking), not by vendor. Each marketer authorizes their own accounts on first use — there is no shared credential.

## Two kinds of connectors

### A. Plugin-pre-wired MCPs (`.mcp.json`)
These load automatically when the `onlineminds-marketing` plugin installs. Each one shows up under **Customize → Onlineminds-marketing → Connectors** in Claude desktop with a **Connect** button. Marketer clicks Connect, runs through the OAuth flow on first use, then it works in every Cowork session.

| Capability | Server (in .mcp.json) | Auth model | Notes |
|---|---|---|---|
| Google Ads | Composio Google Ads | Per-user OAuth via Composio | **Write-capable.** GAQL reads + Mutate Campaigns / budget / bid / negatives / create ads. Token-free (Composio provisions the dev token). Tier 1/2 spend-gate applies. |
| Meta Ads | Composio Meta Ads | Per-user OAuth via Composio | **Write-capable.** Create/update/pause campaigns, budgets, ads/creatives. Facebook + Instagram. |
| GA4 | Composio Google Analytics | Per-user OAuth | Read-only sessions, conversions, funnel data. |
| Google Search Console | Composio GSC | Per-user OAuth | Organic clicks/impressions/positions per query/page. |
| Google Tag Manager | Composio GTM | Per-user OAuth | **Write-capable.** Read/edit tags/triggers/variables, publish containers. Conversion-tracking changes are Tier 1 (bad tracking = fake spend signals). |
| Google Merchant Center | Composio Merchant Center | Per-user OAuth | **Write-capable.** Feed health, product attributes, supplemental feeds, promotions. Only relevant for brands running Shopping/PMax with a product feed. Tier 2 for most edits; Tier 1 when enabling new spend or publishing promotions. ⚠️ Verify URL against your Composio account; if missing, swap to the official Google Content API. |
| Ahrefs | Vendor MCP (`api.ahrefs.com`) | Org API key | SEO keyword research, backlinks, site audits, Brand Radar (AI mentions/GEO). |
| SimilarWeb | Vendor MCP (`mcp.similarweb.com`) | Org API key | Competitive traffic, market benchmarking. |
| Notion | Vendor MCP | Per-user OAuth | Optional. Briefs/playbooks if you keep them in Notion. |
| Supabase | Vendor MCP | Per-user / org | Already in use. Portfolio-site data. |
| Vercel | Vendor MCP | Per-user / org | Already in use. Deployment + scheduled-job inspection. |
| Slack | Vendor MCP | Per-user OAuth | Optional. Share finished reports. |

### B. Native Claude desktop catalog
Claude desktop's built-in **Customize → Connectors** (the top-level one, not the per-plugin one). For OnlineMinds we use exactly one connector from here:

| Capability | Connector | Notes |
|---|---|---|
| Mad Minds Drive Hub | Google Drive | Read/write the shared Hub. Sign in with `@onlineminds.io`. |

> Why not also put Google Ads/Meta/GA4/GSC/GTM/Merchant Center in this catalog? Because on individual Pro/Max seats they aren't in the built-in catalog. Pre-wiring them via `.mcp.json` (group A above) is how we deliver them to every marketer with zero config on their end.

## Onboarding flow
The `/setup-marketing` skill walks through both lists in order:
1. **Native:** Google Drive (mandatory — needed for Mad Minds)
2. **Plugin-prewired (Composio):** Google Ads + Meta Ads (mandatory for paid skills) → GA4, Search Console, Tag Manager (recommended) → Merchant Center (only for Shopping/PMax brands)
3. **Plugin-prewired (vendor):** Ahrefs, SimilarWeb (recommended for SEO + competitive)
4. **Optional:** Notion, Slack, Supabase, Vercel

## Composio account requirement
The Composio-hosted MCPs in group A require a **Composio account** (free at composio.dev). Sign up once at the org level; each marketer authorizes their own Google/Meta accounts through Composio's OAuth flow on first use. No developer-token application required (Composio provisions Google Ads, etc.).

If Composio is ever missing a specific action OnlineMinds needs, swap the URL to:
- **Google Ads:** Pipeboard (`pipeboard.co`) — also hosted, also token-free
- **Meta Ads:** Adspirer (`adspirer.com`)
- **Merchant Center:** Google Content API directly

## Per-user auth
Every connector uses per-user OAuth (or per-user API key). Claude acts as the authenticated marketer — it can only touch ad accounts, GA4 properties, GTM containers, etc. that person already has access to in real life. There is no shared service account.

## Write safety
All write actions (Google Ads, Meta Ads, Google Tag Manager, Merchant Center) are gated by the rules in `account-conventions`. Spend-increasing actions and tracking changes that affect conversion counts (Tier 1) require the user to type a verbatim accept-phrase (e.g. `I wish to increase the ad spending on rentumo.ie by $500`); the gate is non-overridable. Non-spend writes (Tier 2) require explicit confirmation. Every change shows its reversal and is logged to `06_Automation_Outputs/logs/`. Pair with platform-level spend caps for a hard backstop. No machine-to-machine auto-execution.
