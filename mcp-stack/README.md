# Mad Minds MCP stack

Runs the self-hosted MCP servers (starting with **Meta Ads**) as Docker
containers on our Hetzner box (`mcp@37.27.23.202`, hostname `Openclaw` — a KVM VM
with **rootless** Docker and **no sudo** for the `mcp` user).

Because the box is rootless + no-sudo, public HTTPS comes from a **Cloudflare
Tunnel**: a `cloudflared` container dials *out* to Cloudflare, which serves
HTTPS and forwards to each MCP over the internal network. No inbound ports, no
privileged-port problem, no root.

```
internet ──HTTPS──► Cloudflare edge ──tunnel──► cloudflared ──► meta-ads-mcp:8000
                                                          └────► next-mcp:8000  (later)
```

One tunnel serves every MCP. This is the **"containers inside the container"**
setup: the `mcp@` VM hosts the Compose stack, each MCP is its own container.

> **Have root on the host instead?** Skip Cloudflare and use `compose.caddy.yaml`
> (Caddy + Let's Encrypt on 80/443). See "Alternative: Caddy" at the bottom.

---

## Prerequisites

1. **Docker works as `mcp`** (it does on Openclaw — rootless, no sudo needed to
   build/run). Confirm: `docker version && docker compose version`.
2. **A domain on Cloudflare.** The tunnel creates its public hostname in a
   Cloudflare-managed zone, so the domain's nameservers must point at Cloudflare
   (free plan is fine). If you don't want to move `onlineminds.io`'s nameservers,
   use a separate small domain on Cloudflare just for the MCP endpoints.
3. **A Facebook App** for `META_APP_ID` / `META_APP_SECRET` — see
   `../META-SELF-HOST-RUNBOOK.md` Step 1 (incl. the app-Tester trick that skips
   App Review for the team). The app's redirect URI is `https://<host>/auth/callback`.

## 1. Create the Cloudflare Tunnel (dashboard, ~3 min)

In the **Cloudflare Zero Trust** dashboard (one.dash.cloudflare.com):

1. **Networks → Tunnels → Create a tunnel → Cloudflared.** Name it `madminds-mcp`.
2. Copy the **tunnel token** it shows (a long `eyJ…` string). That's all the
   server needs — this is a remotely-managed tunnel; routing is set here, not in
   a local file.
3. On the tunnel's **Public Hostname** tab, **Add a public hostname:**
   - Subdomain: `meta-mcp` · Domain: `<your-cloudflare-domain>`
   - Service: **`http://meta-ads-mcp:8000`** (HTTP — TLS terminates at Cloudflare;
     `meta-ads-mcp` is the Compose service name on the internal network)

Cloudflare auto-creates the DNS record for `meta-mcp.<domain>`. No A record to
add by hand.

## 2. Put the code + secrets on the box (as `mcp`)

```bash
git clone https://github.com/Nikolaj-Storm/Mad-Minds.git   # or: git pull
cd Mad-Minds/mcp-stack

cp cloudflared.env.example cloudflared.env
nano cloudflared.env        # paste TUNNEL_TOKEN=eyJ…

cp meta.env.example meta.env
nano meta.env               # META_APP_ID, META_APP_SECRET,
#                             META_OAUTH_BASE_URL=https://meta-mcp.<domain>,
#                             JWT_SIGNING_KEY (openssl rand -hex 32)
```

`META_OAUTH_BASE_URL` must equal the tunnel's public hostname AND the Facebook
app's redirect-URI host.

## 3. Launch

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f cloudflared     # should show 4 connections "registered"
```

`restart: unless-stopped` + the user's lingering (already enabled on Openclaw)
means the stack comes back on reboot.

## 4. Verify

```bash
curl -s https://meta-mcp.<domain>/health
curl -s https://meta-mcp.<domain>/.well-known/oauth-authorization-server | head -c 400
```

`/health` → `{"status":"healthy","service":"Meta Ads MCP"}`. Then add
`https://meta-mcp.<domain>/mcp` as a custom connector in Claude and run
`server_status` → `list_ad_accounts`. (Facebook-app setup, full verify, and the
connector wiring are in `../META-SELF-HOST-RUNBOOK.md` Steps 1, 7, 8.)

---

## Adding the next MCP later

1. **compose.yaml** — copy the commented `gads-mcp` block; point `build:` at the
   MCP's folder, give it its own `*_data` volume + `*.env` file.
2. **Cloudflare dashboard** — on the same tunnel, add another Public Hostname:
   `gads-mcp.<domain>` → `http://gads-mcp:8000`.
3. `docker compose up -d --build`.

Same tunnel, same token, no new DNS. That's the whole point of the shared stack.

## Updating

```bash
cd Mad-Minds && git pull
cd mcp-stack && docker compose up -d --build
```

Named volumes survive, so no one has to re-Connect.

## Troubleshooting

- **`cloudflared` logs errors / no connections** → bad or missing `TUNNEL_TOKEN`
  in `cloudflared.env`. Recopy it from the dashboard.
- **`502`/`error 1033` at the public URL** → the Public Hostname's Service must be
  `http://meta-ads-mcp:8000` exactly (the Compose service name), and `cloudflared`
  must be on `mcpnet` (it is, in this compose). `docker compose logs meta-ads-mcp`
  to confirm the MCP is up.
- **OAuth loops / wrong redirect** → `META_OAUTH_BASE_URL` must equal
  `https://meta-mcp.<domain>` and the Facebook app's redirect URI must be
  `https://meta-mcp.<domain>/auth/callback`.
- **Meta `190`** for a marketer → their Facebook sign-in expired (~60-day token);
  re-Connect. `(#200)`/permission → not on that ad account / Business Manager.
- **Stack didn't survive reboot** (rootless) → check `loginctl show-user mcp -p Linger`
  is `yes` (it is on Openclaw). If ever not, root runs `loginctl enable-linger mcp`.

---

## Alternative: Caddy (only where you control ports 80/443)

On a host with rootful Docker — or rootless after root sets
`net.ipv4.ip_unprivileged_port_start=80` — you can skip Cloudflare and let Caddy
get its own Let's Encrypt cert:

```bash
nano Caddyfile                                  # set meta-mcp.<domain>
# DNS: A record meta-mcp.<domain> -> the host's public IP
docker compose -f compose.caddy.yaml up -d --build
```

Not usable on Openclaw as-is (rootless + no sudo can't bind 80/443), which is why
the default is the Cloudflare Tunnel above.
