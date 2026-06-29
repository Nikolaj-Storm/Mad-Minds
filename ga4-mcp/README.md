# ga4-mcp — Google Analytics (GA4) connector

The Analytics sibling of `gads-mcp` and `gsc-mcp`. Per-user Google OAuth via
FastMCP's `GoogleProvider` (marketers sign in once; tokens persist on the `/data`
volume). Reached at `https://ga4.<tailnet>.ts.net/mcp`. GA4 is reporting-only, so
every tool is **read-only**.

## Tools

| Tool | Returns |
|---|---|
| `list_properties` | GA4 properties the signed-in account can read (numeric `property_id`s) |
| `get_traffic` | sessions / users / engagement by channel, source/medium, country, device, date… |
| `get_top_pages` | most-viewed pages with users + engagement time |
| `get_conversions` | key events by event name (count + revenue) |
| `get_report` | arbitrary dimensions + metrics (escape hatch) |
| `get_realtime` | activity in the last ~30 minutes |

Dates accept ISO `YYYY-MM-DD` or GA4 relative tokens (`today`, `yesterday`,
`NdaysAgo`, e.g. `28daysAgo`). Default window is the last 28 days.

## Layout

```
ga4-mcp/
  Dockerfile
  requirements.txt
  src/mcp_ga4/
    __init__.py
    server.py     # FastMCP app; auth auto-loaded from FASTMCP_SERVER_AUTH_* env
    run.py        # ASGI entrypoint: mcp.http_app(path="/mcp")
    tools.py      # the read-only reporting tools (async, FastMCP Context)
    service.py    # wraps the per-user OAuth token in google-auth Credentials
    utils.py      # date/name validation, error formatting
```

## Wiring (already done in this repo)

- Service `ga4-mcp` + `tailscale-ga4` sidecar added to `mcp-stack/compose.google.yaml`.
- `mcp-stack/tailscale/serve-ga4.json` funnels `https://ga4.<tailnet>.ts.net` → `ga4-mcp:8000`.
- `mcp-stack/google.env.example` documents the GA4 scope line.

## Deploy (on the server, as `mcp`)

1. **Google Cloud** (the OAuth client behind this server):
   - Enable the **Analytics Data API** and **Analytics Admin API**.
   - Add redirect URI `https://ga4.<your-tailnet>.ts.net/auth/callback`.
2. `cd ~/Mad-Minds/mcp-stack && cp google.env.example ga4.env`, then in `ga4.env`:
   - `FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID` / `_CLIENT_SECRET`
   - `FASTMCP_SERVER_AUTH_GOOGLE_REQUIRED_SCOPES=openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/analytics.readonly`
   - `FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL=https://ga4.<your-tailnet>.ts.net`
   - `CLIENT_STORAGE_DIR=/data`, `JWT_SIGNING_KEY=<openssl rand -hex 32>`
   - delete the `GOOGLE_ADS_*` / `READONLY_MODE` lines (Ads-only).
3. `docker compose -f compose.google.yaml up -d --build ga4-mcp tailscale-ga4`
4. Marketers connect to `https://ga4.<your-tailnet>.ts.net/mcp` and sign in with Google once.
   Verify with `list_properties` → `get_traffic`.
