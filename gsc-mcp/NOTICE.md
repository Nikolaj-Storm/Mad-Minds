# NOTICE — vendored & corrected GSC MCP

This `gsc-mcp/` server is a **vendored, corrected** copy of
[damupi/mcp-gsc-oauth](https://github.com/damupi/mcp-gsc-oauth) (MIT License — see `UPSTREAM-LICENSE`).

We vendored it because the upstream repo **does not run as published**. Three defects were found and fixed during testing (sandbox boot + OAuth/DCR verification):

1. **Token bug (broke every GSC call).** Tools did `access_token = str(token)`, which serialises the whole `AccessToken` object (`"token='ya29…' client_id=… scopes=[…]"`) instead of the raw token, so every Google Search Console API call returned 401. Fixed to `access_token = token.token` (15 occurrences in `tools.py` + `resources.py`).
2. **Won't boot on FastMCP 3.x.** `FastMCP(name=…, description=…)` — the `description` kwarg was removed in FastMCP 3.x. Removed it; pinned `fastmcp<3` in `requirements.txt`.
3. **Won't boot — tool metadata.** `@mcp.tool(… metadata={…})` is rejected by current FastMCP. Removed the `metadata=` kwargs from the tool decorators in `server.py`.

## What was verified (in a sandbox, with dummy Google credentials)
- Server boots cleanly on `fastmcp 2.14.7`, `/health` → 200.
- `/.well-known/oauth-authorization-server` advertises `/authorize`, `/token`, **`/register`** (Dynamic Client Registration) and **PKCE `S256`** — the exact discovery Claude's Connect button needs.
- `POST /register` → **201** with a `client_id` (DCR works → marketers can Connect with nothing to paste).
- `POST /mcp` with no token → **401** `WWW-Authenticate: Bearer` (proper auth challenge).
- `GoogleProvider` wires the upstream Google authorize/token endpoints and a `GoogleTokenVerifier` that validates via Google's `tokeninfo` — so the token reaching the tools is the **caller's own Google token** (per-user; each marketer sees only their properties).

## What was NOT verified here (needs a real deploy)
- The end-to-end Google sign-in → live GSC data round-trip (requires a real OAuth client + a browser). The token plumbing is now correct, so this is low-risk — confirm it once with MCP Inspector per the runbook.
- `/.well-known/oauth-protected-resource` returned 404 in the sandbox. DCR + authorization-server metadata are sufficient for the Connect flow, but if a future Claude build requires RFC 9728 resource metadata, that's the one thing to add. Watch for it in the Inspector test.

See `../GSC-SELF-HOST-RUNBOOK.md` for deployment.
