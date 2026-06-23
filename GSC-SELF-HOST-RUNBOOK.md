# Google Search Console — self-hosted connector runbook (maintainer only)

**Goal:** one GSC connector that **you host once**, and every marketer just clicks **Connect → sign in with Google → done.** No pasting, no Google Cloud, no per-person setup on their side. Each marketer only ever sees the GSC properties their own Google account already has.

**How it works (the important part):** we deploy a small server that acts as the **OAuth broker**. It holds the Google client secret *server-side* and presents a standard Connect handshake to Claude — the same self-hosted, per-user pattern as our Google Ads and Meta Ads connectors. That's what makes it zero-setup for colleagues. (The earlier draft used a server that delegated auth to Google, which forced each marketer to paste a Client ID/Secret — this version removes that.)

**What we deploy:** the **corrected, vendored** server in this repo at [`gsc-mcp/`](./gsc-mcp/) — a FastMCP server using the built-in [Google OAuth-proxy provider](https://gofastmcp.com/integrations/google). It started life as [`damupi/mcp-gsc-oauth`](https://github.com/damupi/mcp-gsc-oauth) (MIT), but that repo **does not run as published** — testing found three defects (a token bug that 401s every GSC call, plus two FastMCP-3 incompatibilities that stop it booting). All three are fixed in `gsc-mcp/`; see `gsc-mcp/NOTICE.md`. 13 GSC tools: search analytics, URL inspection, sitemaps, site listing.

> **Tested before shipping:** in a sandbox the fixed server boots clean, and its OAuth layer was verified end-to-end short of a real Google login — `/register` (Dynamic Client Registration) returns a `client_id`, PKCE `S256` is advertised, and unauthenticated calls get a 401 challenge. That's exactly what Claude's Connect button needs. The only unproven hop is the live Google-sign-in → GSC-data round-trip, which you confirm once with MCP Inspector in Step 3.

> Everything below is done **once, by you.** Total time ~30 min. Colleagues do nothing until the final "what marketers see" section.

---

## Maintainer prerequisites
- A Google Cloud project (billing enabled — the API calls are free, billing is just required to create an OAuth client).
- A Fly.io account: `brew install flyctl` then `fly auth login`. (Render works too — notes at the end.)
- Fly builds the image remotely, so no local Docker needed.

---

## Step 1 — Create ONE Google OAuth client (server-side, ~10 min)
This is the credential the *server* uses. It is never shown to marketers.

1. **Enable the API:** `gcloud services enable searchconsole.googleapis.com webmasters.googleapis.com --project=YOUR_PROJECT_ID` (or console: APIs & Services → Library → "Search Console API" → Enable).
2. **OAuth consent screen:** APIs & Services → OAuth consent screen → **Internal** (so only `@onlineminds.io` accounts can sign in — no test-user list, no Google verification). Add scope `https://www.googleapis.com/auth/webmasters.readonly` (read-only — see safety note).
3. **Create credentials:** Credentials → Create Credentials → **OAuth client ID** → **Web application**, name it `Mad Minds GSC MCP`.
   - **Authorized JavaScript origins:** `https://onlineminds-gsc-mcp.fly.dev`
   - **Authorized redirect URI:** `https://onlineminds-gsc-mcp.fly.dev/auth/callback`
     ⚠️ This is the **server's** callback (`base_url` + `/auth/callback`), **not** `claude.ai`. That's the whole point — the server, not Claude, talks to Google.
   - (Use whatever Fly app name you'll pick in Step 2; the two must match. You can come back and edit these URIs after you know the URL.)
4. Copy the **Client ID** (`…apps.googleusercontent.com`) and **Client Secret** (`GOCSPX-…`). These go into Fly secrets, not the repo.

---

## Step 2 — Deploy to Fly.io (~10 min)
Deploy the corrected server that's already in this repo — no cloning, the `Dockerfile` and `fly.toml` are included.
```bash
cd gsc-mcp        # the vendored, fixed server in this repo

# Create the app (don't deploy yet). The name must match the OAuth URIs from Step 1.
fly launch --no-deploy --name onlineminds-gsc-mcp
#   -> https://onlineminds-gsc-mcp.fly.dev
#   No Postgres needed. Keep the included Dockerfile + fly.toml (internal_port 8000).

# Set the server-side config as Fly secrets (NOT committed anywhere).
fly secrets set \
  FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.google.GoogleProvider \
  FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID="YOUR_ID.apps.googleusercontent.com" \
  FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET="GOCSPX-YOUR_SECRET" \
  FASTMCP_SERVER_AUTH_GOOGLE_REQUIRED_SCOPES="openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/webmasters.readonly" \
  FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL="https://onlineminds-gsc-mcp.fly.dev"

fly deploy --remote-only
```

**Persistence — REQUIRED so marketers sign in once, ever.** Without it, the OAuth proxy keeps clients/tokens in memory, so any restart or redeploy logs everyone out. This server persists all OAuth state (registered clients, Google tokens, refresh tokens) to a disk-backed store when you provide a `CLIENT_STORAGE_DIR` + a stable `JWT_SIGNING_KEY`. The `fly.toml` already mounts a volume at `/data`. Create the volume and set the two extra secrets:
```bash
fly volumes create gsc_data --region ams --size 1 -a onlineminds-gsc-mcp -y
fly secrets set CLIENT_STORAGE_DIR=/data JWT_SIGNING_KEY="$(openssl rand -hex 32)" -a onlineminds-gsc-mcp
```
Run a **single machine** (`fly scale count 1` + `--ha=false` on deploy): a Fly volume attaches to one machine, which is exactly what the shared OAuth registry needs. Verified in testing: the DiskStore is wired into all seven OAuth stores and survives a fresh process. After this, restarts/redeploys/idle never log anyone out.

---

## Step 3 — Verify the deployment (~2 min)
```bash
SERVICE_URL="https://onlineminds-gsc-mcp.fly.dev"

# OAuth metadata should exist (proves the proxy is live)
curl -s "$SERVICE_URL/.well-known/oauth-authorization-server" | python3 -m json.tool

# Inspect it interactively — this runs the full Connect + Google sign-in once, as you:
npx @modelcontextprotocol/inspector "$SERVICE_URL/mcp"
```
In the Inspector, you should be bounced to Google, sign in, land back, and then be able to call `list_sites` and see your own GSC properties. If that works, Claude will too.

---

## Step 4 — Wire it into the plugin (one line)
Because the server brokers OAuth, the plugin entry is just a URL — no marketer settings. Move the staged entry in `onlineminds-marketing/.mcp.json` from `_pending_connectors` into `mcpServers`:
```json
"google-search-console": {
  "type": "http",
  "url": "https://onlineminds-gsc-mcp.fly.dev/mcp",
  "_comment": "Self-hosted GSC (damupi/mcp-gsc-oauth, FastMCP Google OAuth proxy). Server holds the Google secret; marketers just click Connect and sign in with Google. Per-user, read-only (webmasters.readonly)."
}
```
Then bump the plugin version, commit, push. Marketers get it on next plugin update.

---

## What your marketers see (the whole of their job)
1. Customize → **Onlineminds-marketing → Connectors** → **Google Search Console** → **Connect**.
2. A Google sign-in opens → they pick the Google account that has their brand's GSC.
3. Done. *"List my Search Console properties"* returns only their brands.

No URL, no Client ID, no secret, no Google Cloud. Exactly like signing into any app.

---

## Safety note — keep it read-only
Setting the scope to `webmasters.readonly` (above) means even though the server *exposes* `add_site` / `delete_site` / `submit_sitemap` / `delete_sitemap` tools, the Google token can't perform them — they'll 403. That keeps GSC analysis-only and outside the spend-gate, which is what you want. If you ever need write actions, switch the scope to `…/auth/webmasters` and treat those tools as Tier 2.

---

## This same recipe covers GA4 and GTM later
GA4 and Google Tag Manager are the *identical* pattern: same FastMCP Google OAuth-proxy server, just a different Google API client and scope (`analytics.readonly` for GA4, `tagmanager.*` for GTM). Once GSC is proven, standing those up is the same 30-minute recipe — so GTM (your remaining Tier-1 gap) and GA4 are unblocked by getting this one working.

---

## Render instead of Fly
Same container. Render → New → Web Service → your clone → Docker → set the same env vars, port `8000`, and `FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL` to your `…onrender.com` URL. Render's free tier cold-starts (~30s) on idle; Fly's scale-to-zero is snappier for an always-ready connector.
