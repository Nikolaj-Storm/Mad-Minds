# Connectors — OnlineMinds Marketing

## How tool references work
Skills describe workflows by capability (paid ads, SEO, analytics, tracking), not by vendor. Each marketer authorizes their own accounts on first use — there is no shared credential.

## Two kinds of connectors

### A. Native Claude desktop connectors — enabled per marketer in the Connectors UI
These come from Anthropic's built-in connector catalog. The plugin does **not** pre-wire URLs for them; the marketer adds each one through **Customize → Connectors → (pick connector) → Connect** and OAuths their own account. The plugin's skills detect them at runtime.

| Capability | Connector to enable | Notes |
|---|---|---|
| Mad Minds Drive Hub | Google Drive | Read/write the shared Hub. Sign in with an `@onlineminds.io` account. |
| Google Ads | Google Ads | **Write-capable.** Reads + campaign mutate / budget / bid / negatives / create campaigns and ads. Spend-gate (Tier 1/2) applies. |
| Meta Ads | Meta Ads | **Write-capable.** Create/update/pause campaigns, budgets, ads/creatives across Facebook + Instagram. |
| Web analytics | Google Analytics (GA4) | Read-only sessions, conversions, funnel data. |
| Organic search | Google Search Console | Clicks, impressions, positions per query/page. |
| Tracking config | Google Tag Manager | **Write-capable.** Read tags/triggers/variables, create/edit, publish container versions. Conversion-tracking changes are Tier 1 (bad tracking = fake spend signals). |

### B. Vendor-native MCPs — pre-wired in the plugin's `.mcp.json`
These don't live in Anthropic's catalog (yet); the plugin points directly at the vendor's hosted MCP. Each marketer authorizes once (API key or vendor OAuth) on first use.

| Capability | Server in .mcp.json | Notes |
|---|---|---|
| SEO + AI citability | Ahrefs (`api.ahrefs.com/mcp/mcp`) | Keywords, backlinks, site audits, Brand Radar (AI mentions/GEO). Already in use at OnlineMinds. |
| Competitive traffic | SimilarWeb (`mcp.similarweb.com`) | Traffic estimates, market benchmarking. |
| Knowledge base | Notion (`mcp.notion.com/mcp`) | Optional. If briefs/playbooks live in Notion. |
| Product/usage data | Supabase (`mcp.supabase.com/mcp`) | Already in use. Portfolio-site data. |
| Deployments / crons | Vercel (`mcp.vercel.com`) | Already in use; inspect the scheduled data-pull jobs. |
| Team sharing | Slack (`mcp.slack.com/mcp`) | Optional. Remove if not used. |

## Onboarding flow
The `/setup-marketing` skill walks each marketer through both lists in order:
1. Google Drive (mandatory — needed to reach Mad Minds)
2. Google Ads, Meta Ads (mandatory for paid-media skills)
3. GA4, Search Console, GTM (recommended)
4. Ahrefs, SimilarWeb (recommended for SEO + competitive skills)
5. Notion, Slack, Supabase, Vercel (optional)

## Per-user auth
Every connector uses per-user OAuth (or per-user API key). Claude acts as the authenticated marketer — it can only touch ad accounts, GA4 properties, GTM containers, etc. that person already has access to in real life. There is no shared service account.

## Write safety
All write actions (Google Ads, Meta Ads, Google Tag Manager) are gated by the rules in `account-conventions`. Spend-increasing actions and tracking changes that affect conversion counts (Tier 1) require the user to type a verbatim accept-phrase (e.g. `I wish to increase the ad spending on rentumo.ie by $500`); the gate is non-overridable. Non-spend writes (Tier 2) require explicit confirmation. Every change shows its reversal and is logged to `06_Automation_Outputs/logs/`. Pair with platform-level spend caps for a hard backstop. No machine-to-machine auto-execution.
