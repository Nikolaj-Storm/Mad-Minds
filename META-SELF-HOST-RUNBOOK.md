# Meta Ads — self-hosted connector runbook (maintainer only)

Same idea as the Google Ads MCP, but **Meta** and on **your own VPS with plain
Docker** instead of Fly. You host it once; marketers click **Connect → sign in
with Facebook**, nothing on their laptops. Per-user (each sees only the ad
accounts they already manage, across every Business Manager they belong to — so
**one URL serves all companies**, unlike the old per-BM `mcp.meta.com` URLs).

Deploys the server in `meta-ads-mcp/`. Replaces the previous "use Meta's official
hosted MCP" approach.

**Two prerequisites gate real data:**
1. A **Facebook App** (Business type) with **App ID + App Secret** — one app for
   the whole org, the server-side secret (the Meta analogue of the Google Ads
   developer token).
2. A **domain/subdomain pointed at the VPS** with **HTTPS**. Facebook OAuth and
   Claude custom connectors both require `https://`. We put **Caddy** in front
   (free auto-Let's-Encrypt cert); substitute your own reverse proxy if you have
   one.

You can deploy and Connect *before* everything's perfect — reads/writes just
won't return live data until the app + a marketer's Facebook access line up.

Throughout, replace `meta-mcp.example.com` with your real (sub)domain.

> **Running several MCPs on one box?** Use the Compose stack in **`mcp-stack/`**
> instead of the single `docker run` in Steps 5–6 — it runs each MCP as a service
> behind one shared Caddy proxy, so adding the next MCP is one service block. Same
> Facebook-app + DNS setup (Steps 1–2), same verify + wiring (Steps 7–8); only the
> "bring it up" part differs. See `mcp-stack/README.md`. This is the recommended
> path for the Hetzner `mcp@` host.

---

## Step 1 — Create the Meta App + Facebook Login

At <https://developers.facebook.com/apps> → **Create app**:
1. Type **Business**. Name it `Mad Minds Meta Ads MCP`.
2. **Add products → Marketing API** and **Facebook Login**. New "Business" apps
   only offer **Facebook Login for Business** (classic "Facebook Login" is
   retired) — that's fine, but it then needs the **App Domains** step (3) *and* a
   **Configuration / config_id** (step 5).
3. **App settings → Basic:** copy the **App ID** and **App Secret**, and add the
   server's **host** to the **App Domains** field — no scheme, no path, e.g.
   `meta-mcp.example.com`. Save. (Facebook validates the OAuth callback against
   **both** App Domains *and* the redirect URI in step 4; missing App Domains
   gives "Can't load URL — the domain of this URL isn't included in the app's
   domains" at Connect time. If it won't save without a **Privacy Policy URL**,
   any non-empty URL is fine in Development mode.)
4. **Facebook Login (for Business) → Settings → Valid OAuth Redirect URIs:** add
   `https://meta-mcp.example.com/auth/callback` (exactly — this must equal
   `META_OAUTH_BASE_URL` + `/auth/callback`). Save.
5. **(Facebook Login for Business only) → Configurations → Create configuration:**
   grant **ads_read + ads_management**, save, and copy the **Configuration ID**.
   Put it in that instance's env as `META_CONFIG_ID`. FLB carries permissions in
   the config, not in `scope`; without it the dialog redirects back with "Missing
   authorization code". (Skip only for classic Facebook Login, which uses `scope`.)

### The App-Review shortcut for an internal team (do this — saves weeks)
`ads_management` normally needs Meta **App Review** to be granted to users
outside your own Business — *except* for people who hold a **role on the app**.
So for an internal team, **don't submit for review**: instead add each marketer
as a **Tester** (or Developer):

- **App roles → Roles → Add People → Testers** → add silas, frederik, caroline,
  nilas, banin, karina, jacob, julius (they accept the invite once at
  developers.facebook.com). Add yourself as Admin.

Testers can grant `ads_read` + `ads_management` immediately, in Development mode,
for the accounts they manage. No review, no waiting. (Only submit for App Review
later if you ever need non-app-role / external users.) You can leave the app in
**Development** mode for this.

---

## Step 2 — Pick a domain + point it at the VPS

You need a stable HTTPS hostname for the server. You do **not** need to buy a
TLS certificate — Caddy (Step 6) gets one free from Let's Encrypt. You just need
a name that resolves to the VPS.

**Easiest (recommended): a subdomain of a domain OnlineMinds already owns.**
e.g. `meta-mcp.onlineminds.io`. No new purchase, no extra cost. If you'd rather
not touch the main domain's DNS, grab a throwaway domain for ~$10/yr at
Cloudflare / Namecheap / Porkbun and use that.

**Then add ONE DNS record** in whatever controls that domain's DNS (your
registrar or Cloudflare):

```
Type: A     Name: meta-mcp     Value: <your VPS public IPv4>     TTL: auto
```

- The VPS's public IP is shown in your provider's dashboard (Hetzner /
  DigitalOcean / Linode / Vultr…), or run `curl -4 ifconfig.me` on the box. Use
  the IPv4; add a matching `AAAA` record too if you want IPv6.
- "Name `meta-mcp`" + domain `onlineminds.io` → the host
  `meta-mcp.onlineminds.io`. Use whatever subdomain you like.
- If the domain is on **Cloudflare**, set the record to **DNS only** (grey
  cloud) for the first deploy so Caddy can complete the Let's Encrypt challenge;
  you can switch the proxy on afterwards.

Wait for it to resolve before Step 6 (`dig +short meta-mcp.onlineminds.io` should
return your VPS IP) so Caddy can get its certificate.

> This hostname is used in **three places that must match**: `META_OAUTH_BASE_URL`
> (Step 4), the Facebook app's **Valid OAuth Redirect URI** = `https://<host>/auth/callback`
> (Step 1), and the connector URL marketers paste = `https://<host>/mcp` (Step 8).
> Decide the hostname now and reuse it verbatim everywhere.

---

## Step 3 — Get the code on the VPS and build the image

```bash
git clone https://github.com/Nikolaj-Storm/Mad-Minds.git
cd Mad-Minds/meta-ads-mcp
docker build -t meta-ads-mcp .
```

## Step 4 — Write the secrets file

Create `meta.env` next to it (this file holds secrets — do NOT commit it; the
repo `.gitignore` already ignores `.env`):

```ini
META_APP_ID=1234567890
META_APP_SECRET=your_app_secret_here
META_OAUTH_BASE_URL=https://meta-mcp.example.com
META_SCOPES=ads_read,ads_management
# Pin to a currently-supported Graph API version; bump when Meta deprecates it:
META_GRAPH_VERSION=v21.0
CLIENT_STORAGE_DIR=/data
JWT_SIGNING_KEY=replace_with_output_of_openssl_rand_hex_32
# Safety: writes SIMULATE until you flip this to false (and they still go
# through the /ad-actions spend-gate even then). Reads work regardless.
READONLY_MODE=true
# Optional: a default ad account so marketers don't have to pass act_… every time
# META_AD_ACCOUNT_ID=act_1234567890
```

Generate the signing key: `openssl rand -hex 32`. It encrypts the on-disk token
store; keep it stable or everyone has to re-Connect.

## Step 5 — Run the MCP container (plain Docker)

```bash
docker network create web 2>/dev/null || true
docker run -d --name meta-ads-mcp --restart unless-stopped \
  --env-file meta.env \
  -v meta_data:/data \
  --network web \
  meta-ads-mcp
```

- `-v meta_data:/data` persists the OAuth token store (`CLIENT_STORAGE_DIR=/data`)
  across restarts, so marketers stay signed in.
- No `-p` needed: Caddy reaches it over the `web` network. (If you front it with
  your own proxy instead, add `-p 127.0.0.1:8000:8000` and point your proxy at
  `127.0.0.1:8000`.)

## Step 6 — HTTPS in front (Caddy, also plain Docker)

`Caddyfile`:

```
meta-mcp.example.com {
    reverse_proxy meta-ads-mcp:8000
}
```

```bash
docker run -d --name caddy --restart unless-stopped \
  --network web \
  -p 80:80 -p 443:443 \
  -v "$PWD/Caddyfile":/etc/caddy/Caddyfile \
  -v caddy_data:/data \
  caddy:2
```

Caddy fetches a Let's Encrypt cert automatically. (Already run nginx/Traefik?
Skip this and reverse-proxy `meta-mcp.example.com → 127.0.0.1:8000` yourself —
HTTPS is the only hard requirement.)

## Step 7 — Verify

```bash
curl -s https://meta-mcp.example.com/health
curl -s https://meta-mcp.example.com/.well-known/oauth-authorization-server | python3 -m json.tool
npx @modelcontextprotocol/inspector https://meta-mcp.example.com/mcp
```

`/health` returns `{"status":"healthy",...}`; the metadata advertises
`/authorize`, `/token`, `/register` (DCR) and PKCE. In Inspector: **Connect →
sign in with Facebook**, then run **`server_status`** (should show
`app_id_present: true`, `auth_configured: true`), **`list_ad_accounts`**, then
**`get_campaigns`**. With `READONLY_MODE=true`, the write tools simulate.

## Step 8 — Wire into the plugin (custom connector, like Google Ads)

Meta is delivered as a **custom connector** (not in `.mcp.json`), exactly like
Google Search Console and Google Ads — the plugin in-session OAuth flow is buggy
in Claude desktop, the custom-connector path (Claude's hosted callback) is the
reliable one. **One org-wide URL:**

```
https://meta-mcp.example.com/mcp
```

Each marketer: **Customize → Connectors → Add custom connector** → paste that URL
→ leave Advanced settings empty (DCR, so no Client ID/Secret) → **Add** →
**Connect** → **sign in with Facebook**. A new session may be needed for the
tools to appear. `/setup-marketing` walks them through it; `CONNECTORS.md` lists
the URL.

## Going live with writes

Reads + simulated writes work with `READONLY_MODE=true`. When ready for real
writes (still gated by `/ad-actions`):

```bash
# edit meta.env: READONLY_MODE=false, then:
docker rm -f meta-ads-mcp
docker run -d --name meta-ads-mcp --restart unless-stopped \
  --env-file meta.env -v meta_data:/data --network web meta-ads-mcp
```

Also set a **platform-level spend cap per ad account** (Ads Manager → Billing →
Payment settings → Account spending limit) as the hardware backstop, same as the
Google Ads runbook recommends.

## Updating later

```bash
cd Mad-Minds && git pull
cd meta-ads-mcp && docker build -t meta-ads-mcp .
docker rm -f meta-ads-mcp
docker run -d --name meta-ads-mcp --restart unless-stopped \
  --env-file meta.env -v meta_data:/data --network web meta-ads-mcp
```

The `meta_data` volume survives, so no one has to re-Connect.

## Vercel deployment (live — this is how it runs today)

`meta-ads-mcp/` is deployed to Vercel as **two serverless projects**, one per
Meta business area. Vercel gives stable `*.vercel.app` hostnames that Facebook
accepts, with zero server management. Token storage is Upstash Redis (HTTP-only
client, works inside Vercel's ephemeral containers).

**Live URLs:**
- onlineminds.io → `https://meta-ads-onlineminds.vercel.app/mcp`
- Rentumo ApS → `https://meta-ads-rentumo.vercel.app/mcp`

### 1. Create two Vercel projects

In [vercel.com/new](https://vercel.com/new), import `Nikolaj-Storm/Mad-Minds`
twice:
- `meta-ads-onlineminds` — for the onlineminds.io Facebook App
- `meta-ads-rentumo` — for the Rentumo ApS Facebook App

For **each** project:
- **Root Directory** → `meta-ads-mcp`
- Framework preset → **Other**

### 2. Attach Upstash Redis

In the Vercel dashboard: **Marketplace → Upstash → Redis** (not the deprecated
Vercel KV option). Create **one** Redis database and connect it to **both**
projects. The projects are isolated by the `REDIS_KEY_PREFIX` env var (Step 3),
so one database is enough — no key collisions.

Vercel auto-injects `KV_REST_API_URL` and `KV_REST_API_TOKEN` into both
projects.

### 3. Set environment variables

In each project: **Settings → Environment Variables**. Do **not** set
`CLIENT_STORAGE_DIR` (no volume needed on Vercel).

```ini
META_APP_ID=<Facebook App ID for this business area>
META_APP_SECRET=<Facebook App Secret>
META_OAUTH_BASE_URL=https://meta-ads-onlineminds.vercel.app
META_SCOPES=ads_read,ads_management
# REDIS_KEY_PREFIX isolates the two projects in the shared Redis database.
# Use a short unique label per project:
REDIS_KEY_PREFIX=onlineminds        # → rentumo on the other project
META_GRAPH_VERSION=v21.0
JWT_SIGNING_KEY=<openssl rand -hex 32>
READONLY_MODE=true
# KV_REST_API_URL and KV_REST_API_TOKEN — auto-injected by Upstash integration.
# META_CONFIG_ID — only needed if using Facebook Login for Business with a config.
```

`JWT_SIGNING_KEY` encrypts the Redis token store. Keep it stable across
redeployments or marketers have to re-Connect.

### 4. Deploy

Push to `main` — Vercel deploys automatically. Verify:

```bash
curl -s https://meta-ads-onlineminds.vercel.app/health
# → {"status":"healthy","service":"Meta Ads MCP"}
curl -s https://meta-ads-onlineminds.vercel.app/.well-known/oauth-authorization-server | python3 -m json.tool
# authorization_endpoint must show the vercel.app domain, not a placeholder.
```

### 5. Configure the Facebook App

For **each** business-area Facebook App at <https://developers.facebook.com/apps>:

1. **App Settings → Basic → App Domains:** add only the bare hostname, e.g.
   `meta-ads-onlineminds.vercel.app`. Do **not** add full URLs with `https://`
   or paths here — App Domains only accepts bare hostnames.

2. **App Settings → Advanced:** turn **"Native or desktop app?" OFF**. Having
   this toggle ON switches Facebook to a native-app OAuth flow that breaks the
   server-side redirect.

3. **Facebook Login for Business → Settings → Valid OAuth Redirect URIs:** add
   `https://meta-ads-onlineminds.vercel.app/auth/callback`. This is separate
   from App Domains and must be set explicitly.

4. If using Facebook Login for Business with a config: **Configurations** →
   create/update the config granting `ads_read + ads_management` → copy the
   config ID into `META_CONFIG_ID`.

### 6. Wire into Claude

Each marketer: **Customize → Connectors → Add custom connector** → paste URL →
leave Advanced settings empty (DCR, no Client ID/Secret) → **Add** → **Connect**
→ sign in with Facebook.

```
https://meta-ads-onlineminds.vercel.app/mcp   ← onlineminds.io
https://meta-ads-rentumo.vercel.app/mcp        ← Rentumo ApS
```

### Vercel cold-start note

~200–800 ms cold starts. Invisible in practice — Facebook's OAuth redirect
happens in a browser, not a tight loop.

### Known gotchas (all fixed in the codebase)

- **DCR `grant_types` mismatch:** FastMCP 2.12 requires both `authorization_code`
  AND `refresh_token` in `grant_types` at `/register`, but Claude's MCP client
  only sends `authorization_code`. Fixed by `_DCRGrantTypeFix` in `api/index.py`,
  which patches the request body before FastMCP sees it.

- **`RedisStore.put(collection=…)` crash:** FastMCP's OAuthProxy calls
  `put(..., collection=...)` for key namespacing. Fixed in `redis_store.py` —
  the `collection` (and optional `REDIS_KEY_PREFIX`) are prepended to the Redis
  key as `{prefix}:{collection}:{key}`.

- **`META_OAUTH_BASE_URL` placeholder:** Vercel's default env for new projects
  may still say `https://api.example.com`. Must be set to the actual production
  URL (`https://meta-ads-onlineminds.vercel.app`) or Facebook will receive an
  `api.example.com` redirect URI and reject it.

- **App Domains with full URLs:** Facebook's App Domains field only accepts bare
  hostnames. Entries like `https://meta-ads-onlineminds.vercel.app/auth/callback`
  in App Domains are silently ignored and do not substitute for the Valid OAuth
  Redirect URIs field.

---

## Notes / gotchas

- **Token lifetime ~60 days.** Facebook has no refresh token; the server upgrades
  each sign-in to a ~60-day long-lived token automatically, but after that a
  marketer re-Connects (one click). Expected, not a bug. An expired token shows
  up as a `190` error with a "re-connect" hint.
- **Graph version.** `META_GRAPH_VERSION` defaults to `v21.0`. Meta retires
  versions ~2 years out; bump it (and `docker build` is unaffected — it's just an
  env var) when Meta deprecates it. The `debug_token` call is version-agnostic.
- **Consent screen is disabled** (`require_authorization_consent=false`, matching
  the Google Ads MCP) for a one-click Connect. The upstream is each marketer's own
  Facebook and the client is Claude's hosted callback, so the confused-deputy risk
  the screen guards against is low — but if you want it, it's a one-line change in
  `server.py` (`require_authorization_consent=True`).
- **Zero-decimal currencies.** Budgets/spend are converted assuming 2 minor
  digits (DKK, EUR, USD, GBP — all fine). An account in JPY/HUF would mis-scale by
  100; none of the OnlineMinds brands use those today. Flagged in `client.py`.
```
