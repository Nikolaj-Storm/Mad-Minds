# gsc-mcp — self-hosted Google Search Console connector

Maintainer infrastructure (not part of the distributed plugin). Deploy this once; OnlineMinds marketers then connect GSC by clicking **Connect → sign in with Google**, nothing to paste.

- **What it is:** a corrected, version-pinned copy of damupi/mcp-gsc-oauth (FastMCP Google OAuth-proxy). See `NOTICE.md` for the fixes and what was verified.
- **How to deploy:** follow [`../GSC-SELF-HOST-RUNBOOK.md`](../GSC-SELF-HOST-RUNBOOK.md).
- **Auth model:** the server holds the Google client secret (Fly secrets) and brokers OAuth for every marketer. Each marketer signs in with their own Google account and only ever sees their own Search Console properties. Read-only (`webmasters.readonly`).

## TL;DR deploy
```bash
cd gsc-mcp
fly launch --no-deploy --name onlineminds-gsc-mcp
fly secrets set \
  FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.google.GoogleProvider \
  FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID="…apps.googleusercontent.com" \
  FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET="GOCSPX-…" \
  FASTMCP_SERVER_AUTH_GOOGLE_REQUIRED_SCOPES="openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/webmasters.readonly" \
  FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL="https://onlineminds-gsc-mcp.fly.dev"
fly deploy --remote-only
```
Then add `https://onlineminds-gsc-mcp.fly.dev/mcp` to `onlineminds-marketing/.mcp.json`.
