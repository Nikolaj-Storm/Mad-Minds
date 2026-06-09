# Google Ads — self-hosted connector runbook (maintainer only)

Same pattern as GSC: **you host it once**, marketers click **Connect → sign in with Google**, nothing on their laptops. Per-user (each sees only their own accounts). Deploys the corrected server in `gads-mcp/`.

**The one prerequisite that gates real data:** a Google Ads API **developer token** at **Basic Access** (yours or a colleague's — one covers the whole org). You can deploy and connect *before* it's approved; reads/writes just won't return live data until the token is in.

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
