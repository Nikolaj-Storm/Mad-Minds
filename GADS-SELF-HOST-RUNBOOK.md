# Google Ads — self-hosted connector runbook (maintainer only)

Same pattern as GSC: **you host it once**, marketers click **Connect → sign in with Google**, nothing on their laptops. Per-user (each sees only their own accounts). Runs the corrected server in `gads-mcp/`.

**The one prerequisite that gates real data:** a Google Ads API **developer token** at **Basic Access** (yours or a colleague's — one covers the whole org). You can deploy and connect *before* it's approved; reads/writes just won't return live data until the token is in.

> **Where it runs:** the Hetzner box as a Docker Compose service in
> `mcp-stack/compose.google.yaml` (project `madminds-google`) behind **Tailscale
> Funnel** — its own container, disk-backed token storage at `/data`.
> Live URL: `https://gads.tail40453d.ts.net/mcp`.

---

## Step 1 — Google OAuth client (reuse the GSC Cloud project)
In the same Google Cloud project you used for GSC:
1. **APIs & Services → Library →** enable **Google Ads API**.
2. **OAuth consent screen** (already **Internal** from GSC) → **Add scope** `https://www.googleapis.com/auth/adwords`.
3. **Credentials → Create Credentials → OAuth client ID → Web application**, name `Mad Minds Google Ads MCP`:
   - **Authorized redirect URI:** `https://gads.tail40453d.ts.net/auth/callback`
   - **JS origin:** `https://gads.tail40453d.ts.net`
4. Copy this client's **Client ID** and **Client Secret** (a *new* pair, separate from GSC). The client supports multiple secrets, so you can rotate without downtime via **Add secret**.

## Step 2 — Configure `gads.env` on the box
`gads.env` lives next to `mcp-stack/compose.google.yaml`. Template: `mcp-stack/google.env.example`.
```ini
FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.google.GoogleProvider
FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID=YOUR_ADS_CLIENT_ID.apps.googleusercontent.com
FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET=GOCSPX-YOUR_ADS_SECRET
FASTMCP_SERVER_AUTH_GOOGLE_REQUIRED_SCOPES=openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/adwords
FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL=https://gads.tail40453d.ts.net
CLIENT_STORAGE_DIR=/data
JWT_SIGNING_KEY=<openssl rand -hex 32>
GOOGLE_ADS_DEVELOPER_TOKEN=YOUR_BASIC_ACCESS_DEV_TOKEN
READONLY_MODE=true
# Optional, if accounts sit under a manager (MCC):
# GOOGLE_ADS_LOGIN_CUSTOMER_ID=1234567890
```
> No dev token yet? Use a placeholder — the server still boots and Google sign-in works; reads just return no data until the real token is in. Add it later and `docker compose -f compose.google.yaml up -d`.

## Step 3 — Deploy on the box
`gads-mcp` shares the `madminds-google` project with `gsc-mcp`, separate from Meta's `madminds-mcp`, so `up` never touches Meta or Thribee. Each MCP has its own Tailscale Funnel sidecar (`tailscale-gads` → `gads.<tailnet>`).
```bash
cd ~/Mad-Minds/mcp-stack
docker compose -f compose.google.yaml up -d --build
docker compose -f compose.google.yaml exec -T tailscale-gads tailscale funnel status
curl -s https://gads.tail40453d.ts.net/health        # → {"status":"healthy","service":"Google Ads MCP"}
```
Rotating the secret later: edit `gads.env`, then `docker compose -f compose.google.yaml up -d`.

## Step 4 — Verify the OAuth handshake
```bash
curl -s https://gads.tail40453d.ts.net/.well-known/oauth-authorization-server | python3 -m json.tool
npx @modelcontextprotocol/inspector https://gads.tail40453d.ts.net/mcp
```
In Inspector: sign in with Google → run **`list_accounts`** (lists accessible accounts), then **`get_campaigns`**. With `READONLY_MODE=true`, write tools simulate.

## Step 5 — Wire into the plugin
Google Ads is a **custom connector**, not wired in `.mcp.json` (Claude desktop's in-session OAuth flow is buggy). Marketers add it via `/setup-marketing` with the URL `https://gads.tail40453d.ts.net/mcp`. The URL is already listed in `CONNECTORS.md` and the `_custom_connectors_note`.

## Going live with writes
Reads + simulated writes work with `READONLY_MODE=true`. When you're ready for real writes (still gated by `/ad-actions`): set `READONLY_MODE=false` in `gads.env` and `docker compose -f compose.google.yaml up -d`.

---

## Alternative: deploy to Vercel
If you ever want serverless instead of the box, `gads-mcp/` ships a `vercel.json` + `api/index.py`. Import `Nikolaj-Storm/Mad-Minds` at [vercel.com/new](https://vercel.com/new) with **Root Directory** `gads-mcp`, attach a **Vercel KV** store (auto-injects `KV_REST_API_URL` + `KV_REST_API_TOKEN` — the server uses Redis instead of disk), set the same env vars as Step 2 minus `CLIENT_STORAGE_DIR`, point `FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL` at the `*.vercel.app` URL, and add that URL's `/auth/callback` to the OAuth client. The box is the current production path; this is just a documented fallback.
