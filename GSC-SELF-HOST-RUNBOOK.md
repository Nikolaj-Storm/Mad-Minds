# Google Search Console — self-hosted connector runbook (maintainer only)

**Goal:** one GSC connector that **you host once**, and every marketer just clicks **Connect → sign in with Google → done.** No pasting, no Google Cloud, no per-person setup on their side. Each marketer only ever sees the GSC properties their own Google account already has.

**How it works (the important part):** we deploy a small server that acts as the **OAuth broker**. It holds the Google client secret *server-side* and presents a standard Connect handshake to Claude — the same self-hosted, per-user pattern as our Google Ads and Meta Ads connectors. That's what makes it zero-setup for colleagues.

**What we deploy:** the **corrected, vendored** server in this repo at [`gsc-mcp/`](./gsc-mcp/) — a FastMCP server using the built-in [Google OAuth-proxy provider](https://gofastmcp.com/integrations/google). It started life as [`damupi/mcp-gsc-oauth`](https://github.com/damupi/mcp-gsc-oauth) (MIT), but that repo **does not run as published** — testing found three defects (a token bug that 401s every GSC call, plus two FastMCP-3 incompatibilities that stop it booting). All three are fixed in `gsc-mcp/`; see `gsc-mcp/NOTICE.md`. 13 GSC tools: search analytics, URL inspection, sitemaps, site listing.

> **Where it runs:** the Hetzner box as a Docker Compose service in
> `mcp-stack/compose.google.yaml` (project `madminds-google`) behind **Tailscale
> Funnel** — its own container, disk-backed token storage at `/data`, so marketers
> sign in once and survive restarts/redeploys.
> Live URL: `https://gsc.tail40453d.ts.net/mcp`.

---

## Step 1 — Create ONE Google OAuth client (server-side, ~10 min)
This is the credential the *server* uses. It is never shown to marketers.

1. **Enable the API:** `gcloud services enable searchconsole.googleapis.com webmasters.googleapis.com --project=YOUR_PROJECT_ID` (or console: APIs & Services → Library → "Search Console API" → Enable).
2. **OAuth consent screen:** APIs & Services → OAuth consent screen → **Internal** (so only `@onlineminds.io` accounts can sign in — no test-user list, no Google verification). Add scope `https://www.googleapis.com/auth/webmasters.readonly` (read-only — see safety note).
3. **Create credentials:** Credentials → Create Credentials → **OAuth client ID** → **Web application**, name it `Mad Minds GSC MCP`.
   - **Authorized JavaScript origins:** `https://gsc.tail40453d.ts.net`
   - **Authorized redirect URI:** `https://gsc.tail40453d.ts.net/auth/callback`
     ⚠️ This is the **server's** callback (`base_url` + `/auth/callback`), **not** `claude.ai`. The server, not Claude, talks to Google.
4. Copy the **Client ID** (`…apps.googleusercontent.com`) and **Client Secret** (`GOCSPX-…`). These go into `gsc.env` on the box, never the repo.

---

## Step 2 — Configure `gsc.env` on the box
`gsc.env` lives next to `mcp-stack/compose.google.yaml`. Template: `mcp-stack/google.env.example`.
```ini
FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.google.GoogleProvider
FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID=YOUR_ID.apps.googleusercontent.com
FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET=GOCSPX-YOUR_SECRET
FASTMCP_SERVER_AUTH_GOOGLE_REQUIRED_SCOPES=openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/webmasters.readonly
FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL=https://gsc.tail40453d.ts.net
CLIENT_STORAGE_DIR=/data
JWT_SIGNING_KEY=<openssl rand -hex 32>
```
`CLIENT_STORAGE_DIR=/data` + a stable `JWT_SIGNING_KEY` persist all OAuth state (registered clients, Google tokens, refresh tokens) to the container's disk volume — so restarts/redeploys never log anyone out.

## Step 3 — Deploy on the box
`gsc-mcp` shares the `madminds-google` project with `gads-mcp`, separate from Meta's `madminds-mcp`, so `up` never touches Meta or Thribee. Each MCP has its own Tailscale Funnel sidecar (`tailscale-gsc` → `gsc.<tailnet>`).
```bash
cd ~/Mad-Minds/mcp-stack
docker compose -f compose.google.yaml up -d --build
docker compose -f compose.google.yaml exec -T tailscale-gsc tailscale funnel status
curl -s https://gsc.tail40453d.ts.net/health
```

## Step 4 — Verify the OAuth handshake (~2 min)
```bash
SERVICE_URL="https://gsc.tail40453d.ts.net"
curl -s "$SERVICE_URL/.well-known/oauth-authorization-server" | python3 -m json.tool
npx @modelcontextprotocol/inspector "$SERVICE_URL/mcp"
```
In the Inspector you should be bounced to Google, sign in, land back, and be able to call `list_sites` and see your own GSC properties. If that works, Claude will too.

## Step 5 — Wire into the plugin
GSC is a **custom connector** (Claude desktop's in-session OAuth flow is buggy). Marketers add it via `/setup-marketing` with the URL `https://gsc.tail40453d.ts.net/mcp` — no Client ID/Secret to paste, the server brokers OAuth. The URL is already in `CONNECTORS.md` and the `_custom_connectors_note`.

---

## What your marketers see (the whole of their job)
1. Customize → **Connectors** → **Add custom connector** → paste `https://gsc.tail40453d.ts.net/mcp` → **Connect**.
2. A Google sign-in opens → they pick the Google account that has their brand's GSC.
3. Done. *"List my Search Console properties"* returns only their brands.

No Client ID, no secret, no Google Cloud. Exactly like signing into any app.

---

## Safety note — keep it read-only
Setting the scope to `webmasters.readonly` means even though the server *exposes* `add_site` / `delete_site` / `submit_sitemap` / `delete_sitemap` tools, the Google token can't perform them — they'll 403. That keeps GSC analysis-only and outside the spend-gate. If you ever need write actions, switch the scope to `…/auth/webmasters` and treat those tools as Tier 2.

## This same recipe covers GA4 and GTM later
GA4 and Google Tag Manager are the *identical* pattern: same FastMCP Google OAuth-proxy server, just a different Google API client and scope (`analytics.readonly` for GA4, `tagmanager.*` for GTM). Add them as two more services in `mcp-stack/compose.google.yaml` with their own Funnel sidecars — same recipe as GSC/Google Ads.

---

## Alternative: deploy to Vercel
`gsc-mcp/` ships a `vercel.json` + `api/index.py` if you ever want serverless instead of the box. Import `Nikolaj-Storm/Mad-Minds` at [vercel.com/new](https://vercel.com/new) with **Root Directory** `gsc-mcp`, attach a **Vercel KV** store (auto-injects `KV_REST_API_URL` + `KV_REST_API_TOKEN` — the server uses Redis instead of disk), set the Step 2 env vars minus `CLIENT_STORAGE_DIR`, point `FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL` at the `*.vercel.app` URL, and add that URL's `/auth/callback` to the OAuth client. The box is the current production path; this is just a documented fallback.
