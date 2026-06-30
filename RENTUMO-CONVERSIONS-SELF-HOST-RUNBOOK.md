# Rentumo Conversions — self-hosted connector runbook (maintainer only)

**Goal:** one read-only connector that surfaces **Rentumo** conversion and
UTM-attribution data **per market** inside Mad Minds, so the team can see which
channels and campaigns drive Rentumo subscriptions — and what they're worth —
next to ad spend (Thribee) and subscriber/revenue KPIs (Rentumo Trials). It is
**pre-wired** in the plugin — marketers do nothing, the same as Thribee / Rentumo
Trials.

> **Rentumo only.** This datasource covers the **Rentumo** brand exclusively — not
> Adsumo, Printumo, Bidumo, Monetumo, Photumo, or JLA. Every figure is Rentumo,
> per market; never present it as portfolio-wide.

**How it works (the important part):** the connector reads **two public S3 feeds
per market** on the `kuhamia` bucket — there is **no auth at all** (not even a
shared bearer): the feeds are public objects, so the server just `GET`s them. It is
**read-only**, so it never touches the `/ad-actions` spend-gate. The two feeds:

- `utm-feed-rentumo-<market>.json` — first-touch/last-touch **attribution** (one
  record per conversion, UTM params + gclid per touchpoint, no PII, no money).
  This is where channels like **Lifull-connect** appear as a `utm_source`.
- `google-ads-offline-conversions-feed-rentumo-<market>.csv` — Google Ads
  offline-conversion import rows with **Conversion Value (money), per-market
  currency**, Conversion Name, gclid and a **SHA-256-hashed** email.

**Privacy:** the CSV email is hashed and the tools **never** return raw rows or any
email — output is always aggregated (counts, value, breakdowns).

**What we deploy:** the FastMCP server in this repo at
[`rentumo-conversions-mcp/`](./rentumo-conversions-mcp/). Four tools:
`conversions_list_markets`, `conversions_get_attribution` (counts by a UTM
dimension, first vs last touch), `conversions_get_offline_summary` (counts + value
by source / conversion name), `conversions_get_source` (one channel across both
feeds, e.g. Lifull-connect).

> **Where it runs:** the Hetzner box as a Docker Compose service in
> `mcp-stack/compose.conversions.yaml` (project `madminds-conversions`) behind
> **Tailscale Funnel** — its own container + tunnel sidecar, separate from the
> Meta (`madminds-mcp`), Google (`madminds-google`) and Rentumo-Trials
> (`madminds-rentumo`) projects.
> Live URL (SSE): `https://rentumo-conversions.tail40453d.ts.net/sse`. Health:
> `https://rentumo-conversions.tail40453d.ts.net/health`.

---

## Step 1 — Secrets

**None.** The feeds are public, so there is no token to set and no `*.env` for this
connector's app container. The 26 Rentumo market codes + feed slugs are **bundled**
in the image (`rentumo-conversions-mcp/src/rentumo_conversions_mcp/markets.json`,
no secrets) — nothing to seed. The Tailscale sidecar reuses the same
`mcp-stack/tailscale.env` (`TS_AUTHKEY`) as the other stacks.

---

## Step 2 — Deploy

```bash
cd ~/Mad-Minds/mcp-stack && git pull
docker compose -f compose.conversions.yaml up -d --build
```
Use the `-f compose.conversions.yaml` / `madminds-conversions` project so you never
recreate the Meta, Google, or Rentumo-Trials containers.

Verify: `curl https://rentumo-conversions.tail40453d.ts.net/health` →
`{"status":"healthy","brand":"Rentumo (only)","markets_loaded":26,...}`. In a Cowork
session, ask "list Rentumo conversion markets", then "how many conversions did
Lifull-connect drive for Rentumo FR last month, and what were they worth".

---

## Markets / feed rotation

- **Add/change a market or feed slug:** edit the bundled
  `rentumo-conversions-mcp/src/rentumo_conversions_mcp/markets.json`, commit, then
  `git pull && docker compose -f compose.conversions.yaml up -d --build`. (Or
  override via a `/data/markets.json` + `RENTUMO_CONV_MARKETS_FILE` with just a
  `restart`.)
- **If the feed location/naming ever changes:** override
  `RENTUMO_CONV_FEED_BASE_URL` / `RENTUMO_CONV_UTM_TEMPLATE` /
  `RENTUMO_CONV_OFFLINE_TEMPLATE` in the compose `environment:` block and redeploy.
- **If the public connector URL ever changes:** bump the `onlineminds-marketing`
  plugin version and update the `rentumo-conversions` entry in
  `onlineminds-marketing/.mcp.json` + `CONNECTORS.md` so marketers get the new URL.

Markets whose feed isn't generated upstream yet (currently **UK** and **BR**, which
return 403) surface a friendly per-market "feed not available" error rather than
failing the call.

## Safety

Read-only by construction — the server has no write path, so the Tier 1 / Tier 2
spend-gate does not apply. There is no secret at all. Emails in the source CSV are
hashed and never leave the server; all tool output is aggregated.
