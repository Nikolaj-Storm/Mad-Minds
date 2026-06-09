# Mad Minds — Marketer Onboarding (~15 min, once)

Welcome. You're setting up your own marketing assistant inside Claude Cowork. After this you'll be able to analyze ad/SEO/analytics data, act on it (with safety gates on anything that spends money), and read/write reports directly in the shared **Mad Minds** Google Drive Hub.

This is a one-time setup. Future sessions just need you to open Cowork and ask.

> **Note on Composio:** it's per-user, not org-level. There's no centralized setup that has to happen first. You sign up for your own free Composio account; each colleague signs up for theirs. Treat it like your Google or Facebook login.

---

## Step 1 — Install Claude desktop

Skip this step if you already have Claude desktop installed and are signed in with your account.

> If you are not signed up using `@onlineminds.io` there may be some different steps later on.

Download: <https://claude.ai/download>

## Step 2 — Install the Mad Minds plugins

1. In Claude desktop, click **Customize** (top right) → **Browse Plugins** tab → **Plugins** → **Personal** → **Add marketplace** → **Add from a repository** → paste this URL:
   ```
   https://github.com/Nikolaj-Storm/Mad-Minds
   ```
2. After a couple seconds, two plugins appear → click **+** to install both:
   - **`onlineminds-marketing`** — OnlineMinds-specific skills, Google Drive Hub routing, the spend-gate that protects live ad accounts
   - **`claude-ads`** — open-source paid-advertising audit toolkit, 250+ checks across 8 platforms, Health Score, PDF reports

Both plugins are now active in every Cowork session. No per-project setup is required — but you'll want a dedicated project for organisation. That's the next step.

## Step 3 — Create your dedicated Mad Minds project in Cowork (~2 min)

A dedicated project keeps Mad Minds work isolated from other Cowork work and lets the project's `CLAUDE.md` charter auto-load whenever you open a session here.

**In Cowork:**

1. Open Cowork (the desktop app — separate from regular Claude chat).
2. Click **+ New project** (or the equivalent "create project" button in your Cowork UI).
3. Use this information to set it up:

   | Field | Value |
   |---|---|
   | **Project name** | `Mad Minds` |
   | **Workspace folder** | Any empty folder on your machine. Recommended: create `~/Documents/Mad Minds` and pick that. The folder doesn't need to mirror the Drive Hub — Claude reads/writes the real Mad Minds Hub through the Google Drive connector (next step), not through this local folder. |
   | **Drive Hub URL (for reference)** | <https://drive.google.com/drive/folders/1aLu66XMaCKptC3GEYql20tHsbzDUCCpN> |

4. **Project instructions — paste this exact block into the Instructions / Custom instructions field.** This is the most important field. It tells Claude every session in this project is a Mad Minds session, what the rules are, where the Hub lives, and how to behave. Without it, Claude has to re-figure out context every time.

```
This is the Mad Minds marketing workspace for OnlineMinds ApS.

Mad Minds is a shared Google Drive workspace for the marketing department, at https://drive.google.com/drive/folders/1aLu66XMaCKptC3GEYql20tHsbzDUCCpN. This local Cowork workspace folder is just a session container — all real reads and writes go through the Google Drive connector to that Hub.

Two plugins are installed:
- onlineminds-marketing: in-house skills, Drive Hub routing, the /ad-actions skill for live ad-account changes (with a non-overridable Tier 1 / Tier 2 spend-gate).
- claude-ads: open-source paid-advertising audit toolkit (250+ checks across 8 platforms, Health Score 0–100, industry templates, PDF reports). Analysis-only.

House rules (the account-conventions skill loads these automatically, but for context):
- Load the account-conventions skill at the start of any marketing task. It's the foundational skill with brand portfolio, KPI definitions, Drive map, routing rule, and spend-gate rules.
- Brand-specific values (account IDs, KPI targets, currency, conversion definitions, brand voice) live in Mad Minds/01_Knowledge_Base/account-conventions-live (a Drive doc). If you need a value not yet filled in there, ask me once in chat, then write the answer into that doc so nobody gets re-asked.
- Drafts auto-save to my personal folder: Mad Minds/07_People/<my-name>/, in the matching subfolder (reports/, plans/, data/, notes/). Move to shared folders only when I say "publish this to the team".
- Ad write-actions go through the /ad-actions skill only. Spend increases require me to type a verbatim accept-phrase that you construct (Tier 1, non-overridable). Lower-risk changes (pause, lower budget, add negatives, GTM non-conversion edits) take a normal yes (Tier 2). I can say "read-only" anytime to lock the session into analysis-only mode.
- Plain English works — I don't need to type slash commands. For substantial tasks (multi-platform audits, campaign plans, anything that publishes to shared folders or touches money) ask 2–4 clarifying questions before running. For light requests, propose a route and go.
- Every substantive answer starts with a brief three-block header: Objectives / Tools used / Want to go deeper. Skip the header for short conversational replies, clarifying questions, the typed-phrase exchange, errors, or inside the /setup-marketing flow.

Brands: rentumo, adsumo, printumo, bidumo, monetumo, photumo, jla (Jacob Lund Art). Use "portfolio" for cross-brand work.

On a new session here, greet briefly and ask what I want to do. If I haven't been onboarded (no folder under 07_People with my name), suggest /setup-marketing.
```

5. Save the project. From now on, opening Mad Minds in Cowork drops you into this dedicated session every time.

> **Why a local workspace folder if Mad Minds lives in Drive?** Cowork's project model expects a local folder as its workspace. That folder is just a container for the Cowork session — you don't need to drag Mad Minds content into it. All real reads and writes go through the Google Drive connector you authorize next.

## Step 4 — Connect Google Drive (~1 min)

This one lives in the **native** Connectors panel (the top-level one, not under a specific plugin):

1. Customize → **Connectors** (the top-level item, NOT under a specific plugin)
2. Find **Google Drive** → **Connect** → sign in with your `@onlineminds.io` account

Result: Claude can now read and write the shared Mad Minds Drive Hub on your behalf.

## Step 5 — Connect the ad/analytics MCPs via Composio (~5 min)

These live in the **per-plugin** Connectors panel — separately from Drive:

1. Customize → **Onlineminds-marketing → Connectors** (left sidebar, under the plugin name)
2. Click **Connect** on each connector you need. For each, a browser tab opens for Composio's OAuth flow.

**What is Composio?** A free third-party service that handles the OAuth handshake for Google Ads, Meta Ads, GA4, Search Console, Google Tag Manager, and Merchant Center. It removes the need for any developer-token application or technical setup — you just sign in to the actual platform (Google or Facebook) through Composio's flow.

On your first Connect click, you'll be asked to sign in to Composio (30 sec, free). After that, every subsequent Connect just shows the platform's OAuth screen.

**Connect in this order:**

- **Google Ads** — sign in with the Google account that has access to your brand's Google Ads (via the OnlineMinds Manager / MCC)
- **Meta Ads** — sign in with the Facebook account that has Business Manager access
- **Google Analytics (GA4)** — Google account with GA4 viewer access
- **Google Search Console** — Google account with GSC verified for the relevant domains
- **Google Tag Manager** — GTM-admin Google account
- **Google Merchant Center** — only if your brand runs Shopping or Performance Max with a product feed

Skip Notion / Slack / Supabase / Vercel unless you actually use them.

## Step 6 — Open your Mad Minds project and run `/setup-marketing` (~3 min)

1. In Cowork, open the **Mad Minds** project you created in Step 3.
2. Start a new session inside the project.
3. Type: `/setup-marketing`

That command will:
- Show a dropdown of existing personal-folder names — pick yours, or pick "Other" to type your first name (a new folder + standard subfolders gets auto-created if you're new)
- Verify each connector by attempting a small read — tells you exactly what's broken if anything is
- Walk you through the capabilities tour
- End with a small live test so you leave having seen it work

## Step 7 — Try a real query (~1 min)

Anything in plain English. Examples:

- "Show me Rentumo's spend last week on Google Ads"
- "Do a quick audit on Printumo's paid performance"
- "How is Jacob Lund Art's organic search trending in DK?"
- Or use slash commands if you prefer: `/monthly-paid-review rentumo`

If Claude doesn't know a specific value (like your brand's Google Ads account ID), it'll ask you in chat. Answer once and Claude writes it into the shared `account-conventions-live` doc in Drive — next time, no prompt.

---

## How saving works

- Drafts go to **your personal folder** `Mad Minds/07_People/<your-name>/` automatically. Inside it Claude routes to subfolders by type: `reports/` for analyses, `plans/` for briefs, `data/` for CSVs, `notes/` for scratch, `archive/` for old work.
- When something's finished and useful to the team, say **"publish this to the team"** — Claude copies the final version into the shared folder (`04_Reports/`, `05_Plans_and_Strategy/`, etc.) with the house naming convention. Your working draft stays in your personal folder.
- Every session reads fresh from Drive. No sync, no local files.

## How taking actions works — the safety gate

You can pause campaigns, change budgets, change bids, add negative keywords, create ads on Google + Meta, and edit Google Tag Manager. Claude acts as you, so you can only touch accounts you already have access to.

**Spend changes require a typed confirmation phrase.** If you ask for anything that would raise spend (budget up, bid up, enable a campaign, launch an ad, change tracking on a conversion event), Claude shows you a sentence like:

> I wish to increase the ad spending on rentumo.ie by $500

You **type that exact sentence back word-for-word** as your next message. Nothing happens until you do. A "yes" or "approve" won't trigger it.

Lower-risk changes (pausing, adding negatives, lowering a budget) need a normal "yes."

To make a session analysis-only, say **"read-only"** at the start.

---

## Capabilities cheat sheet

### `onlineminds-marketing` — Mad Minds–integrated, write-capable

- `/monthly-paid-review <brand>` — monthly Google + Meta paid report (+ Merchant Center feed health if relevant)
- `/wasted-spend-audit <brand>` — find wasted ad spend, get an uploadable exclusion list
- `/seo-geo-audit <brand> <market>` — SEO + AI-citability audit
- `/competitor-scan <brand> <market>` — competitor comparison
- `/content-brief <brand> <type> <topic>` — brand-voice content brief
- `/campaign-plan <brand> <goal>` — full campaign brief
- `/ad-actions <brand> <change>` — the only skill that changes live ad accounts. Spend-gate enforced
- `/report-builder` — assemble inputs into a stakeholder-ready report
- `/setup-marketing` — re-run setup anytime

### `claude-ads` — deep analysis, industry templates, PDF reports

- `/ads audit` — full multi-platform audit, scored 0–100
- `/ads google` · `/ads meta` · `/ads youtube` · `/ads linkedin` · `/ads tiktok` · `/ads microsoft` · `/ads apple` · `/ads amazon` — single-platform deep dives
- `/ads creative` · `/ads landing` · `/ads budget` · `/ads attribution` · `/ads tracking` · `/ads competitor` — cross-cutting audits
- `/ads plan <type>` — strategic plan by industry
- `/ads math` · `/ads test` — PPC calculator + A/B test design
- `/ads dna` · `/ads create` · `/ads generate` · `/ads photoshoot` — creative generation
- `/ads report` — generate PDF audit report

### Slash commands optional

You don't have to use them. Plain English works: "audit rentumo's ads", "find wasted spend on adsumo", "compare bidumo to competitors in the Dutch market", etc. Claude picks the right skill and chains them when needed.

---

## Brands

`rentumo`, `adsumo`, `printumo`, `bidumo`, `monetumo`, `photumo`, `jla` (Jacob Lund Art). Use `portfolio` for cross-brand work.

## Living docs in Drive

Open `Mad Minds/00_START_HERE/` for: README, naming-conventions, Connector-Setup-Guide, Skills-Index.

## When things break

- **A connector won't connect** → screenshot the error and ping Nikolaj
- **Claude says "I need <X>" and pauses** → answer the question; Claude writes the value into `account-conventions-live` in Drive so nobody else gets asked
- **Tier 1 spend-gate doesn't ask for the typed phrase** → STOP, ping Nikolaj
- **Cowork feels expensive** → it uses more tokens than regular Claude chat. Use Cowork for live data + finished deliverables; use regular Claude for quick questions
