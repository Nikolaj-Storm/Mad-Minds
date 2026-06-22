# Mad Minds MCP stack

Runs the self-hosted MCP servers (starting with **Meta Ads**) as Docker
containers on our Hetzner box (`mcp@37.27.23.202`, hostname `Openclaw` — a KVM VM
with **rootless** Docker and **no sudo** for the `mcp` user).

Because the box is rootless + no-sudo **and** we don't want to tie up a domain,
public HTTPS comes from a **Tailscale Funnel**: a `tailscale` container joins the
tailnet in userspace mode and exposes a stable public URL like
`https://meta-mcp.<your-tailnet>.ts.net`, forwarding to the MCP over the internal
network. No domain, no inbound ports, no root — free.

```
internet ──HTTPS──► Tailscale Funnel ──► tailscale (userspace) ──► meta-ads-mcp:8000
```

This is the **"containers inside the container"** setup: the `mcp@` VM hosts the
Compose stack; each MCP (and the tunnel) is its own container.

> Alternatives if your situation differs: `compose.cloudflare.yaml` (Cloudflare
> Tunnel, needs a domain on Cloudflare) and `compose.caddy.yaml` (own TLS on
> 80/443, needs root). See the bottom of this file.

---

## Prerequisites

1. **Docker works as `mcp`** (it does on Openclaw — rootless, no sudo to build/run).
   Confirm: `docker version && docker compose version`.
2. **A free Tailscale account** (just you — marketers never touch it).
3. **A Facebook App** for `META_APP_ID` / `META_APP_SECRET` — `../META-SELF-HOST-RUNBOOK.md`
   Step 1 (incl. the app-Tester trick that skips App Review). Its redirect URI is
   `https://<host>/auth/callback`.

## 1. One-time Tailscale setup (admin console, ~3 min)

At <https://login.tailscale.com> after signing up:

1. **DNS** tab → note your **Tailnet name** (e.g. `tail9a8b7.ts.net`, or rename it
   to something nicer). Your MCP URL will be `https://meta-mcp.<tailnet-name>`.
2. **DNS** tab → **Enable HTTPS** (provisions the certs Funnel needs).
3. **Access Controls** tab → add a Funnel node-attribute policy to the JSON, then
   Save:
   ```jsonc
   "nodeAttrs": [
     { "target": ["*"], "attr": ["funnel"] }
   ]
   ```
4. **Settings → Keys → Generate auth key** (tick **Reusable**). Copy the
   `tskey-auth-…` value.

## 2. Put the code + secrets on the box (as `mcp`)

```bash
git clone https://github.com/Nikolaj-Storm/Mad-Minds.git   # or: git pull
cd Mad-Minds/mcp-stack

cp tailscale.env.example tailscale.env
nano tailscale.env          # paste TS_AUTHKEY=tskey-auth-…

cp meta.env.example meta.env
nano meta.env               # META_APP_ID, META_APP_SECRET,
#                             META_OAUTH_BASE_URL=https://meta-mcp.<tailnet-name>,
#                             JWT_SIGNING_KEY (openssl rand -hex 32)
```

`META_OAUTH_BASE_URL` = `https://meta-mcp.<tailnet-name>` (from step 1) — it must
match the Funnel hostname AND the Facebook app's redirect-URI host.

## 3. Launch

```bash
docker compose up -d --build
docker compose logs -f tailscale     # should show it logging in + Funnel started
```

`restart: unless-stopped` + the user's lingering (already on, on Openclaw) brings
the stack back on reboot.

## 4. Confirm the Funnel + URL

```bash
docker compose exec tailscale tailscale funnel status
docker compose exec tailscale tailscale status     # shows the node's full name
```

Funnel status should list `https://meta-mcp.<tailnet>.ts.net` → `http://meta-ads-mcp:8000`.

## 5. Verify + wire the connector

```bash
curl -s https://meta-mcp.<tailnet>.ts.net/health
```

→ `{"status":"healthy","service":"Meta Ads MCP"}`. Set the Facebook app's redirect
URI to `https://meta-mcp.<tailnet>.ts.net/auth/callback`, then add
`https://meta-mcp.<tailnet>.ts.net/mcp` as a custom connector in Claude and run
`server_status` → `list_ad_accounts`. (Facebook-app + full verify + wiring:
`../META-SELF-HOST-RUNBOOK.md` Steps 1, 7, 8.)

---

## Adding the next MCP later

1. **compose.yaml** — add the new MCP service (copy `meta-ads-mcp`'s block; point
   `build:` at its folder, give it its own `*_data` volume + `*.env`).
2. Expose it via Tailscale. Two options:
   - **Same node, by path** — add a handler to `tailscale/serve.json`
     (`"/gads/": {"Proxy": "http://gads-mcp:8000"}`), URL becomes
     `…ts.net/gads/mcp`. Simplest.
   - **Its own subdomain** — add a second `tailscale` service with
     `TS_HOSTNAME: gads-mcp` and its own serve.json → `https://gads-mcp.<tailnet>.ts.net`.
     Cleaner per-MCP URLs.
3. `docker compose up -d --build`.

## Updating

```bash
cd Mad-Minds && git pull
cd mcp-stack && docker compose up -d --build
```

Named volumes survive (token store + Tailscale identity), so no one re-Connects.

## Troubleshooting

- **`funnel status` says Funnel not available / HTTPS** → step 1.2 (Enable HTTPS)
  or 1.3 (the `funnel` nodeAttr) wasn't applied. Fix in the admin console, then
  `docker compose restart tailscale`.
- **Node didn't authenticate** → bad/expired `TS_AUTHKEY` in `tailscale.env`.
  Regenerate it; `docker compose up -d` re-reads it.
- **`/health` works locally but not over the Funnel URL** → the serve.json `Proxy`
  must be `http://meta-ads-mcp:8000` (the Compose service name) and tailscale must
  be on `mcpnet` (it is here).
- **OAuth loops / wrong redirect** → `META_OAUTH_BASE_URL` must equal
  `https://meta-mcp.<tailnet>.ts.net` and the Facebook redirect URI must be that +
  `/auth/callback`.
- **Meta `190`** for a marketer → their Facebook sign-in expired (~60-day token);
  re-Connect. `(#200)`/permission → not on that ad account / Business Manager.
- **Didn't survive reboot** (rootless) → `loginctl show-user mcp -p Linger` should
  be `yes` (it is on Openclaw); if not, root runs `loginctl enable-linger mcp`.

---

## Alternatives

- **`compose.cloudflare.yaml`** — Cloudflare Tunnel. Cleaner branded URL, but needs
  a domain on Cloudflare. `docker compose -f compose.cloudflare.yaml up -d --build`
  (fill `cloudflared.env` + add a Public Hostname → `http://meta-ads-mcp:8000`).
- **`compose.caddy.yaml`** — Caddy + Let's Encrypt on 80/443. Needs a domain (A
  record) AND control of ports 80/443 (rootful Docker, or rootless after root sets
  `net.ipv4.ip_unprivileged_port_start=80`). Not usable on Openclaw as-is.
