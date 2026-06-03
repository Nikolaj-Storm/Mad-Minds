---
name: account-conventions
description: OnlineMinds house rules — the brand portfolio, KPI definitions, where files live in the Marketing Hub, naming conventions, and brand-voice pointers. This skill is foundational. Every other OnlineMinds marketing skill reads it first to know which brand it is working on, how OnlineMinds defines its metrics, and where to read inputs from and write outputs to. Use it automatically at the start of any marketing task, audit, report, or plan.
---

# OnlineMinds Account Conventions

## Response format — every substantive answer starts with a brief header

Lead every substantive response to a marketer with this three-block summary. Keep it tight — bullets, not paragraphs. Then deliver the actual content underneath.

**Objectives**
- (1-3 bullets) The marketing goal(s) the request was trying to address, in plain English. Describe what the marketer was trying to accomplish, not which tools you used.

**Tools used**
- (1-3 bullets) Which skill(s) and connector(s) ran, and what each one contributed. Use plain-English names (e.g. "monthly paid review", "claude-ads Google deep-dive", "Google Ads connector for live data") — not file paths or internal skill identifiers.

**Want to go deeper?**
- (1-3 bullets) Concrete follow-up commands or skills that would extend the answer in directions the user is likely to care about. Each bullet should be a specific command or natural-language prompt the user can copy/paste — not a generic listing of every skill. Match the user's apparent intent (e.g. if they just got a paid-media analysis, suggest a tracking audit or a competitor scan, not unrelated skills).

After the header block, deliver the actual content normally.

**When to skip the header:**
- Pure conversational replies ("ok", "yes", "thanks").
- Mid-task clarification questions (e.g. "I need Rentumo's Meta Ads account ID to continue").
- The verbatim accept-phrase interaction during a Tier 1 write — keep that exchange tight and focused.
- Errors / blockers that require the user to fix something before continuing.
- Inside a guided multi-step flow like `/setup-marketing` — show the header at the END of the flow (final summary), not at each step.

For everything else — analyses, audits, plans, written reports, file saves, recommendations — the header is mandatory.

## How to interpret marketer requests (read this first)

Marketers describe what they want in normal English. They are NOT expected to know which slash command does what, and most of the time they won't type `/` at all. Your job is to **route their intent to the right skill or skills automatically and explain what you're doing in one sentence**.

**Routing principles:**

- Treat any request matching a skill's purpose as an invocation, even without the slash command. "How is Rentumo's Google Ads doing?" → run `/ads google` (and probably `/monthly-paid-review rentumo` for the OnlineMinds-formatted version). The user doesn't need to know which one.
- When multiple skills apply, **chain them**. "Analyze Rentumo's Google and Meta and suggest a rebalance" → `/ads google` + `/ads meta` + `/ads budget`, then synthesize. Tell the user the plan in one short sentence before running: "Running the Google audit, the Meta audit, and the cross-platform budget review — back in a moment."
- When a request implies both **analysis and action**, do analysis first, then ask before any write. "Find wasted spend on Rentumo and apply the fixes" → `/wasted-spend-audit` for analysis → present findings → "Apply the top N? (a) and (b) are Tier 2; (c) raises a budget so it's Tier 1 — needs the typed phrase." Then `/ad-actions` with the spend-gate.
- When a **light request** is ambiguous, **propose a route** instead of asking for permission. "Look at Rentumo." → "I'll run a quick monthly paid review and a competitor scan — say stop if you want something different." Default to action.
- When a **big request** is ambiguous (see the size threshold in the next section), ASK clarifying questions FIRST — don't guess your way through it.
- When two plugins overlap (e.g. both `onlineminds-marketing` and `claude-ads` have paid-review capability), pick by **what the user seems to actually want**: a quick OnlineMinds-formatted monthly review → `/monthly-paid-review`; a deep multi-platform audit with Health Score and PDF → `/ads audit` + `/ads report`.
- When a request needs a value that's `PLEASE FILL` in `account-conventions-live` (see below), stop and ask — don't substitute a guess.
- For any write action (Google Ads, Meta Ads, Google Tag Manager), the Tier 1 / Tier 2 spend-gate rules later in this file are mandatory and non-overridable. Routing intent into a write does not bypass the gate.

**Showing your work:** narrate the routing in one short sentence as you go ("running the audit", "pulling data", "writing the draft to your folder"). Don't expose tool internals or skill names like "I'm now invoking `monthly-paid-review.SKILL.md`". Keep it normal English.

**Slash commands still work** for marketers who prefer the explicit form — never refuse a slash command, never tell a user to use one. Both styles are supported equally.

## Ask before doing big things

The default bias is action — but for substantial tasks, **ask 2–5 clarifying questions FIRST**. Asking takes 30 seconds. Running the wrong audit takes 5–10 minutes, burns tokens, and produces a deliverable nobody wanted. Always cheaper to clarify than to redo.

### What counts as "big" — clarify before running

- **Multi-platform or multi-brand audits.** `/ads audit`, monthly paid review across all brands, full SEO+GEO across multiple markets.
- **Strategic deliverables.** Campaign plans, content briefs, content calendars, growth experiments. Getting the direction wrong wastes the actual work that follows.
- **Anything that will be published to a shared team folder.** Future people read these as the source of truth.
- **Live ad-account actions and tracking changes.** The Tier 1/Tier 2 spend-gate is in addition to clarification, not instead of. Clarify the intent first, then run the gate at execution time.
- **Creating new infrastructure.** New brand folders, new sections in `account-conventions-live`, new people folders. Hard to undo cleanly.
- **Long agent chains** (3+ skills run sequentially). Tokens add up; bad chains compound.

### What counts as "small" — propose and run

- A single read-only query ("show me Rentumo's spend last week").
- Saving a draft to the user's own personal folder.
- Routing to one specific skill the user clearly named or implied.
- A quick lookup, calculation, or factual answer.
- Mid-task continuation when the next step is obvious from prior context.

### How to ask

Use `AskUserQuestion` with **2–4 concrete multiple-choice options** rather than open-ended "what do you want?" prompts. The goal is fast convergence, not negotiation.

Typical clarifying-question dimensions for a big task:

- **Scope** — single brand vs portfolio? Single market vs all? Specific channel(s) vs everything?
- **Time horizon** — last week, last month, last quarter, year-to-date, vs prior period?
- **Depth** — quick summary vs deep audit with PDF? Read-only or willing to act on findings?
- **Deliverable** — personal-folder draft, or publish to the team immediately? Format: Google Doc, Markdown, PDF, slide deck?
- **Audience** — for you, for the team standup, for the leadership review, for an external client?
- **Comparison baseline** — vs target, vs prior period, vs competitor, vs all of the above?

Skip dimensions whose answer is obvious from the request or already documented in `account-conventions` / `account-conventions-live`. Don't ask 5 questions when 2 are enough; don't ask 2 when the request was specific enough to need none.

### After the user answers

Run the task — don't re-confirm, don't ask "are you sure?". Narrate the chosen route in one short sentence ("Running the full Google + Meta audit for Rentumo, last 30 days, against your target ROAS, saving to your reports folder"), then go.

### Special case: clarifying vs the response header

If you ask clarifying questions BEFORE running, the response-format header (Objectives / Tools used / Want to go deeper) appears with the FINAL deliverable, not with the clarifying questions. Clarifying questions are a separate exchange — keep them tight and free of the header.

> This is the shared source of truth for the OnlineMinds marketing department. Other skills reference it. The structural rules (routing, spend-gate, naming, Drive map) live in this file. The **brand-specific values** (account IDs, KPI targets, currency, conversion definitions, brand voice defaults) live in a separate Drive doc: `Mad Minds/01_Knowledge_Base/account-conventions-live` — that doc is editable by any `@onlineminds.io` marketer, so values can be set without a code change.

## How to use this skill (read this first)

**Before any task that needs a specific value** (e.g. "ROAS target for Rentumo", "Meta account ID for Adsumo", "conversion definition for Bidumo"), do this:

1. Open `Mad Minds/01_Knowledge_Base/account-conventions-live` via the Google Drive connector.
2. Find the value you need.
3. **If the value is filled in** — use it and continue silently.
4. **If the value still says `PLEASE FILL` (or the section is missing)** — STOP. Do not guess. Do not proceed with a placeholder. Instead, tell the user plainly:
   > "I need `<the specific value>` to continue. It's not set yet in `01_Knowledge_Base/account-conventions-live`. What's the value?"
   When the user answers, write it into the live doc at the right place (preserving the headings exactly), then continue the original task.
5. If the user explicitly says "skip it for now, just estimate / use a generic placeholder", do so but flag the estimate at the top of any output ("**Estimated:** ROAS target assumed at 3.0x — fill in `account-conventions-live` to make this real").

This pattern means new marketers get prompted in real time for whatever's missing, and the values accumulate in Drive as the team uses the system. No big upfront fill-in exercise required.

## The brand portfolio

OnlineMinds ApS operates a portfolio of brands. Always confirm which brand a task targets before starting. If the user names a brand, use it. If ambiguous, ask which brand.

| Brand | Slug | What it is | Primary markets | Primary paid channels |
|---|---|---|---|---|
| **Rentumo** | `rentumo` | [FILL IN] | [FILL IN] | [FILL IN] |
| **Adsumo** | `adsumo` | [FILL IN] | [FILL IN] | [FILL IN] |
| **Printumo** | `printumo` | [FILL IN] | [FILL IN] | [FILL IN] |
| **Bidumo** | `bidumo` | [FILL IN] | [FILL IN] | [FILL IN] |
| **Monetumo** | `monetumo` | [FILL IN] | [FILL IN] | [FILL IN] |
| **Photumo** | `photumo` | [FILL IN] | [FILL IN] | [FILL IN] |
| **Jacob Lund Art (JLA)** | `jla` | [FILL IN] | [FILL IN] | [FILL IN] |

When a metric, target, or convention differs by brand, the brand-specific value lives in that brand's folder under `01_Knowledge_Base/brand/<brand>/`. This file holds the defaults.

## Where everything lives — the Marketing Hub on Google Drive

The shared hub is the root folder **"Mad Minds"**. All inputs are read from it and all deliverables are written back to it, so colleagues can build on each other's work. Never leave a finished deliverable only inside a private Cowork session.

```
Mad Minds/
├── 00_START_HERE/            ← README, conventions, onboarding
├── 01_Knowledge_Base/        ← brand voice, playbooks, ICP/personas, past campaigns, glossary
│   └── brand/<brand>/        ← per-brand voice + brand-specific overrides
├── 02_Brand_Assets/          ← logos, fonts, imagery, templates
├── 03_Data/
│   ├── raw_exports/YYYY-MM/  ← dated dumps from ad platforms, GA4, GSC
│   ├── cleaned/              ← processed, analysis-ready datasets
│   └── connectors-cache/     ← outputs of scheduled pulls
├── 04_Reports/
│   ├── _templates/           ← report skeletons skills fill in
│   ├── weekly/ monthly/ quarterly/
│   └── ad-hoc/YYYY-MM-DD_brand_topic/
├── 05_Plans_and_Strategy/    ← campaign briefs, content calendars, growth experiments
└── 06_Automation_Outputs/    ← logs/, scheduled/
```

**Reading inputs:** look first in `03_Data/cleaned/`, then `03_Data/raw_exports/<latest month>/`. If no usable data is present and a connector is available, pull live. If neither, ask the user to paste data.

**Writing outputs (shared, published):** match the cadence folder (`04_Reports/monthly/` etc.) or `04_Reports/ad-hoc/` for one-offs. Always use the matching template from `04_Reports/_templates/`.

**Writing outputs (personal drafts, default):** `07_People/<name>/` is divided into five subfolders. Save into the subfolder that matches the artifact's nature:

| Subfolder | What goes here | Skills that target it by default |
|---|---|---|
| `reports/` | Drafts of analytical/stakeholder-facing artifacts | `/monthly-paid-review`, `/wasted-spend-audit` (the report half), `/seo-geo-audit`, `/competitor-scan`, `/ads audit`, `/ads <platform>`, `/ads report` |
| `plans/` | Briefs, calendars, forward-looking strategy docs | `/campaign-plan`, `/content-brief`, `/ads plan`, `/ads create` |
| `data/` | Raw exports, cleaned CSVs, negative-keyword lists, working datasets | `/wasted-spend-audit` (the CSV half), data-collection steps of any analysis skill |
| `notes/` | Meeting notes, research, learnings, scratch context | Use when the user is jotting, not producing a deliverable |
| `archive/` | Older completed work the marketer has moved out of the active folders | Skills never write here; only the marketer does, manually |

If the user opens a brand-new line of work that doesn't fit (e.g. a new content type that isn't a brief or report), ask once where to save it; if they don't specify, default to `reports/` and tell them.

## File naming conventions

Every artifact is named: `YYYY-MM-DD_<brand>_<type>[_<detail>].<ext>`

- Date-prefixed and zero-padded so files sort chronologically and never collide.
- Brand tag always present (lowercase): `rentumo`, `adsumo`, `printumo`, `bidumo`, `monetumo`, `photumo`, `jla`. Use `portfolio` for cross-brand work.
- Type is a short slug: `monthly-paid-review`, `wasted-spend`, `content-brief`, `seo-geo-audit`, `campaign-plan`, `competitor-scan`.

Examples:
- `2026-06-01_rentumo_monthly-paid-review.md`
- `2026-06-01_portfolio_competitor-scan_nl-market.md`

## KPI and metric definitions (house standard)

Use these definitions consistently across all reports so numbers are comparable brand-to-brand and month-to-month. Brand-specific targets live in each brand folder; these are the shared definitions and default benchmarks.

| Metric | OnlineMinds definition | Default target / benchmark |
|---|---|---|
| ROAS | Revenue attributed to ads / ad spend (same attribution window across brands) | [FILL IN per brand] |
| CPA | Total ad spend / conversions | [FILL IN per brand] |
| CAC | (Marketing + sales cost) / new customers | [FILL IN] |
| Conversion rate | Conversions / clicks (paid) or / sessions (organic) | [FILL IN] |
| "Conversion" definition | [FILL IN: signup? purchase? lead? Differs by brand — define per brand] | — |
| Attribution model | [FILL IN: e.g. last-touch as default; note any platform differences] | — |
| Reporting currency | [FILL IN: DKK or EUR — pick one and convert consistently] | — |
| Attribution window | [FILL IN: e.g. 7-day click] | — |

> If a skill needs a definition not listed here, it should state the assumption it used at the top of its output and flag it for addition to this table.

## Brand voice

Each brand's voice, tone, banned/preferred terms, and positioning live in `01_Knowledge_Base/brand/<brand>/brand-voice.md`. Read the relevant one before writing any customer-facing copy. Defaults across the portfolio: [FILL IN: e.g. clear, concrete, no hype, Scandinavian-direct]. Danish-language output for DK-market assets; English otherwise unless specified.

## Working conventions

- **Multi-brand by default.** Never assume a single account; always scope to a named brand or `portfolio`.
- **State your data source.** At the top of any analytical output, note where the numbers came from (which connector / which file / which date range).
- **Show comparison context.** Every metric gets a prior-period and/or target comparison, never a bare number.
- **Log automated/scheduled runs** to `06_Automation_Outputs/logs/`.
- **Don't fabricate.** If data is missing, say so and ask, rather than estimating silently.
- **Privacy:** never write API keys, secrets, or credentials into any hub file or report.

## Connector inventory (by capability)

| Capability | Live data via | Notes |
|---|---|---|
| Shared Hub | Google Drive (Mad Minds) | Reads inputs, writes drafts to `07_People/<name>/`, publishes finals to `04_Reports/` etc. |
| Paid — Google | Google Ads | Reads + write (pause/enable, budgets, bids, negatives, create campaigns/ads). Tier 1/2 spend-gate applies. |
| Paid — Meta | Meta Ads | Same; Facebook + Instagram. |
| Web analytics | GA4 | Read-only sessions, conversions, funnels. |
| Organic search | Google Search Console | Clicks, impressions, positions per query/page. |
| Tracking config | Google Tag Manager | **Write-capable.** Diagnose tracking gaps; create/edit tags, triggers, variables; publish container versions. Changes that affect conversion counts are Tier 1 in the spend-gate (bad tracking = fake spend signals). |
| SEO + AI mentions | Ahrefs | Keyword research, backlinks, site audit, Brand Radar. |
| Competitive | SimilarWeb | Traffic estimates, market benchmarking. |
| Optional | Notion, Slack, Supabase, Vercel | See `CONNECTORS.md`. |

For new marketer onboarding, run `/setup-marketing` — it walks through each of the above in order, tests authorization, and ends with a capabilities tour.
