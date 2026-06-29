# ga4-mcp — Google Analytics (GA4) connector for marketers

The Analytics sibling of the marketer `gads-mcp`. Humans use it through Claude
(Desktop or the Mad-Minds stack). Auth is **each marketer's own Google sign-in**
(OAuth, scope `analytics.readonly`). GA4 is reporting-only, so every tool is
**read-only** — there are no write/mutate tools.

> Counterpart: the `mad-minds-machine` repo has `ga4-ro`, the same tools but for
> autonomous "robot"/cron use behind a service account + shared bearer. This one is
> the human, per-user-OAuth version.

## Tools

| Tool | What it returns |
|---|---|
| `list_properties` | GA4 properties your Google account can read (numeric `property_id`s) |
| `get_traffic` | sessions / users / engagement by channel, source/medium, country, device, date… |
| `get_top_pages` | most-viewed pages with users + engagement time |
| `get_conversions` | key events by event name (count + revenue) |
| `get_report` | arbitrary dimensions + metrics (escape hatch) |
| `get_realtime` | activity in the last ~30 minutes |
| `server_status` | non-sensitive config health check |

Dates accept ISO `YYYY-MM-DD` or GA4 relative tokens (`today`, `yesterday`,
`NdaysAgo`, e.g. `28daysAgo`). Default window is the last 28 days.

## Auth wiring (important)

`src/ga4_mcp/client.py::get_credentials()` builds Google OAuth `Credentials` from
env vars (`GA4_OAUTH_CLIENT_ID`, `GA4_OAUTH_CLIENT_SECRET`, `GA4_OAUTH_REFRESH_TOKEN`)
so it runs standalone out of the box. **If Mad-Minds already injects each marketer's
Google token through a shared OAuth helper** (the way `gads-mcp` / the Google
connector do), replace the body of `get_credentials()` with a call into that helper
and keep everything else. Scope needed: `https://www.googleapis.com/auth/analytics.readonly`.

## Run it

**Claude Desktop (stdio).** Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "google-analytics": {
      "command": "python",
      "args": ["-m", "ga4_mcp"],
      "env": {
        "PYTHONPATH": "/abs/path/to/ga4-mcp/src",
        "GA4_OAUTH_CLIENT_ID": "...apps.googleusercontent.com",
        "GA4_OAUTH_CLIENT_SECRET": "...",
        "GA4_OAUTH_REFRESH_TOKEN": "...",
        "GA4_PROPERTY_ID": "123456789"
      }
    }
  }
}
```

**HTTP (Mad-Minds stack), like the other connectors:**

```bash
pip install -r requirements.txt
PYTHONPATH=src uvicorn ga4_mcp.run:app --host 0.0.0.0 --port 8000
# or: docker build -t madminds/ga4-mcp . && docker run -p 8000:8000 --env-file .env madminds/ga4-mcp
```

Wire it into the stack the same way `gads-mcp` is registered (compose service +
whatever plugin/connector manifest lists the marketer servers). If marketer
connectors sit behind a shared auth middleware, pass it in `run.py`'s
`mcp.http_app(..., middleware=[...])`.

## Setup checklist

- [ ] Enable the **Analytics Data API** and **Analytics Admin API** in the Google
      Cloud project behind the OAuth client.
- [ ] OAuth consent scope includes `analytics.readonly`.
- [ ] The signed-in Google account has at least **Viewer** on the GA4 properties.
- [ ] Verify: `server_status` → tokens present; `list_properties` → IDs; `get_traffic`
      → data.
