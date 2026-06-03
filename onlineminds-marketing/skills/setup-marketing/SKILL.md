---
name: setup-marketing
description: First-session onboarding for a new marketer in the Mad Minds project. Walks them through authorizing every required connector (Google Drive, Google Ads, Meta Ads, GA4, Search Console, Google Tag Manager, Ahrefs, SimilarWeb), verifies Drive access to Mad Minds, asks their first name and confirms their personal folder, and ends with a capabilities overview of every skill they can run. Triggered automatically by CLAUDE.md on first session, or manually as /setup-marketing whenever a marketer wants to re-verify their setup. Use whenever a marketer is new, says "hi" / "what can you do" / "I just installed this", or asks to check their connectors.
argument-hint: "(no args — runs interactively)"
---

# Setup — Mad Minds Marketing Project

> Load `account-conventions` first. This skill is interactive; treat the user as a marketer (non-engineer). One question or check per turn. Keep momentum — don't dump the whole flow at once.

## Goal
By the end of this skill, the marketer:
1. Has every required connector authorized (or knows exactly which one is blocking them).
2. Can see their personal folder in Mad Minds.
3. Knows what `onlineminds-marketing` lets them do.
4. Has run one tiny live command successfully.

## Flow

### Step 1 — Greet and orient (one short paragraph)
Welcome them to the Mad Minds project. Explain in two sentences: this is the marketing department's shared workspace; Claude can analyze ad/SEO/analytics data, act on it (pause/budget/bid changes with safety gates), and write reports straight into the shared Drive. Tell them this onboarding takes ~5 minutes and they can re-run it anytime by typing `/setup-marketing`.

### Step 2 — Identify the marketer (pick existing or add new)

The marketer's personal workspace lives at `Mad Minds/07_People/<lowercase-first-name>/`. Don't guess and don't ask them to type a freeform name — present a list so the right folder is always picked.

**Sequence:**

1. **List existing people folders.** Use the Google Drive connector to search for child folders under `07_People/` (parent ID `1PK1wSKcL81X8cV8LiY0D8oFGGwQi8kR2`, mimeType `application/vnd.google-apps.folder`). Sort alphabetically. (If the Drive connector isn't connected yet, jump to Step 3 first and come back here once it is.)

2. **Present the dropdown via AskUserQuestion.** Use AskUserQuestion with one question — "Which of these is you?" — and offer:
   - Each existing folder name (lowercase first name) as a labelled option
   - The user always gets an automatic "Other" option (the AskUserQuestion tool adds this) — when they pick "Other" they can type their first name

3. **If they pick an existing name:** confirm `07_People/<name>/` is theirs and move on to Step 3.

4. **If they pick "Other" and type a new first name:**
   - Lowercase it and strip whitespace.
   - Confirm with them: "I'll create `07_People/<name>/` for you with the standard subfolders (reports, plans, data, notes, archive) and a README. Continue?"
   - On yes, create the full structure via the Drive connector:
     - One folder `<name>` under `07_People/` (parent ID `1PK1wSKcL81X8cV8LiY0D8oFGGwQi8kR2`)
     - Five subfolders inside it: `reports`, `plans`, `data`, `notes`, `archive`
     - One Google Doc named `README` inside `<name>/` — content mirrors what's in the other people folders' READMEs (explains the subfolder purposes, naming conventions, version-history note, cleanup norm). You can copy the structure from any existing person's README to keep them consistent.
   - Tell the user the folder is built and give them the direct Drive link to their new folder.
   - Also update `01_Knowledge_Base/account-conventions-live` section 6 (Team Roster) by appending the new name to the list (preserve the existing names; just add a comma-separated entry).

### Step 3 — Walk through every required connector
For each connector below, in order, do this loop:
1. State what the connector is for in one sentence (what the marketer gets from it).
2. Test whether it's connected by attempting a trivial read (e.g. list one Google Ads account, list one Drive folder). Do NOT show raw API output to the user.
3. If connected: confirm "✓ Connected" and move on.
4. If not connected: tell them exactly where to click — `Customize → Connectors → <name> → Connect` — and what Google/Meta/etc. account to use. Wait for them to say "done" before re-testing.

Connector order and one-line purpose:
- **Google Drive** — reach Mad Minds (the shared Hub). Account: `@onlineminds.io` (any).
- **Google Ads** — pull campaign performance, pause/enable, change budgets and bids, add negatives, create campaigns/ads. Account: the Google account with access to the OnlineMinds brand Google Ads accounts.
- **Meta Ads** — same as above for Facebook/Instagram. Account: the Facebook account with access.
- **Google Analytics (GA4)** — full-funnel session/conversion data behind the ads. Account: the Google account with GA4 access.
- **Google Search Console** — organic clicks, impressions, positions for SEO/GEO work. Account: GSC-verified Google account.
- **Google Tag Manager** — read tag/trigger config; fix tracking gaps. Account: GTM-admin Google account.
- **Ahrefs** — keyword research, backlinks, site audits, Brand Radar (AI mentions). API key already provisioned for the org; this is a token connect.
- **SimilarWeb** — competitive traffic and market benchmarking. API key.

Skip Notion / Slack / Supabase / Vercel unless the marketer says they want them — those are optional.

If a connector fails to connect twice in a row, note it in the summary and continue. Do not block the whole onboarding on one connector.

### Step 4 — Show their personal folder
Tell them: "Your personal folder is `Mad Minds/07_People/<name>/`. Drafts and works-in-progress save here by default. When something's finished and useful to the team, say 'publish to the team' and the skill copies it into the right shared folder." Give them the direct link to their folder if you can construct it from the folder ID.

### Step 5 — Capabilities overview
Show them this — verbatim layout, headings exactly as shown:

> **Two plugins are installed and work together:**
> - **`onlineminds-marketing`** — OnlineMinds-specific skills, Mad Minds Drive routing, and the **only place** that touches live ad accounts (write-action skill with the spend-gate).
> - **`claude-ads`** — open-source paid-advertising audit toolkit (250+ checks across 8 platforms, Health Score, industry templates, PDF reports). Analysis-only.
>
> **From `onlineminds-marketing`:**
>
> Analyze (saves to your Drive folder)
> - `/monthly-paid-review <brand>` — Google + Meta paid report for the past month
> - `/wasted-spend-audit <brand>` — flag wasted ad spend, build an exclusion list
> - `/seo-geo-audit <brand> <market>` — SEO + AI-citability audit
> - `/competitor-scan <brand> <market>` — head-to-head competitive snapshot
>
> Plan
> - `/content-brief <brand> <type> <topic>` — brand-voice content brief
> - `/campaign-plan <brand> <goal>` — full campaign brief with channels, content, KPIs
>
> Act (live ad accounts, with safety gates)
> - `/ad-actions <brand> <change>` — pause/enable, budget/bid changes, add negatives, create ads/campaigns on Google + Meta, edit GTM. **Spend increases require you to type back a verbatim confirmation phrase** (Tier 1). Pauses and budget decreases are quick yes (Tier 2). GTM changes affecting conversion tracking are Tier 1.
>
> Document
> - `/report-builder` — assemble any of the above into a stakeholder-ready report
>
> **From `claude-ads`:**
>
> Audit (deep, scored, PDF-able)
> - `/ads audit` — full multi-platform audit with parallel agents, Health Score 0-100
> - `/ads google` · `/ads meta` · `/ads youtube` · `/ads linkedin` · `/ads tiktok` · `/ads microsoft` · `/ads apple` · `/ads amazon` — single-platform deep dives
> - `/ads creative` · `/ads landing` · `/ads budget` · `/ads attribution` · `/ads tracking` — cross-cutting audits
> - `/ads report` — generate PDF audit report
>
> Plan + math
> - `/ads plan <type>` — strategic plan by industry (saas, ecommerce, local-service, etc.)
> - `/ads math` — PPC financial calculator (CPA, ROAS, break-even, LTV:CAC)
> - `/ads test` — A/B test design (hypothesis, sample size, duration)
>
> Creative generation
> - `/ads dna <url>` · `/ads create` · `/ads generate` · `/ads photoshoot`
>
> **Common pattern:** `/ads audit` to find issues → `/ad-actions` to apply the fixes. The spend-gate enforces safety on writes regardless of which plugin surfaced the finding.
>
> **House rules I always follow**
> - I read `account-conventions` before every task — that's the shared brain (brands, KPIs, naming, routing rule, spend-gate rules).
> - Drafts save to your personal folder `07_People/<name>/`. Say "publish to the team" to move a finished version into the shared folder.
> - For Tier 1 ad changes, I'll show you a sentence like `I wish to increase the ad spending on rentumo.ie by $500`. Nothing happens until you type it back word-for-word. Say "read-only" anytime to make this session analysis-only.
> - `claude-ads` is analysis-only; it never writes to ad accounts directly. If you want to act on an `/ads` finding, I run it through `/ad-actions` so the spend-gate applies.

### Step 6 — Smoke test
Offer to run one of:
- `/account-conventions` (read-only, fastest — just loads the shared brain so they can see it works)
- `/competitor-scan <one of their brands> <market>` (read-only, uses Ahrefs + SimilarWeb so it tests those connectors)
- "Show me last 7 days performance for `<brand>` on Google Ads" (tests Google Ads read)

Let them pick. Run it, narrate as you go ("pulling the data… writing a draft to your folder… done").

### Step 7 — Wrap-up summary
Recap in 4 lines:
- Which connectors are connected ✓
- Which (if any) failed and need them to retry (with the exact click path)
- Their personal folder path with link
- A pointer to `Mad Minds/00_START_HERE/` for the living docs

Then ask if they want to run a real task right now, or stop here.

## Style and constraints
- One question or one connector per turn. Never dump the whole connector list in one message.
- Never show raw connector JSON or error stacks. Translate failures into one sentence: "Google Ads isn't connected yet — click Customize → Connectors → Google Ads → Connect, then say done."
- Don't proceed past Step 3 until at least Google Drive is connected (otherwise the rest of the system is useless).
- If the user explicitly says "skip the setup, I know what I'm doing", confirm what they want to skip and jump straight to whatever task they name. But never skip naming the user — `07_People/<name>/` resolution requires it.
- Save a short log of this onboarding to `Mad Minds/06_Automation_Outputs/logs/` so the maintainer can see who's onboarded and which connectors failed for who.
