# CLAUDE.md — onlineminds-marketing repo (admin maintenance)

This file is auto-loaded by Cowork when the **maintainer** opens this repo as a project. It is NOT loaded for marketers — they install the plugin from Mad Minds Drive and never see this file.

## What this repo is

This is the **Mad Minds marketplace** — a single GitHub repo that ships two Claude plugins to OnlineMinds marketers:

1. **`onlineminds-marketing/`** — the in-house plugin. Skills, the Mad Minds Drive Hub routing, write-action safety gates, OnlineMinds-specific brand voice and KPI conventions.
2. **`claude-ads/`** — a vendored copy of AgriciDaniel/claude-ads (MIT) for deep paid-advertising audits. See `claude-ads/NOTICE.md` for the upstream commit and attribution. Update via `scripts/sync-claude-ads.sh`.

Marketers paste this one repo URL into Claude desktop and get both plugins. They do not clone or read this repo.

The plugins read from and write to the shared **Mad Minds** Google Drive Hub. Live data comes from per-user OAuth connectors (Google Ads, Meta Ads, GA4, Search Console, Google Tag Manager, Google Drive — all via Claude desktop's native Connectors UI) and pre-wired vendor MCPs (Notion, Supabase, Vercel, Slack — in `onlineminds-marketing/.mcp.json`).

## Anti-guessing rule

Do NOT add interpretive descriptions of OnlineMinds brands, markets, KPIs, or strategy unless the maintainer has explicitly provided them. Empty `[FILL IN]` slots in `account-conventions/SKILL.md` and elsewhere should stay empty until real values are pasted in. Speculative content (guessed brand descriptions, market lists, KPI targets) leaks into every skill output and produces bad work for the team.

## Maintenance workflow

- **Skill edits to `onlineminds-marketing/`** → bump the `onlineminds-marketing` `version` in both `.claude-plugin/marketplace.json` and `onlineminds-marketing/.claude-plugin/plugin.json` → commit + push.
- **Update vendored `claude-ads/` from upstream** → run `bash scripts/sync-claude-ads.sh` → review the diff → bump the `claude-ads` `version` in `.claude-plugin/marketplace.json` to match upstream → commit + push.
- **Boundary rule** (enforce when editing skills): `claude-ads` is analysis-only. Live ad-account writes go through `/ad-actions` in `onlineminds-marketing`, which applies the Tier 1 / Tier 2 spend-gate. Don't add write capabilities to the vendored copy; that's drift from upstream and bypasses the gate.
- The Tier 1 / Tier 2 spend-gate rules in `account-conventions` are non-overridable. Do not weaken them when editing other skills.

## Key references

- Mad Minds Drive Hub: https://drive.google.com/drive/folders/1aLu66XMaCKptC3GEYql20tHsbzDUCCpN
- Plugin repo (this one): https://github.com/Nikolaj-Storm/Mad-Minds
- Marketer onboarding doc: `EMPLOYEE-ONBOARDING.md`
- Admin setup doc: `SETUP.md`
- Connector inventory: `onlineminds-marketing/CONNECTORS.md`
