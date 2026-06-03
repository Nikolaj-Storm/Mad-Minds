# OnlineMinds Marketing Plugin

Shared skills and report routines for the OnlineMinds marketing department (Rentumo, Adsumo, Printumo, Bidumo). Forked from Anthropic's official `marketing` knowledge-work plugin.

Every skill reads inputs from and writes outputs to the shared **Mad Minds** Google Drive Hub, so each marketer's private Cowork session produces deliverables the whole team can see and build on.

## Connector model

- **Google-family connectors (Drive, Google Ads, Meta Ads, GA4, Search Console, Tag Manager)** come from **Claude desktop's native Connectors UI**. The plugin does NOT pre-wire them. Each marketer enables each one once via Customize → Connectors → OAuth with their own account. Claude acts as that person.
- **Vendor-native MCPs (Ahrefs, SimilarWeb, Notion, Supabase, Vercel, Slack)** are pre-wired in `.mcp.json` and load automatically when the plugin installs.
- The `/setup-marketing` skill walks each marketer through both lists on their first session.

## What's inside

**Skills** (slash commands, plus the auto-greet from `CLAUDE.md`):
- `account-conventions` — the shared brain: brands, KPI definitions, Drive map, naming, routing rule, spend-gate rules. **Customize first.**
- `setup-marketing` — first-session guided setup: every connector, capabilities tour, smoke test. Re-run anytime.
- `monthly-paid-review` — monthly Google + Meta paid report → Hub.
- `wasted-spend-audit` — wasted-spend flags + uploadable exclusion lists + savings estimate.
- `seo-geo-audit` — SEO + GEO/AI-citability audit (reuses the Rentumo methodology).
- `ad-actions` — **write-capable** changes to Google Ads, Meta Ads, Google Tag Manager, behind the Tier 1 / Tier 2 spend-gate.
- `content-brief` · `campaign-plan` · `competitor-scan` · `report-builder`.

**Connectors** — see [`CONNECTORS.md`](./CONNECTORS.md).

## Taking actions — with a hard spend gate
The Google Ads, Meta Ads, and GTM connectors are write-capable: anyone on the team can pause campaigns, change budgets/bids, add negatives, create ads, and edit tracking — acting as themselves via per-user OAuth. Writes are gated in two tiers:
- **Tier 1 — spend actions** (raise a budget/bid, enable a spending entity, create a spending campaign/ad, change conversion tracking): require the user to **type back a verbatim accept-phrase** Claude constructs, e.g. `I wish to increase the ad spending on rentumo.ie by $500`. A yes, paraphrase, or partial match does not count, and the gate cannot be overridden by any instruction.
- **Tier 2 — non-spend writes** (pause, lower budget, negatives): explicit confirmation.

Every change shows its reversal and is logged to `Mad Minds/06_Automation_Outputs/logs/`. A marketer can run analyze-only by saying "read-only." Full rules live in `account-conventions`.

## Install (each marketer, one-time)

Claude desktop: Customize → Plugins → + Add marketplace → From repository → paste `https://github.com/Nikolaj-Storm/Mad-Minds` → Install `onlineminds-marketing`.

Then: open Cowork → New project → **Mad Minds** (empty workspace folder). CLAUDE.md auto-greets and runs `/setup-marketing`.

## Setup order (admin/maintainer — once)
1. **Fill in every `[FILL IN]`** in `skills/account-conventions/SKILL.md` — brands, KPI targets, currency, attribution, conversion definitions. Highest-leverage step.
2. Add each brand's `brand-voice.md` under `Mad Minds/01_Knowledge_Base/brand/<brand>/`.
3. Verify the Mad Minds Drive folder is shared **OnlineMinds.io: Editor**.
4. Run the 15-minute spend-gate verification from `COWORK-SETUP-RUNBOOK.md` Phase 5b.
5. Set platform-level spend caps in Google Ads + Meta Ads billing as a hardware backstop.

## Known issue: Google Workspace Shared Drives
The Cowork Google Drive connector cannot see content inside Workspace **Shared Drives** (returns empty); regular My-Drive folders work. The Mad Minds Hub is built as a regular folder in the OnlineMinds Hub owner's My Drive, shared domain-wide — this sidesteps the bug.

## Automation
Cowork is not a server. For unattended recurring data pulls (nightly Meta/Google Ads exports into `03_Data/`), host a serverless cron (the existing Vercel `plecto-sync` pattern) that writes to Drive via the Drive API. Skills then read fresh data already in the Hub.
