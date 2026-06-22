# Mad Minds MCP stack

Runs the self-hosted MCP servers (starting with **Meta Ads**) as Docker
containers behind **one Caddy reverse proxy** with automatic HTTPS, on our
Hetzner box (`mcp@37.27.23.202`). One stack, many MCPs: each MCP is a Compose
service on a shared `mcpnet` network and gets its own `*.mcp` subdomain.

This is the **"containers inside the container"** setup you asked for — the
`mcp@` environment your colleague made is the host for this Compose stack, and
each MCP runs as its own container within it.

```
internet ──► Caddy (:80/:443, auto-TLS) ──► meta-ads-mcp:8000
                                       └──► (next MCP):8000  (later)
```

---

## 0. First, confirm the environment (run on the server)

`docker` must be usable **inside** the `mcp@` container, and ports **80/443**
must reach it from the internet. SSH in and run:

```bash
# A) Is Docker usable as this user?
docker version && docker compose version

# B) What am I running inside?
systemd-detect-virt 2>/dev/null; cat /run/systemd/container 2>/dev/null
ls /.dockerenv >/dev/null 2>&1 && echo "-> inside a Docker container (nested)"

# C) Are 80/443 free here?
ss -tlnp 2>/dev/null | grep -E ':80 |:443 ' || echo "80/443 look free"
```

Interpreting it:

- **`docker version` works** and B shows a VM / LXC (or nothing) → you're on the
  normal path. Use **Mode A** below.
- **Rootless Docker** (the daemon runs as your user — `docker version` shows a
  `rootlesskit` section, StateDir `/run/user/<uid>/dockerd-rootless`) → you can
  build and run with **no sudo**, but rootless can't publish ports < 1024 until
  root sets one sysctl. Do step **1b** before Mode A. *(This is our Hetzner
  `Openclaw` box's setup — KVM VM, rootless Docker as the `mcp` user.)*
- **`docker version` says permission denied** (rootful Docker) → the `mcp` user
  isn't in the `docker` group. Have your colleague run `usermod -aG docker mcp`
  (then re-login), or run the stack with `sudo`.
- **B says "inside a Docker container (nested)"** and `docker` is missing → this
  is Docker-in-Docker. Your colleague needs to either mount the host's Docker
  socket into this container (`-v /var/run/docker.sock:/var/run/docker.sock`)
  or run it `--privileged` with dind. Easiest: ask them to make `docker` work
  inside, then the steps below are unchanged.
- **C shows 80/443 already taken** (e.g. the host already runs a proxy) → use
  **Mode B** below (don't run our Caddy; hang the MCP off the existing proxy).

Also make sure DNS for your MCP hostname points at the box:
`dig +short meta-mcp.<your-domain>` → `37.27.23.202` (see
`../META-SELF-HOST-RUNBOOK.md` Step 2).

---

## 1. Get the code + secrets in place

```bash
git clone https://github.com/Nikolaj-Storm/Mad-Minds.git   # or: git pull
cd Mad-Minds/mcp-stack

cp meta.env.example meta.env
nano meta.env            # fill in META_APP_ID / META_APP_SECRET / domain / JWT key
#                          JWT key: openssl rand -hex 32
nano Caddyfile           # replace meta-mcp.example.com with your real hostname
```

The hostname must be identical in three places: `Caddyfile`,
`META_OAUTH_BASE_URL` in `meta.env`, and the Facebook app's redirect URI
(`https://<host>/auth/callback`).

## 1b. Rootless Docker — allow ports 80/443 (one-time, needs root)

Skip this on rootful Docker, or if you're using Mode B. On **rootless** Docker
(our Hetzner box) the daemon can't publish privileged ports until the host's
unprivileged-port floor is lowered. Whoever has root — the colleague who set up
the box, or you via `sudo` — runs this **once**:

```bash
echo 'net.ipv4.ip_unprivileged_port_start=80' | sudo tee /etc/sysctl.d/99-rootless-ports.conf
sudo sysctl --system
```

This is the *only* command that needs root; everything else runs as `mcp`. If a
later `docker compose up` errors with "cannot expose privileged port", this
wasn't applied — set it, then `systemctl --user restart docker` (runs as `mcp`,
no sudo) and retry.

## 2a. Mode A — self-contained (our Caddy does HTTPS)  ← default

Use this when 80/443 reach the container (and, on rootless, after step 1b).

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f caddy        # watch it obtain the TLS cert (ctrl-C to stop)
```

## 2b. Mode B — behind an existing host reverse proxy

Use this when the host already terminates TLS on 80/443. Don't start our Caddy;
publish just the MCP on a loopback port and point the host proxy at it.

```bash
# bring up only the MCP, mapped to localhost:8000
docker compose up -d --build meta-ads-mcp
docker compose exec -T meta-ads-mcp true   # sanity check it's up
```

Then add a port mapping by creating `compose.override.yaml`:

```yaml
services:
  meta-ads-mcp:
    ports:
      - "127.0.0.1:8000:8000"
```

…and configure the host proxy: `meta-mcp.<domain>` → `127.0.0.1:8000`,
terminating TLS. (Caddy/nginx/Traefik — whatever already runs there.)

## 3. Verify

```bash
curl -s https://meta-mcp.<your-domain>/health
curl -s https://meta-mcp.<your-domain>/.well-known/oauth-authorization-server | head -c 400
```

`/health` → `{"status":"healthy","service":"Meta Ads MCP"}`. Then add it as a
custom connector in Claude (`https://meta-mcp.<your-domain>/mcp`) and run
`server_status` → `list_ad_accounts`. See `../META-SELF-HOST-RUNBOOK.md` Steps
1, 7, 8 for the Facebook-app setup, full verify, and the connector wiring.

---

## Adding the next MCP later

Three edits, no architecture change:

1. **compose.yaml** — copy the commented `gads-mcp` block, point `build:` at the
   MCP's folder, give it its own `*_data` volume and `*.env` file.
2. **Caddyfile** — add a block: `gads-mcp.<domain> { reverse_proxy gads-mcp:8000 }`.
3. Create its env file (`cp …`), then `docker compose up -d --build`.

A wildcard DNS record (`*.mcp.<domain> A 37.27.23.202`) means new MCPs need
**zero** DNS changes — Caddy still issues a per-hostname cert over HTTP-01.

## Updating

```bash
cd Mad-Minds && git pull
cd mcp-stack && docker compose up -d --build
```

Named volumes survive, so no one has to re-Connect.

## Troubleshooting

- **Caddy can't get a cert** → 80/443 aren't reaching the container from the
  internet, or DNS isn't pointing at `37.27.23.202` yet. Fix the port forward /
  DNS, then `docker compose restart caddy`. (Cloudflare users: set the record to
  DNS-only / grey-cloud for issuance.)
- **`permission denied` on the Docker socket** (rootful only) → add `mcp` to the
  `docker` group (`usermod -aG docker mcp`, re-login) or use `sudo docker compose …`.
- **Stack doesn't come back after logout/reboot** (rootless) → the user's Docker
  daemon needs *lingering*. Check `loginctl show-user mcp -p Linger` (want
  `Linger=yes`); if not, `sudo loginctl enable-linger mcp`. With that + the
  services' `restart: unless-stopped`, the stack auto-starts on boot.
- **Meta returns `190`** for a marketer → their Facebook sign-in expired (~60-day
  token); they just re-Connect. A `(#200)`/permission error means their Facebook
  isn't on that ad account / Business Manager.
- **Logs:** `docker compose logs -f meta-ads-mcp` and `… logs -f caddy`.
