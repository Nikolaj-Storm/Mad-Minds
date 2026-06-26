---
name: setup-marketing
description: First-session onboarding for a new marketer in the Mad Minds project. Walks them through authorizing every required connector (Google Drive, Google Search Console, Google Ads, Meta Ads), verifies Drive access to Mad Minds, asks their first name and confirms their personal folder, and ends with a capabilities overview of every skill they can run. Triggered automatically by CLAUDE.md on first session, or manually as /setup-marketing whenever a marketer wants to re-verify their setup. Use whenever a marketer is new, says "hi" / "what can you do" / "I just installed this", or asks to check their connectors.
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

### Step 3 — Connect the tools (Customize → Connectors)

All connecting happens in **Customize → Connectors** (the top-level panel). Google Drive is in Claude's built-in catalog; **Google Search Console, Google Ads, and Meta Ads are added as *custom connectors*** (paste a URL). The custom-connector path uses Claude's hosted sign-in, which is the reliable one.

> IMPORTANT: Do NOT authenticate Google Search Console, Google Ads, or Meta Ads through an in-session sign-in link (a `localhost` URL). Claude desktop's plugin/in-session OAuth listener is unreliable — it fails with "no flow in progress" and the tools never register. Always use the **Add custom connector** path below. (There is no `authenticate` tool to call for these now — they aren't plugin servers anymore.)

For each connector: say what it's for in one sentence, test it with a trivial read, and if it isn't connected give the exact steps and wait for "done" before re-testing. If one won't connect after two tries, note it and move on — don't block onboarding.

- **Google Drive** (built-in catalog) — the Mad Minds Hub. Steps: Customize → Connectors → **Google Drive → Connect** → sign in with `@onlineminds.io`.
- **Google Search Console** (custom connector) — organic clicks/impressions/positions; read-only; they see only their own verified properties. Steps: Customize → Connectors → **Add custom connector** → URL `https://gsc.tail40453d.ts.net/mcp` → leave Advanced settings empty → **Add** → **Connect** → sign in with the Google account that has their Search Console. (After connecting, a new session may be needed for the tools to appear.)
- **Google Ads** (custom connector) — campaign reporting + management (read+write); per-user; they see only accounts they can access; writes simulate (READONLY_MODE) until enabled and route through `/ad-actions`. Steps: Customize → Connectors → **Add custom connector** → URL `https://gads.tail40453d.ts.net/mcp` → leave Advanced settings empty → **Add** → **Connect** → sign in with the Google account that has their Google Ads.
- **Meta Ads** (custom connector(s) — self-hosted, like Google Ads) — Facebook/Instagram reporting + management (read+write); per-user; they see only ad accounts they can access; writes simulate (READONLY_MODE) until enabled and route through `/ad-actions`. **Two Meta business areas → two connectors; add the one(s) the marketer manages:** onlineminds.io → `https://meta-onlineminds.tail40453d.ts.net/mcp` ; Rentumo → `https://meta-rentumo.tail40453d.ts.net/mcp`. Steps: Customize → Connectors → **Add custom connector** → the URL → leave Advanced settings empty → **Add** → **Connect** → sign in with their **Facebook** account. (After connecting, a new session may be needed for the tools to appear. The marketer's Facebook must hold a role in the relevant ad accounts; if Meta returns a permission error, they're not added to that account/Business Manager yet.)

- **Thribee** (plugin connector — pre-wired, no setup needed) — ad spend data across 22 markets. This is already included in the plugin's `.mcp.json` with a shared bearer token, so it connects automatically when the plugin loads. No action required from the marketer. Verify it's working by asking "list Thribee markets" — it should return the 22 configured markets.

- **Rentumo Trials** (plugin connector — pre-wired, no setup needed) — **Rentumo only**: new subscribers (trials) **and revenue** across all 26 Rentumo markets, read-only. Each market returns `new_subscriptions`, `revenue_gross`, and chargeback figures. Pre-wired with a shared bearer token, so no marketer login. Revenue is in each market's **local currency** (never summed across markets). Verify by asking "how many new subscribers and how much revenue did Rentumo get last month".

Skip Notion / Slack / Supabase / Vercel unless the marketer asks — those are optional plugin connectors.

Not available yet (don't walk through; if asked, say they're coming): **GA4**, **Google Tag Manager**, **Google Merchant Center**. For organic search, use Google Search Console.

If a connector fails to authorize twice in a row, note it in the summary and continue. Do not block the whole onboarding on one connector.


### Step 3b — Record their access profile (notes about their spaces + connections)
As the connectors come online, capture what this person can actually reach, and save it so the system knows their access in future sessions and doesn't have to re-check each time.

Gather (from the connectors that connected):
- **Google Search Console** — call `list_sites`; record each property URL and its permission level (e.g. siteFullUser vs siteUnverifiedUser).
- **Google Ads** — call `list_accounts`; record the account IDs, and where `account-conventions-live` maps an ID to a brand, note the brand too.
- **Meta Ads** — if connected, list the ad accounts they can access (via the Meta connector's account-listing tool) and record them + mapped brands/company.
- **Google Drive** — their personal folder, plus any shared Hub folders they can open.
- Which connectors are connected vs. still missing.

Then WRITE it to two places:
1. **Their personal folder** — create/overwrite a doc `07_People/<name>/notes/access-profile` containing: today's date, connectors connected, GSC properties (+ permission level), Google Ads account IDs (+ mapped brands), and anything they told you about which brands they own. This is the per-person source of truth for their access.
2. **The Team Roster** in `01_Knowledge_Base/account-conventions-live` (section 6) — append/refresh a one-line summary next to their name, e.g. `nikolaj — GSC: rentumo.* (7) + usenti.com; Google Ads: 9289934893, 2484018099`.

To the marketer, confirm in plain language only — never dump raw IDs/JSON: e.g. "You've got Search Console access to 8 properties and 2 Google Ads accounts — I've noted that in your profile so I won't have to ask again." Re-running `/setup-marketing` refreshes this profile.

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
> - **Thribee** is pre-wired (no login needed) — ask "show Thribee spend for DK last month" to pull cross-market spend data across all 22 markets.
> - **Rentumo Trials** is pre-wired (Rentumo only) — ask "how many new subscribers and how much revenue did Rentumo get last month" to pull trials + revenue per market. Revenue is in each market's local currency.
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
- Never show raw connector JSON or error stacks. Translate failures into one sentence: "Google Ads isn't connected yet — add it via Customize → Connectors → Add custom connector with the URL https://gads.tail40453d.ts.net/mcp, connect, then say done."
- Don't proceed past Step 3 until at least Google Drive is connected (otherwise the rest of the system is useless).
- If the user explicitly says "skip the setup, I know what I'm doing", confirm what they want to skip and jump straight to whatever task they name. But never skip naming the user — `07_People/<name>/` resolution requires it.
- Save a short log of this onboarding to `Mad Minds/06_Automation_Outputs/logs/` so the maintainer can see who's onboarded and which connectors failed for who.
- Always write the access profile (Step 3b) — the per-person `07_People/<name>/notes/access-profile` doc plus the Team Roster summary line. Other skills read `account-conventions` first, so recording each person's reachable properties/accounts/brands there lets the whole system route correctly and skip re-checking access.
