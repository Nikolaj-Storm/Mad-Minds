# gsc-mcp — self-hosted Google Search Console connector

Maintainer infrastructure (not part of the distributed plugin). Deploy this once; OnlineMinds marketers then connect GSC by clicking **Connect → sign in with Google**, nothing to paste.

- **What it is:** a corrected, version-pinned copy of damupi/mcp-gsc-oauth (FastMCP Google OAuth-proxy). See `NOTICE.md` for the fixes and what was verified.
- **How to deploy:** follow [`../GSC-SELF-HOST-RUNBOOK.md`](../GSC-SELF-HOST-RUNBOOK.md).
- **Auth model:** the server holds the Google client secret (env file on the box) and brokers OAuth for every marketer. Each marketer signs in with their own Google account and only ever sees their own Search Console properties. Read-only (`webmasters.readonly`).
- **Deploy target (current):** the Hetzner box via Docker Compose `mcp-stack/compose.google.yaml` (project `madminds-google`) behind Tailscale Funnel — its own container, disk-backed token storage at `/data`. Live URL: `https://gsc.tail40453d.ts.net/mcp`. A `vercel.json` + `api/index.py` (Vercel serverless, Redis/KV storage) ships as an alternative.

## TL;DR deploy (on the box)
```bash
cd ~/Mad-Minds/mcp-stack
# gsc.env holds FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID/SECRET/SCOPES,
#   FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL=https://gsc.tail40453d.ts.net,
#   CLIENT_STORAGE_DIR=/data, JWT_SIGNING_KEY=$(openssl rand -hex 32)
docker compose -f compose.google.yaml up -d --build gsc-mcp tailscale-gsc
curl -s https://gsc.tail40453d.ts.net/health
```
Full steps (Google OAuth client + redirect URIs + the paired gads service): [`../GSC-SELF-HOST-RUNBOOK.md`](../GSC-SELF-HOST-RUNBOOK.md).
