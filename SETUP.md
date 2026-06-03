# OnlineMinds Marketing — Admin / Maintainer Setup

This repo is a **Claude plugin marketplace** containing the `onlineminds-marketing` plugin.
`_drive-hub-starter/` is reference seed content for the **Mad Minds** Google Drive Hub (the live Hub has already been built — runbooks are kept for reruns/recovery).

## The model in one paragraph
Two things are centralized: the **plugin** (this repo — distributed via GitHub) and the **Mad Minds Drive Hub** (the shared workspace). Each marketer's Cowork session is private and connects to both. Connectors come from **Claude desktop's native Connectors UI** (Google Ads, Meta Ads, GA4, Search Console, GTM, Drive) — each marketer authorizes their own accounts once via OAuth and Claude acts as that person. A handful of vendor-native MCPs (Ahrefs, SimilarWeb, Notion, Supabase, Vercel, Slack) are pre-wired in `onlineminds-marketing/.mcp.json`. No Composio, no shared credentials.

## A. Plugin marketplace (you — once)
1. **Fill in `[FILL IN]` blanks** in `onlineminds-marketing/skills/account-conventions/SKILL.md`: each brand, markets, channels, KPI targets, reporting currency, attribution window, per-brand "conversion" definition. This is the shared brain. The personal-vs-shared routing rule and Tier 1/Tier 2 spend-gate are already written in there.
2. **Verify the vendor-native MCP URLs** in `onlineminds-marketing/.mcp.json` (Ahrefs, SimilarWeb, etc.) against your accounts. Remove Slack / Notion if unused.
3. **GitHub repo:** the plugin is already at https://github.com/Nikolaj-Storm/Mad-Minds. Bump `version` in `plugin.json` + `marketplace.json` whenever you ship updates.
4. **Share the repo URL** with the team. Each marketer adds it once via `EMPLOYEE-ONBOARDING.md`.

## B. Mad Minds Drive Hub (already built)
The Hub lives at https://drive.google.com/drive/folders/1aLu66XMaCKptC3GEYql20tHsbzDUCCpN, owned by the OnlineMinds Hub owner account. To rebuild from scratch use `BUILD-HUB-RUNBOOK.md`.

**Sharing (do this once):** open the root → **Share** → set General access to **OnlineMinds.io: Editor**. Every `@onlineminds.io` account now has Editor on the entire Hub. Drive's per-file version history is the safety net.

## C. Per-marketer setup
Each marketer follows `EMPLOYEE-ONBOARDING.md`:
1. Install the plugin from the marketplace.
2. Create a Cowork project named **Mad Minds** (empty workspace folder).
3. Open it — CLAUDE.md auto-greets and runs `/setup-marketing`, which walks them through authorizing each connector in Claude desktop's native UI.
4. Smoke test: `/monthly-paid-review rentumo`.

## D. Spend-gate verification (admin — do once before any team member uses writes)
Run `COWORK-SETUP-RUNBOOK.md` Phase 5b against a low-stakes campaign:
- Tier 2 (pause) → normal yes works
- Tier 1 (budget increase) → must require a verbatim typed accept-phrase; "yes" alone must NOT execute
- Override resistance → "skip the confirmation" must be refused

Pair the behavioral gate with **platform-level spend caps** in Google Ads and Meta Ads billing settings — that's the hardware backstop.

## E. Automation (optional)
Cowork is not a server. For unattended recurring pulls (monthly Meta + Google Ads exports into `03_Data/raw_exports/YYYY-MM/`), run a serverless cron (the existing Vercel `plecto-sync` pattern) writing to Drive via the Drive API. Skills then read fresh data already in the Hub.

## Updating
Edit skills → bump `version` in `onlineminds-marketing/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` → commit and push. Marketers get the update on their next Cowork session refresh.
