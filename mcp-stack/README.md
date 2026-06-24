# Mad Minds MCP stack

Runs the self-hosted MCP servers on our Hetzner box (`<maintainer>@<box-ip>`, hostname
`<box-hostname>` — a KVM VM with **rootless** Docker and **no sudo** for the `mcp` user).

OnlineMinds has **two Meta business areas**, each with its own Meta business +
Facebook app, so Meta runs as **two MCP instances** (each server is wired to one
App ID/Secret). Public HTTPS for each comes from a **Tailscale Funnel** (no domain,
no inbound ports, no root — free):

```
internet ─HTTPS─► Tailscale Funnel ─► meta-onlineminds.<tailnet>.ts.net ─► meta-ads-onlineminds:8000
                                  └─► meta-rentumo.<tailnet>.ts.net     ─► meta-ads-rentumo:8000
```

Marketers add the connector(s) for the area(s) they work in. This is the
**"containers inside the container"** setup: the `mcp@` VM hosts the Compose
stack; each MCP and each tunnel is its own container.

> Alternatives if your situation differs: `compose.cloudflare.yaml` (needs a
> domain on Cloudflare) and `compose.caddy.yaml` (own TLS on 80/443, needs root).

---

## Prerequisites

1. **Docker works as `mcp`** (it does on <box-hostname> — rootless, no sudo to build/run).
2. **A free Tailscale account** (just you — marketers never touch it).
3. **Two Facebook Apps** — one per business area — for the two `META_APP_ID` /
   `META_APP_SECRET` pairs. See `../META-SELF-HOST-RUNBOOK.md` Step 1 (incl. the
   app-Tester trick that skips App Review). Each app's redirect URI is its own
   instance's `https://<host>/auth/callback` (see below).

## 1. One-time Tailscale setup (admin console, ~3 min)

At <https://login.tailscale.com>:

1. **DNS** tab → note your **Tailnet name** (e.g. `tail9a8b7.ts.net`). Your two
   URLs will be `https://meta-onlineminds.<tailnet>` and `https://meta-rentumo.<tailnet>`.
2. **DNS** tab → **Enable HTTPS**.
3. **Access Controls** → add the Funnel node-attribute policy (covers both nodes):
   ```jsonc
   "nodeAttrs": [
     { "target": ["*"], "attr": ["funnel"] }
   ]
   ```
4. **Settings → Keys → Generate auth key** (tick **Reusable** — one key registers
   both nodes). Copy the `tskey-auth-…`.

## 2. Point each Facebook app's redirect URI at its instance

In each app at developers.facebook.com → **Facebook Login → Settings → Valid OAuth
Redirect URIs**:

| Facebook app | Redirect URI |
|---|---|
| Mad Minds MCP onlineminds.io | `https://meta-onlineminds.<tailnet>.ts.net/auth/callback` |
| Mad Minds MCP Rentumo aps | `https://meta-rentumo.<tailnet>.ts.net/auth/callback` |

## 3. Put the code + secrets on the box (as `mcp`)

```bash
git clone https://github.com/Nikolaj-Storm/Mad-Minds.git   # or: git pull
cd Mad-Minds/mcp-stack

cp tailscale.env.example tailscale.env
nano tailscale.env             # TS_AUTHKEY=tskey-auth-…  (the one reusable key)

cp meta.env.example meta-onlineminds.env
nano meta-onlineminds.env      # onlineminds.io app: META_APP_ID/SECRET,
#                                META_OAUTH_BASE_URL=https://meta-onlineminds.<tailnet>.ts.net,
#                                JWT_SIGNING_KEY (openssl rand -hex 32)

cp meta.env.example meta-rentumo.env
nano meta-rentumo.env          # Rentumo aps app: its META_APP_ID/SECRET,
#                                META_OAUTH_BASE_URL=https://meta-rentumo.<tailnet>.ts.net,
#                                a DIFFERENT JWT_SIGNING_KEY
```

Each instance's `META_OAUTH_BASE_URL` must equal its Funnel hostname AND its
Facebook app's redirect-URI host. Give the two a different `JWT_SIGNING_KEY`.

## 4. Launch

```bash
docker compose up -d --build
docker compose ps                 # 4 services Up: 2x meta-ads, 2x tailscale
```

`restart: unless-stopped` + lingering (already on, on <box-hostname>) brings it all
back on reboot.

## 5. Confirm both Funnels + verify

```bash
docker compose exec tailscale-onlineminds tailscale funnel status
docker compose exec tailscale-rentumo     tailscale funnel status
curl -s https://meta-onlineminds.<tailnet>.ts.net/health
curl -s https://meta-rentumo.<tailnet>.ts.net/health
```

Each `/health` → `{"status":"healthy","service":"Meta Ads MCP"}`.

## 6. Wire the connectors in Claude

Add each as a custom connector (Customize → Connectors → Add custom connector →
leave Advanced empty → Add → Connect → sign in with **Facebook**):

| Connector | URL |
|---|---|
| Meta Ads — onlineminds | `https://meta-onlineminds.<tailnet>.ts.net/mcp` |
| Meta Ads — Rentumo | `https://meta-rentumo.<tailnet>.ts.net/mcp` |

Then run `server_status` (expect `auth_configured: true`) and `list_ad_accounts`
on each. Marketers connect whichever business area(s) they work in.

---

## Adding another MCP later (e.g. a third area, or Google Ads)

Copy the meta-ads + tailscale pair: add the two services to `compose.yaml` (new
`*.env`, new `serve-*.json` pointing at the new service, new `TS_HOSTNAME`), add a
redirect URI / connector as needed, then `docker compose up -d --build`. The
shared `&meta-ads` / `&tailscale` anchors keep each addition to a few lines.

## Updating

```bash
cd Mad-Minds && git pull
cd mcp-stack && docker compose up -d --build
```

Named volumes survive (token stores + Tailscale identities), so no one re-Connects.

## Troubleshooting

- **`funnel status` says Funnel not available / HTTPS** → step 1.2 (Enable HTTPS)
  or 1.3 (the `funnel` nodeAttr) wasn't applied. Fix in the console, then
  `docker compose restart tailscale-onlineminds tailscale-rentumo`.
- **A node didn't authenticate** → bad/expired `TS_AUTHKEY`. Regenerate; `up -d`.
- **`/health` works locally but not over a Funnel URL** → that instance's
  `serve-*.json` `Proxy` must name its own MCP service (`meta-ads-onlineminds` /
  `meta-ads-rentumo`) on port 8000.
- **OAuth loops / wrong redirect** → that instance's `META_OAUTH_BASE_URL` and its
  Facebook app's redirect URI must both be its own `…ts.net` host + `/auth/callback`.
- **Meta `190`** → marketer's Facebook sign-in expired (~60d); re-Connect.
  `(#200)`/permission → not on that ad account / Business Manager.
- **Didn't survive reboot** (rootless) → `loginctl show-user mcp -p Linger` is `yes`
  on <box-hostname>; if ever not, root runs `loginctl enable-linger mcp`.

---

## Alternatives (single-instance examples)

- **`compose.cloudflare.yaml`** — Cloudflare Tunnel; cleaner branded URL, needs a
  domain on Cloudflare.
- **`compose.caddy.yaml`** — Caddy + Let's Encrypt on 80/443; needs a domain (A
  record) and control of ports 80/443 (rootful, or rootless after root sets
  `net.ipv4.ip_unprivileged_port_start=80`). Not usable on <box-hostname> as-is.
