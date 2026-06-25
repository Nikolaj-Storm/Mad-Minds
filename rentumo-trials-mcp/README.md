# Rentumo Trials MCP

A small, read-only MCP server that reports **new subscribers (trials)** per Rentumo
market, so Mad Minds can track subscriber growth alongside ad spend.

It wraps each market's admin endpoint:

```
GET https://{domain}/api/admin/charts?start_date={D. M. YYYY}&end_date={D. M. YYYY}
Authorization: Bearer {RENTUMO_BEARER_TOKEN}
```

and reads `.totals` — surfacing `new_subscriptions` as a first-class field while
returning the full `totals` object for any other KPIs the endpoint exposes.

## Auth model — shared bearer (like Thribee, NOT per-user OAuth)

A single admin bearer token works across every market's domain, so it stays a
**server-side secret** and the connector is **pre-wired in the plugin** (`.mcp.json`)
with no marketer Connect step — exactly the Thribee pattern. There is **no write
path**: the server only issues `GET` requests, so it never touches the `/ad-actions`
spend-gate.

## Tools

| Tool | What it does |
|---|---|
| `rentumo_list_markets` | List market codes + admin domains. Call first. |
| `rentumo_get_trials(market, start_date, end_date)` | New subscribers for one market. |
| `rentumo_get_all_trials(start_date, end_date)` | All markets in parallel → per-market breakdown + portfolio total. |

Dates are ISO `YYYY-MM-DD`; the server converts to the admin API's quirky
`"25. 6. 2026"` format and URL-encodes it.

## Configuration

Two server-side inputs, neither committed:

| Input | How | Notes |
|---|---|---|
| `RENTUMO_BEARER_TOKEN` | env var (`rentumo.env`) | The shared admin bearer. Rotate by redeploying. |
| `markets.json` | mounted at `/data/markets.json` | The 26 market codes + admin domains. See `markets.example.json` for the schema; pull real values from the spotlight-refresh project's account maps. |

Optional tuning: `RENTUMO_MARKETS_FILE` (default `/data/markets.json`),
`RENTUMO_MAX_CONCURRENCY` (default `12`), `RENTUMO_REQUEST_TIMEOUT` (default `30`).

## Deploy (Hetzner box, Docker Compose + Tailscale Funnel)

Runs as its own compose project (`madminds-rentumo`) so `up`/`down` never recreates
the Meta / Google / Thribee containers.

```bash
cd ~/Mad-Minds/mcp-stack
cp rentumo.env.example rentumo.env     # paste RENTUMO_BEARER_TOKEN
# put the real markets.json on the rentumo_data volume (see runbook)
docker compose -f compose.rentumo.yaml up -d --build
```

This serves `https://rentumo-trials.<tailnet>.ts.net/sse`, which is the SSE URL
pre-wired in `onlineminds-marketing/.mcp.json`. Health check:
`https://rentumo-trials.<tailnet>.ts.net/health`.

Local smoke test:

```bash
pip install -r requirements.txt
RENTUMO_BEARER_TOKEN=xxx RENTUMO_MARKETS_FILE=./markets.json \
  fastmcp run src/rentumo_trials_mcp/server.py --transport sse --port 8000
```
