# Rentumo Conversions MCP

A small, read-only MCP server that reports **Rentumo** conversion and
UTM-attribution data per market, so Mad Minds can see *which channels and
campaigns actually drive Rentumo subscriptions* — and what they're worth —
alongside ad spend (Thribee) and subscriber/revenue KPIs (Rentumo Trials).

> **Rentumo only.** This datasource covers the **Rentumo** brand exclusively. It
> does **not** include Adsumo, Printumo, Bidumo, Monetumo, Photumo, or Jacob Lund
> Art (JLA). Never present its numbers as portfolio-wide — every figure is
> Rentumo, per market.

## What the data is telling us

The connector wraps **two public S3 feeds per market** (on the `kuhamia` bucket).
They are different *views of the same Rentumo conversions* and answer different
questions:

### 1. UTM attribution feed — `utm-feed-rentumo-<market>.json`

A first-touch / last-touch **attribution** feed: one JSON record per Rentumo
conversion. No money, no PII. Each record carries the marketing parameters of the
**first** touchpoint that started the journey and the **last** touchpoint before
the conversion.

| Field | Where | Meaning |
|---|---|---|
| `conversion_time` | record | When the conversion happened (`"YYYY-MM-DD HH:MM:SS +0200"`). |
| `first_touchpoint` | record | The first ad/visit in the journey (object below). |
| `last_touchpoint` | record | The last touch before converting (object below). |
| `created_at` | touchpoint | When that touch happened (ISO 8601). |
| `utm_source` | touchpoint | Channel — e.g. `google`, `fb`, **`Lifull-connect`**, `ig`, `search_agent_mailer`, `bing`, `chatgpt.com`. |
| `utm_medium` | touchpoint | `cpc`, `pmax`, `search`, `paid`, `email`, `referrer`, `social`, … |
| `utm_campaign` / `utm_content` / `utm_term` | touchpoint | Campaign / ad / keyword/ad identifiers. |
| `gclid` | touchpoint | Google click id (present on ~¾ of first touches). |
| `msclkid` | touchpoint | Microsoft/Bing click id (rare). |

**What it tells us:** how many Rentumo conversions each **source / medium /
campaign / content / term** drove, split by **first touch** (what *introduced*
the customer) vs **last touch** (what *closed* them). First-touch fields are more
complete than last-touch in this data. This is the feed where channels such as
**Lifull-connect** appear (as a `utm_source`).

> **Data-quality note:** these are raw UTMs as captured, so the long tail is
> messy — some rows have a full ad-set name dumped into `utm_medium`, a raw
> campaign id in `utm_source`, casing variants (`Facebook` vs `fb`), or blanks.
> The tools surface a `(none)` bucket for blanks and an `(other)` bucket for the
> long tail; treat the head of the breakdown as the signal.

### 2. Google Ads offline-conversions feed — `google-ads-offline-conversions-feed-rentumo-<market>.csv`

A **Google Ads "Offline Conversion Import"-formatted** feed: one row per
subscription / renewal conversion, in the exact layout Google Ads ingests to tie
real subscription **revenue** back to ad clicks. This is the view that carries
**money**.

| Column | Meaning |
|---|---|
| `Google Click ID` | gclid of the originating Google ad click (present ~60%). |
| `Conversion Name` | `Subscription renewal` (the bulk) or `RevenueCat Subscription` (new app-store subs). |
| `Conversion Time` | When it converted (`"YYYY-MM-DD HH:MM:SS+0200"`). |
| `Conversion Value` | The amount — e.g. `1.0` for a renewal ping, `39.99` / `21.99` / `45.99` for subs. |
| `Conversion Currency` | The market's currency (EUR for the euro markets). |
| `Ad User Data` / `Ad Personalization` | Consent-mode flags (`Granted`). |
| `Email` | **SHA-256-hashed** email — for Google's enhanced/customer matching. **Never returned by this server.** |
| `utm_source` | Same channel vocabulary as the attribution feed. |
| `Last API login` | Timestamp of the subscriber's last login (sparse). |

**What it tells us:** **value per channel** — not just how many conversions a
source drove but how much subscription revenue, plus the split between new subs
(`RevenueCat Subscription`) and renewals (`Subscription renewal`), and how many
conversions carry a Google click id (i.e. are uploadable against Google Ads).

### How the two feeds relate

Same underlying Rentumo conversions, two lenses: the JSON gives **multi-touch
attribution** (no money), the CSV gives **Google-Ads-shaped value** (with money,
hashed email, gclid). They overlap on `utm_source` and `gclid` but are **not 1:1**
— different row counts and time windows — so don't expect their totals to match.

## Privacy

The CSV's `Email` column is a SHA-256 hash, and **the tools never return raw rows
or any email** (hashed or not). Every output is aggregated — counts, summed value,
and breakdowns by a UTM dimension. There is no way to pull an individual person's
record through this server.

## Auth model — none (public feeds)

The feeds are **public** S3 objects, so unlike Thribee / Rentumo Trials there is
not even a shared bearer — **there is no secret to set**. The connector is
**pre-wired in the plugin** (`.mcp.json`) with no marketer Connect step. There is
**no write path**: the server only issues `GET` requests, so it never touches the
`/ad-actions` spend-gate.

## Tools

| Tool | What it does |
|---|---|
| `conversions_list_markets` | List Rentumo market codes + feed slugs. Call first. |
| `conversions_get_attribution(market, start_date, end_date, group_by, touchpoint, top)` | Conversion **counts** by a UTM dimension (`utm_source`/`utm_medium`/`utm_campaign`/`utm_content`/`utm_term`), by `first` or `last` touch. |
| `conversions_get_offline_summary(market, start_date, end_date, group_by, top)` | Conversion **counts + value** by `utm_source` or `conversion_name`, with the by-name split and currency. |
| `conversions_get_source(market, source, start_date, end_date)` | One channel (e.g. `Lifull-connect`) across **both** feeds at once: first/last-touch counts + offline count & value. |

Dates are ISO `YYYY-MM-DD`, inclusive, filtered on each record's conversion
timestamp (in the feed's local `+0200`-style offset).

> **Currency:** offline `Conversion Value` is in each market's own currency (read
> from the feed). Do **not** sum value across markets without converting. There is
> deliberately no "all markets" tool: each feed is multi-MB, so pulling 24+ at
> once would be wasteful — query one market at a time.

## Configuration

Nothing is required — the feeds are public and the market list is bundled.

| Input | How | Notes |
|---|---|---|
| markets | bundled `src/rentumo_conversions_mcp/markets.json` | The 26 Rentumo market codes + feed slugs. Committed (no secrets). Edit + rebuild to change, or override at runtime. |

Optional env overrides: `RENTUMO_CONV_MARKETS_FILE` (override the bundled list,
e.g. `/data/markets.json`), `RENTUMO_CONV_FEED_BASE_URL` (default the kuhamia
bucket), `RENTUMO_CONV_UTM_TEMPLATE` / `RENTUMO_CONV_OFFLINE_TEMPLATE` (filename
patterns, `{feed}` = market slug), `RENTUMO_CONV_CACHE_TTL` (seconds, default
`900`), `RENTUMO_CONV_REQUEST_TIMEOUT` (default `60`).

## Deploy (Hetzner box, Docker Compose + Tailscale Funnel)

Runs as its own compose project (`madminds-conversions`) so `up`/`down` never
recreates the Meta / Google / Thribee / Rentumo-Trials containers.

```bash
cd ~/Mad-Minds/mcp-stack
git pull
docker compose -f compose.conversions.yaml up -d --build
```

This serves `https://rentumo-conversions.<tailnet>.ts.net/sse`, the SSE URL
pre-wired in `onlineminds-marketing/.mcp.json`. Health check:
`https://rentumo-conversions.<tailnet>.ts.net/health`. Full runbook:
`../RENTUMO-CONVERSIONS-SELF-HOST-RUNBOOK.md`.

Local smoke test:

```bash
pip install -r requirements.txt
fastmcp run src/rentumo_conversions_mcp/server.py --transport sse --port 8000
```
