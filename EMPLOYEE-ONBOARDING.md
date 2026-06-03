# Mad Minds — Employee Onboarding (~10 min, once)

Welcome. You're setting up your own marketing assistant inside Claude Cowork. After this you'll be able to analyze ad/SEO/analytics data, act on it (with safety gates on anything that spends money), and read/write reports directly in the shared **Mad Minds** Google Drive Hub. Everything lives in Drive — there's no local folder to maintain.

This is one-time. Future sessions just need you to open Cowork.

## Step 1 — Install Claude desktop
If you don't have it: https://claude.ai/download. Sign in with your `@onlineminds.io` account.

## Step 2 — Install the Mad Minds plugins
1. In Claude desktop, click your profile (bottom-left) → **Customize**
2. **Plugins** tab → **+ Add marketplace** → **From repository**
3. Paste: `https://github.com/Nikolaj-Storm/Mad-Minds`
4. Two plugins appear — **install both**:
   - **`onlineminds-marketing`** — your shared brain, Drive Hub routing, write-capable ad actions with the spend-gate, monthly review / wasted-spend / SEO-GEO / content-brief skills.
   - **`claude-ads`** — open-source paid-advertising audit toolkit (MIT, by AgriciDaniel). 250+ checks across Google, Meta, YouTube, LinkedIn, TikTok, Microsoft, Apple, Amazon Ads. Health Score 0-100. Industry templates. PDF reports.

Both plugins are now active in every Cowork session — no per-project setup.

## Step 3 — Open Cowork and run the guided setup
1. Open Cowork (the desktop app)
2. Start a new session — no need to create a project or pick a workspace folder. Everything goes through the Google Drive connector to the shared Mad Minds hub.
3. Type: **`/setup-marketing`**

That command walks you through:
- Authorizing each connector you need (Google Drive, Google Ads, Meta Ads, GA4, Search Console, Google Tag Manager, Ahrefs, SimilarWeb) — one at a time, with the exact clicks
- Confirming Drive access to the shared **Mad Minds** Hub
- Asking your first name so it knows your personal folder (`Mad Minds/07_People/<your-name>/`)
- A capabilities tour — every command you can run
- One small live test so you leave having seen it work

## Step 4 — Try a real command
After onboarding, try one of these:
- `/monthly-paid-review rentumo` — pulls last month's Google + Meta paid data, computes KPIs, drafts the report to your folder
- `/competitor-scan rentumo dk` — head-to-head comparison in the Danish market
- `/seo-geo-audit printumo` — SEO + AI-citability audit

## How saving works (everything lives in Drive)
- Your drafts and works-in-progress save to **your personal folder** `Mad Minds/07_People/<name>/` by default. Claude writes them directly through the Drive connector — nothing lives on your laptop.
- When something's finished and useful to the team, say **"publish this to the team"** — Claude copies the final version into the shared folder (e.g. `04_Reports/monthly/`). Your working copy stays in your folder.
- Every session starts by reading the latest state from Drive. There's no "sync" step — Claude pulls fresh.
- The whole team has Editor access to Mad Minds. If you accidentally overwrite something, Drive's per-file version history is the safety net (File → Version history in any Google Doc).

## How taking actions works (the safety gates)
You can pause campaigns, change budgets/bids, add negative keywords, create ads on Google + Meta, and edit Google Tag Manager — Claude acts as you (using your authorizations), so you can only touch accounts you already have access to.

**Spend changes require a typed confirmation phrase.** If you ask Claude to do something that would increase spend (raise a budget, raise a bid, enable a campaign, launch a new ad, or change tracking that affects conversion counts), Claude shows you a sentence like:

> I wish to increase the ad spending on rentumo.ie by $500

You **type that exact sentence back word-for-word** as your next message. Nothing happens until you do. A "yes" or "go ahead" won't trigger it — this is on purpose, so spend is never changed by accident or by a misread instruction.

Lower-risk changes (pausing, adding negatives, lowering a budget) just need a normal "yes."

Claude always tells you how to undo a change. To make sure nothing gets changed at all in a session, say **"read-only"** at the start.

## Capabilities at a glance

### From `onlineminds-marketing` (OnlineMinds-specific, Drive-integrated)

**Analyze** — read live data, save to your Drive folder
- `/monthly-paid-review <brand>` · `/wasted-spend-audit <brand>` · `/seo-geo-audit <brand> <market>` · `/competitor-scan <brand> <market>`

**Plan** — turn an idea into a brief
- `/content-brief <brand> <type> <topic>` · `/campaign-plan <brand> <goal>`

**Act** — change live ad accounts (with safety gates)
- `/ad-actions <brand> <change>` — only place that touches money. Tier 1 changes require a typed accept-phrase.

**Document** — assemble a deliverable
- `/report-builder`

**Re-run setup anytime**
- `/setup-marketing` — re-verifies your connectors and shows the capabilities tour again

### From `claude-ads` (deep analysis, industry benchmarks, PDF reports)

**Full multi-platform audit**
- `/ads audit` — 6 parallel agents run 250+ checks across Google, Meta, YouTube, LinkedIn, TikTok, Microsoft, Apple, Amazon. Returns a Health Score 0-100, prioritized action plan.
- `/ads report` — turn the audit into a client-ready PDF.

**Single-platform deep dives**
- `/ads google` · `/ads meta` · `/ads youtube` · `/ads linkedin` · `/ads tiktok` · `/ads microsoft` · `/ads apple` · `/ads amazon`

**Cross-cutting**
- `/ads creative` — creative quality + fatigue across platforms
- `/ads landing` — landing page assessment
- `/ads budget` — budget allocation review
- `/ads attribution` — cross-platform attribution audit
- `/ads tracking` — server-side tracking pipeline audit (sGTM, CAPI, dedup)
- `/ads competitor` — competitor ad intelligence

**Planning / math**
- `/ads plan <type>` — strategic plan (`saas`, `ecommerce`, `local-service`, `b2b-enterprise`, `info-products`, `mobile-app`, `real-estate`, `healthcare`, `finance`, `agency`, `generic`)
- `/ads math` — PPC financial calculator (CPA, ROAS, break-even, LTV:CAC)
- `/ads test` — A/B test design (hypothesis, sample size, duration)

**Creative generation**
- `/ads dna <url>` — extract brand DNA from a site
- `/ads create` — campaign concepts and copy briefs
- `/ads generate` — AI ad image generation
- `/ads photoshoot` — product photography in 5 styles

### When to use which

| You want to… | Use |
|---|---|
| Run the monthly OnlineMinds paid review and save it to Mad Minds | `/monthly-paid-review` |
| Get a deep, scored audit with PDF deliverable for a stakeholder meeting | `/ads audit` + `/ads report` |
| Plan a new campaign for a brand using OnlineMinds brand voice | `/campaign-plan` |
| Plan a new campaign using an industry template (saas, ecom, etc.) | `/ads plan` |
| **Apply** a change (pause, budget, bid, create) on a live account | `/ad-actions` — always |
| Find wasted spend with an uploadable negative-keyword CSV | `/wasted-spend-audit` |
| Get a deep creative-fatigue audit across all platforms | `/ads creative` |
| Calculate CPA / ROAS / LTV:CAC quickly | `/ads math` |

Common pattern: **`/ads audit` to find issues** → **`/ad-actions` to apply the fixes** (the spend-gate enforces safety). Or: **`/monthly-paid-review` for the routine report**, then ask Claude to compare findings with `/ads google` for deeper diagnosis on whichever channel underperformed.

Brands: `rentumo`, `adsumo`, `printumo`, `bidumo`. Use `portfolio` for cross-brand work.

## Living docs (in Mad Minds itself)
Open `Mad Minds/00_START_HERE/` for:
- **README** — what Mad Minds is, naming, the publish workflow
- **Connector-Setup-Guide** — the step-by-step for each connector (rerun source for `/setup-marketing`)
- **Skills-Index** — every routine with a short description
- **Capabilities-Overview** — the bigger picture of what the system can and can't do
- **naming-conventions** — file naming rules

## Notes
- Cowork uses more tokens than regular Claude chat — use Cowork for finished deliverables and live data work; use regular chat for quick questions
- Never paste API keys or secrets into any Hub file or chat message
- If something breaks during onboarding, screenshot the error and ping Nikolaj
