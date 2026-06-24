# Google Ads — self-hosted connector runbook (maintainer only)

Same pattern as GSC: **you host it once**, marketers click **Connect → sign in with Google**, nothing on their laptops. Per-user (each sees only their own accounts). Deploys the corrected server in `gads-mcp/`.

**The one prerequisite that gates real data:** a Google Ads API **developer token** at **Basic Access** (yours or a colleague's — one covers the whole org). You can deploy and connect *before* it's approved; reads/writes just won't return live data until the token is in.

> **Deploy target (current): the Hetzner box.** Google Ads runs on the box
> (`mcp@37.27.23.202`) as a Docker Compose service in `mcp-stack/compose.google.yaml`
> (project `madminds-google`) behind Tailscale Funnel — its own container, disk-backed
> token storage at `/data`. Live URL: `https://gads.tail40453d.ts.net/mcp`. See
> **"Deploy on the box"** just below. The **Vercel** section (Redis/KV storage) and
> the **Fly.io** steps further down are documented **alternatives**; the server code
> auto-selects token storage from env vars (`KV_REST_API_*` → Redis, else
> `CLIENT_STORAGE_DIR` → disk).

---

## Deploy on the box (current path)

Two containers (gads + gsc) live in `mcp-stack/compose.google.yaml`, project
`madminds-google`, separate from Meta's `madminds-mcp` so `up` never touches Meta.
Each MCP has its own Tailscale Funnel sidecar (`tailscale-gads` → `gads.<tailnet>`).

```bash
cd ~/Mad-Minds/mcp-stack
# gads.env: FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID/SECRET/SCOPES,
#   FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL=https://gads.tail40453d.ts.net,
#   CLIENT_STORAGE_DIR=/data, JWT_SIGNING_KEY, GOOGLE_ADS_DEVELOPER_TOKEN, READONLY_MODE=true
docker compose -f compose.google.yaml up -d --build
docker compose -f compose.google.yaml exec -T tailscale-gads tailscale funnel status
curl -s https://gads.tail40453d.ts.net/health
```
Add `https://gads.tail40453d.ts.net/auth/callback` as a redirect URI on the Google
OAuth client (Step 1). Rotating the secret: edit `gads.env`, then
`docker compose -f compose.google.yaml up -d`.

---

## Deploy to Vercel (alternative)

Mirrors `META-SELF-HOST-RUNBOOK.md` → "Alternative: deploy to Vercel". One
serverless project; token storage in Vercel KV (Upstash Redis), so no volume.

### V1. Create the Vercel project
In [vercel.com/new](https://vercel.com/new), import `Nikolaj-Storm/Mad-Minds`:
- **Project name** → `onlineminds-gads-mcp` (→ `https://onlineminds-gads-mcp.vercel.app`)
- **Root Directory** → `gads-mcp` (where `vercel.json` lives)
- Framework preset → **Other** (Vercel detects `@vercel/python` from `vercel.json`)

### V2. Attach a Vercel KV store
In the project: **Storage → Create → KV** (Upstash Redis), name it
`kv-gads`. Vercel auto-injects `KV_REST_API_URL` + `KV_REST_API_TOKEN` — the
server picks these up to replace the disk store. (Use a **separate** KV store
per server; don't share one across gads/gsc/meta.)

### V3. Set environment variables (Settings → Environment Variables)
Same values as the Fly `secrets set` in Step 2 below, **minus** `CLIENT_STORAGE_DIR`
(no volume on Vercel), with the base URL pointed at the Vercel domain:
```ini
FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.google.GoogleProvider
FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID=NEW_ADS_CLIENT_ID.apps.googleusercontent.com
FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET=GOCSPX-NEW_ADS_SECRET
FASTMCP_SERVER_AUTH_GOOGLE_REQUIRED_SCOPES=openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/adwords
# Set AFTER the first deploy so you know the exact URL, then redeploy:
FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL=https://onlineminds-gads-mcp.vercel.app
JWT_SIGNING_KEY=<output of: openssl rand -hex 32>
GOOGLE_ADS_DEVELOPER_TOKEN=YOUR_BASIC_ACCESS_DEV_TOKEN
READONLY_MODE=true
# Optional, if accounts sit under a manager (MCC):
# GOOGLE_ADS_LOGIN_CUSTOMER_ID=1234567890
# KV_REST_API_URL and KV_REST_API_TOKEN are injected automatically by Vercel KV.
```
Keep `JWT_SIGNING_KEY` stable across redeploys or everyone has to re-Connect.

### V4. Update the Google OAuth client redirect URI
In the same Google Cloud OAuth client (Step 1), add the Vercel callback:
- **Authorized redirect URI:** `https://onlineminds-gads-mcp.vercel.app/auth/callback`
- **JS origin:** `https://onlineminds-gads-mcp.vercel.app`

You can keep the old `…fly.dev` URIs until the Fly app is decommissioned. (The
consent screen is **Internal**, so a `*.vercel.app` redirect needs no domain
verification.)

### V5. Deploy + verify
Click **Deploy**, then:
```bash
curl -s https://onlineminds-gads-mcp.vercel.app/health
# → {"status":"healthy","service":"Google Ads MCP"}
curl -s https://onlineminds-gads-mcp.vercel.app/.well-known/oauth-authorization-server | python3 -m json.tool
npx @modelcontextprotocol/inspector https://onlineminds-gads-mcp.vercel.app/mcp
```
In Inspector: sign in with Google → `list_accounts`, then `get_campaigns`.

### V6. Wire into the plugin
In `onlineminds-marketing/.mcp.json`, update the `_custom_connectors_note`
Google Ads URL to `https://onlineminds-gads-mcp.vercel.app/mcp`, bump the plugin
version, commit + push. CONNECTORS.md is already updated to the Vercel URL.

<a name="decommissioning-fly"></a>
### V7. Decommission the Fly app (after the Vercel connector is verified)
```bash
fly apps destroy onlineminds-gads-mcp   # also removes the gads_data volume
```
Remove the old `…fly.dev` redirect URI from the Google OAuth client. The
`gads-mcp/fly.toml` + `Dockerfile` stay in the repo as the documented
disk-storage / container fallback.

---

## Step 1 — Google OAuth client (reuse your GSC Cloud project)
In the same Google Cloud project you used for GSC:
1. **APIs & Services → Library →** enable **Google Ads API**.
2. **OAuth consent screen** (already Internal from GSC) → **Add scope** `https://www.googleapis.com/auth/adwords`.
3. **Credentials → Create Credentials → OAuth client ID → Web application**, name `Mad Minds Google Ads MCP`:
   - **Authorized redirect URI:** `https://onlineminds-gads-mcp.fly.dev/auth/callback`
   - **JS origin:** `https://onlineminds-gads-mcp.fly.dev`
4. Copy this client's **Client ID** and **Client Secret** (a *new* pair, separate from GSC).

## Step 2 — Create the Fly app, volume, secrets
```bash
cd ~/Desktop/2onlineminds-marketing-marketplace/gads-mcp
fly apps create onlineminds-gads-mcp
fly volumes create gads_data --region ams --size 1 -a onlineminds-gads-mcp -y
fly secrets set \
  FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.google.GoogleProvider \
  FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID="NEW_ADS_CLIENT_ID.apps.googleusercontent.com" \
  FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET="GOCSPX-NEW_ADS_SECRET" \
  FASTMCP_SERVER_AUTH_GOOGLE_REQUIRED_SCOPES="openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/adwords" \
  FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL="https://onlineminds-gads-mcp.fly.dev" \
  CLIENT_STORAGE_DIR=/data \
  JWT_SIGNING_KEY="$(openssl rand -hex 32)" \
  GOOGLE_ADS_DEVELOPER_TOKEN="YOUR_BASIC_ACCESS_DEV_TOKEN" \
  -a onlineminds-gads-mcp
# Optional, if accounts sit under a manager (MCC) and need login-customer-id:
# fly secrets set GOOGLE_ADS_LOGIN_CUSTOMER_ID=1234567890 -a onlineminds-gads-mcp
```
> No dev token yet? Set a placeholder for now; the server still deploys and the Google sign-in works. Add the real token with `fly secrets set GOOGLE_ADS_DEVELOPER_TOKEN=... -a onlineminds-gads-mcp` when it's approved — it redeploys automatically.

## Step 3 — Deploy + force always-on
```bash
fly deploy --remote-only --ha=false -a onlineminds-gads-mcp
fly status -a onlineminds-gads-mcp
```
Confirm STATE = `started`. (Same trial-machine note as GSC: a card on the Fly account keeps it from idling off.)

## Step 4 — Verify
```bash
curl -s https://onlineminds-gads-mcp.fly.dev/.well-known/oauth-authorization-server | python3 -m json.tool
npx @modelcontextprotocol/inspector https://onlineminds-gads-mcp.fly.dev/mcp
```
In Inspector: sign in with Google → run **`list_accounts`** (should list your accessible accounts), then **`get_campaigns`**. With `READONLY_MODE=true`, write tools simulate.

## Step 5 — Wire into the plugin
Add to `onlineminds-marketing/.mcp.json` under `mcpServers`:
```json
"google-ads": {
  "type": "http",
  "url": "https://onlineminds-gads-mcp.fly.dev/mcp"
}
```
Commit + push. Marketers connect it with one Google sign-in via `/setup-marketing`.

## Going live with writes
Reads + simulated writes work with `READONLY_MODE=true`. When you're ready for real writes (still gated by `/ad-actions`): `fly secrets set READONLY_MODE=false -a onlineminds-gads-mcp`.
