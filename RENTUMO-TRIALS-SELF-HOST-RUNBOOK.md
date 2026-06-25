# Rentumo Trials — self-hosted connector runbook (maintainer only)

**Goal:** one read-only connector that surfaces **new subscribers (trials) per Rentumo
market** inside Mad Minds, so the team can read subscriber growth next to ad spend.
It is **pre-wired** in the plugin — marketers do nothing, the same as Thribee.

**How it works (the important part):** unlike Google/Meta (per-user OAuth), Rentumo's
admin API uses a **single shared admin bearer token that works across every market's
domain**. So there is no per-user sign-in: the token stays a **server-side secret** and
the connector ships pre-wired in `onlineminds-marketing/.mcp.json`. The server is
**read-only** — it only issues `GET` requests, so it never touches the `/ad-actions`
spend-gate.

**What we deploy:** the FastMCP server in this repo at [`rentumo-trials-mcp/`](./rentumo-trials-mcp/).
It wraps each market's `GET /api/admin/charts`, reads `.totals`, and surfaces
`new_subscriptions`. Three tools: `rentumo_list_markets`, `rentumo_get_trials`
(one market), `rentumo_get_all_trials` (all markets in parallel + portfolio total).

> **Where it runs:** the Hetzner box as a Docker Compose service in
> `mcp-stack/compose.rentumo.yaml` (project `madminds-rentumo`) behind **Tailscale
> Funnel** — its own container + tunnel sidecar, separate from the Meta
> (`madminds-mcp`) and Google (`madminds-google`) projects.
> Live URL (SSE): `https://rentumo-trials.tail40453d.ts.net/sse`. Health:
> `https://rentumo-trials.tail40453d.ts.net/health`.

---

## Step 1 — The one secret you need

**`RENTUMO_BEARER_TOKEN`** — the shared admin bearer. It's the same token the
`spotlight-refresh` project keeps in `secrets.json` under `RENTUMO_BEARER_TOKEN`,
and the same one used in the Make/Integromat "Marketing dashboard data flow"
blueprint (the `Authorization: Bearer …` header on the Rentumo backend API call).

The **26 market domains are already bundled** in the image
(`rentumo-trials-mcp/src/rentumo_trials_mcp/markets.json`, public domains, no
secrets) — nothing to seed.

---

## Step 2 — Configure `rentumo.env` on the box

`rentumo.env` lives next to `mcp-stack/compose.rentumo.yaml`. Template:
`mcp-stack/rentumo.env.example`.
```ini
RENTUMO_BEARER_TOKEN=<shared admin bearer>
# RENTUMO_MAX_CONCURRENCY=12
# RENTUMO_REQUEST_TIMEOUT=30
```
That's the whole file. (To override the bundled market list without rebuilding,
put a `markets.json` on the `/data` volume and add `RENTUMO_MARKETS_FILE=/data/markets.json`.)

---

## Step 3 — Deploy

```bash
cd ~/Mad-Minds/mcp-stack && git pull
cp rentumo.env.example rentumo.env   # then paste the token
docker compose -f compose.rentumo.yaml up -d --build
```
Use the `-f compose.rentumo.yaml` / `madminds-rentumo` project so you never recreate
the Meta or Google containers.

Verify: `curl https://rentumo-trials.tail40453d.ts.net/health` →
`{"status":"healthy","markets_loaded":26,"token_present":true}`. In a Cowork session,
ask "list Rentumo markets" then "how many new subscribers did Rentumo get last week".

---

## Token / markets rotation

- **Rotate the bearer:** edit `rentumo.env`, then
  `docker compose -f compose.rentumo.yaml up -d` (no rebuild needed).
- **Add/change a market:** edit the bundled
  `rentumo-trials-mcp/src/rentumo_trials_mcp/markets.json`, commit, then
  `git pull && docker compose -f compose.rentumo.yaml up -d --build`. (Or override
  via a `/data/markets.json` + `RENTUMO_MARKETS_FILE` with just a `restart`.)
- **If the public URL ever changes:** bump the `onlineminds-marketing` plugin version
  and update the `rentumo-trials` entry in `onlineminds-marketing/.mcp.json` +
  `CONNECTORS.md` so marketers get the new URL.

## Safety

Read-only by construction — the server has no write path, so the Tier 1 / Tier 2
spend-gate does not apply. The bearer is a server secret; it never appears in any hub
file, report, or the repo.
