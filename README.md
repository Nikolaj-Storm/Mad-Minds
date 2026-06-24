# Mad Minds — OnlineMinds Marketing Marketplace

A Claude plugin marketplace for the OnlineMinds marketing department. Paste this repo URL once into Claude desktop, get two plugins:

| Plugin | What it does |
|---|---|
| **`onlineminds-marketing`** | In-house skills for the OnlineMinds brands (Rentumo, Adsumo, Printumo, Bidumo, Monetumo, Photumo, Jacob Lund Art). Reads/writes the Mad Minds Google Drive Hub. Includes `/ad-actions` — the **only** skill that touches live ad accounts, behind a non-overridable Tier 1 / Tier 2 typed-phrase spend-gate. |
| **`claude-ads`** | Vendored copy of [AgriciDaniel/claude-ads](https://github.com/AgriciDaniel/claude-ads) (MIT). 250+ paid-advertising audit checks across Google, Meta, YouTube, LinkedIn, TikTok, Microsoft, Apple, Amazon. Health Score 0-100. Industry templates. PDF reports. **Analysis-only.** |

## Install (for marketers)

In Claude desktop → Customize → Plugins → **+ Add marketplace** → **From repository** → paste:

```
https://github.com/Nikolaj-Storm/Mad-Minds
```

Install **both** plugins when prompted. Then open Cowork and type `/setup-marketing`.

See [`EMPLOYEE-ONBOARDING.md`](./EMPLOYEE-ONBOARDING.md) for the full walkthrough.

## Connectors

Every connector is **per-user OAuth** — Claude acts as the signed-in marketer and only ever touches accounts that person already has. `/setup-marketing` walks marketers through connecting them.

| Capability | How to add it | Sign in with |
|---|---|---|
| Mad Minds Drive Hub | Built-in Connectors catalog → **Google Drive** | `@onlineminds.io` |
| Google Search Console | Add custom connector → `https://gsc.tail40453d.ts.net/mcp` | Google |
| Google Ads | Add custom connector → `https://gads.tail40453d.ts.net/mcp` | Google |
| Meta Ads — onlineminds.io | Add custom connector → `https://meta-onlineminds.tail40453d.ts.net/mcp` | Facebook |
| Meta Ads — Rentumo | Add custom connector → `https://meta-rentumo.tail40453d.ts.net/mcp` | Facebook |

Google Ads, Search Console, and Meta Ads are **self-hosted** in this repo (`gads-mcp/`, `gsc-mcp/`, `meta-ads-mcp/`). Meta runs as **two connectors** because OnlineMinds has two Meta business areas (onlineminds.io + Rentumo ApS); add the one(s) you manage. GA4 / Tag Manager / Merchant Center aren't wired yet. (No Composio — an earlier draft used it; removed.)

## Repo layout

```
.claude-plugin/marketplace.json   ← lists both plugins
onlineminds-marketing/            ← in-house plugin
  .claude-plugin/plugin.json
  .mcp.json                       ← vendor-native MCPs (Notion, Supabase, etc.)
  skills/                         ← 9 skills incl. /ad-actions, /setup-marketing
  CONNECTORS.md                   ← the live connector list + auth model
claude-ads/                       ← vendored upstream plugin (MIT)
  ads/, agents/, skills/, scripts/, LICENSE, NOTICE.md
gsc-mcp/  gads-mcp/  meta-ads-mcp/ ← self-hosted connector servers (FastMCP, per-user OAuth)
mcp-stack/                        ← Docker Compose stack to run the MCPs on a VPS (Tailscale Funnel)
scripts/sync-claude-ads.sh        ← refresh vendored copy from upstream
SETUP.md                          ← maintainer setup (one-time)
EMPLOYEE-ONBOARDING.md            ← marketer onboarding
{GSC,GADS,META}-SELF-HOST-RUNBOOK.md ← deploy guides for the self-hosted connectors
COWORK-SETUP-RUNBOOK.md, BUILD-HUB-RUNBOOK.md
```

## Self-hosted connectors (maintainer)

Google Ads, Search Console, and Meta Ads run as small [FastMCP](https://gofastmcp.com) servers in this repo, so there's no per-marketer API-key or developer-token setup — each marketer just signs in with their own Google/Facebook account.

- **Google Search Console / Google Ads** — on our Hetzner box via [`mcp-stack/compose.google.yaml`](./mcp-stack/) (Docker Compose + Tailscale Funnel, each its own container). See [`GSC-SELF-HOST-RUNBOOK.md`](./GSC-SELF-HOST-RUNBOOK.md) / [`GADS-SELF-HOST-RUNBOOK.md`](./GADS-SELF-HOST-RUNBOOK.md).
- **Meta Ads** — on the same box via [`mcp-stack/compose.yaml`](./mcp-stack/) (Tailscale Funnel, no domain/root needed). Deploy guide: [`META-SELF-HOST-RUNBOOK.md`](./META-SELF-HOST-RUNBOOK.md); server internals: [`meta-ads-mcp/NOTICE.md`](./meta-ads-mcp/NOTICE.md).

All writes are gated by the `/ad-actions` Tier 1 / Tier 2 spend-gate **and** a server-side `READONLY_MODE` flag that simulates writes until you flip it.

## Boundary between the two plugins

`claude-ads` is **analysis-only**. To act on its findings, use `/ad-actions` in `onlineminds-marketing` — the spend-gate enforces safety. The natural pattern:

1. `/ads audit` — get the 250-check audit with Health Score
2. `/ad-actions <brand> <change>` — apply the fixes, with the typed-phrase confirmation for anything that spends money

## Updating

- **In-house edits** to `onlineminds-marketing/`: edit, bump that plugin's `version` in `.claude-plugin/marketplace.json` and `onlineminds-marketing/.claude-plugin/plugin.json`, commit + push.
- **Sync `claude-ads/` from upstream**: `bash scripts/sync-claude-ads.sh`, review diff, bump that plugin's `version` in `.claude-plugin/marketplace.json` to the new upstream version, commit + push.

## License

The `onlineminds-marketing/` plugin is proprietary to OnlineMinds ApS. The `claude-ads/` plugin is MIT-licensed by AgriciDaniel — see `claude-ads/LICENSE` and `claude-ads/NOTICE.md`.
