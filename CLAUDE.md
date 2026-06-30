# CLAUDE.md — onlineminds-marketing repo (admin maintenance)

This file is auto-loaded by Cowork when the **maintainer** opens this repo as a project. It is NOT loaded for marketers — they install the plugin from Mad Minds Drive and never see this file.

## What this repo is

This is the **Mad Minds marketplace** — a single GitHub repo that ships two Claude plugins to OnlineMinds marketers:

1. **`onlineminds-marketing/`** — the in-house plugin. Skills, the Mad Minds Drive Hub routing, write-action safety gates, OnlineMinds-specific brand voice and KPI conventions.
2. **`claude-ads/`** — a vendored copy of AgriciDaniel/claude-ads (MIT) for deep paid-advertising audits. See `claude-ads/NOTICE.md` for the upstream commit and attribution. Update via `scripts/sync-claude-ads.sh`.

Marketers paste this one repo URL into Claude desktop and get both plugins. They do not clone or read this repo.

The plugins read from and write to the shared **Mad Minds** Google Drive Hub. The write-capable ad-platform connectors are **per-user OAuth**. Google Drive is in Claude desktop's built-in catalog; **Google Search Console, Google Ads, and Meta Ads are self-hosted MCPs in this repo** (`gsc-mcp/`, `gads-mcp/`, `meta-ads-mcp/`), added as custom connectors — Meta runs as **two connectors**, one per business area (onlineminds.io + Rentumo ApS). Two read-only self-hosted MCPs use a **shared server-side bearer** instead and are pre-wired in `.mcp.json` (no marketer Connect step): Thribee (ad spend) and **Rentumo Trials** (`rentumo-trials-mcp/` — new-subscriber/trial counts **and revenue/chargeback KPIs** per Rentumo market; money is in each market's local currency, so it's never summed across markets). A third pre-wired read-only MCP, **Rentumo Conversions** (`rentumo-conversions-mcp/`), needs **no auth at all** — it reads two **public** S3 feeds per market (`kuhamia` bucket): a first/last-touch UTM **attribution** feed and a Google Ads **offline-conversions** feed (with per-market-currency conversion value + a hashed email that is never returned). It is **Rentumo-brand-only** (not Adsumo/Printumo/Bidumo/Monetumo/Photumo/JLA) and is where channels like **Lifull-connect** surface as a `utm_source`; all tool output is aggregated. Plus pre-wired vendor MCPs (Supabase, Vercel, Slack — in `onlineminds-marketing/.mcp.json`). **Notion, Ahrefs, and AirOps are deliberately excluded** — Notion was removed from `.mcp.json`, Ahrefs/AirOps are not wired by this repo, and the plugin's `account-conventions` skill carries a non-overridable "Excluded connectors — never use" rule so Mad Minds won't touch them even if a marketer has them connected at the Claude-desktop level. GA4 / Tag Manager / Merchant Center aren't wired yet, and **Composio is not used** (an earlier draft did; removed).

## Anti-guessing rule

Do NOT add interpretive descriptions of OnlineMinds brands, markets, KPIs, or strategy unless the maintainer has explicitly provided them. Empty `[FILL IN]` slots in `account-conventions/SKILL.md` and elsewhere should stay empty until real values are pasted in. Speculative content (guessed brand descriptions, market lists, KPI targets) leaks into every skill output and produces bad work for the team.

## Maintenance workflow

- **Skill edits to `onlineminds-marketing/`** → bump the `onlineminds-marketing` `version` in both `.claude-plugin/marketplace.json` and `onlineminds-marketing/.claude-plugin/plugin.json` → commit + push.
- **Update vendored `claude-ads/` from upstream** → run `bash scripts/sync-claude-ads.sh` → review the diff → bump the `claude-ads` `version` in `.claude-plugin/marketplace.json` to match upstream → commit + push.
- **Self-hosted connector changes** (`meta-ads-mcp/`, `gads-mcp/`, `gsc-mcp/`) → redeploy the server (not a plugin version bump). All three now run on the **Hetzner box** (`<maintainer>@<box-ip>`, "<box-hostname>", rootless Docker) as Docker Compose services behind **Tailscale Funnel**: Meta is `mcp-stack/compose.yaml` (project `madminds-mcp`, hosts `meta-onlineminds`/`meta-rentumo`); Google Ads + GSC are `mcp-stack/compose.google.yaml` (project `madminds-google`, hosts `gads`/`gsc`, each its own container + tunnel sidecar, disk-backed token storage at `CLIENT_STORAGE_DIR=/data`); **Rentumo Trials** is `mcp-stack/compose.rentumo.yaml` (project `madminds-rentumo`, host `rentumo-trials`, read-only, no OAuth — the only config is the shared `RENTUMO_BEARER_TOKEN` in `rentumo.env`; the 26 market domains are bundled in the image at `rentumo-trials-mcp/src/rentumo_trials_mcp/markets.json`, overridable via `RENTUMO_MARKETS_FILE`); **Rentumo Conversions** is `mcp-stack/compose.conversions.yaml` (project `madminds-conversions`, host `rentumo-conversions`, **Rentumo-brand-only**, read-only, **no auth/secret at all** — it reads public S3 feeds; the 26 market codes + feed slugs are bundled at `rentumo-conversions-mcp/src/rentumo_conversions_mcp/markets.json`, overridable via `RENTUMO_CONV_MARKETS_FILE`, and feed location/naming is overridable via `RENTUMO_CONV_FEED_BASE_URL`/`RENTUMO_CONV_UTM_TEMPLATE`/`RENTUMO_CONV_OFFLINE_TEMPLATE`). Redeploy with `cd ~/Mad-Minds/mcp-stack && git pull && docker compose -f <file> up -d --build` — use the right `-f`/project so you don't recreate the others. Each server also ships a `Dockerfile` and a `vercel.json` + `api/index.py` (Vercel serverless alternative, Redis/KV token storage). Keep `meta-ads-mcp` analysis+write parity with `gads-mcp`, and never weaken the `READONLY_MODE` / `/ad-actions` gating. If a connector's public URL changes, bump the plugin version and update the `_custom_connectors_note` in `onlineminds-marketing/.mcp.json` + CONNECTORS.md so marketers get the new URL.
- **Boundary rule** (enforce when editing skills): `claude-ads` is analysis-only. Live ad-account writes go through `/ad-actions` in `onlineminds-marketing`, which applies the Tier 1 / Tier 2 spend-gate. Don't add write capabilities to the vendored copy; that's drift from upstream and bypasses the gate.
- The Tier 1 / Tier 2 spend-gate rules in `account-conventions` are non-overridable. Do not weaken them when editing other skills.

## Key references

- Mad Minds Drive Hub: https://drive.google.com/drive/folders/1aLu66XMaCKptC3GEYql20tHsbzDUCCpN
- Plugin repo (this one): https://github.com/Nikolaj-Storm/Mad-Minds
- Marketer onboarding doc: `EMPLOYEE-ONBOARDING.md`
- Admin setup doc: `SETUP.md`
- Connector inventory: `onlineminds-marketing/CONNECTORS.md`
- Self-hosted connector deploy: `META-SELF-HOST-RUNBOOK.md` + `mcp-stack/README.md` (Meta); `GADS-SELF-HOST-RUNBOOK.md`, `GSC-SELF-HOST-RUNBOOK.md`, `RENTUMO-TRIALS-SELF-HOST-RUNBOOK.md`, `RENTUMO-CONVERSIONS-SELF-HOST-RUNBOOK.md`
