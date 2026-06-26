# Machine Access (read-only) — design & build plan

**Goal:** a non-human access point that gives a self-built AI agent ("OpenClaw") and scheduled cron
jobs **read-only** access to every OnlineMinds data source, **independent of any employee's Claude or
personal OAuth login**. The existing marketer setup (per-user OAuth connectors, the spend-gate,
`/ad-actions` writes) must stay **exactly as it is** — this adds a second, parallel access point and
changes nothing about the human one.

Status: design. No credentials are provisioned yet (that needs console access in your own accounts —
see "What needs you" at the end). Everything else can be scaffolded from this repo.

---

## 1. The core idea: two separate worlds

| | Human world (unchanged) | Machine world (new) |
|---|---|---|
| Who acts | The signed-in marketer | A service identity (no person) |
| Auth | Per-user OAuth (Google/Facebook sign-in) | **System/service credentials held server-side**, gated by **one shared bearer token** |
| Transport in | Claude desktop Connect button / custom connectors | Agent + cron present the machine bearer |
| Writes | Allowed, via `/ad-actions` + spend-gate | **None — read-only by construction** |
| Infra | `madminds-mcp`, `madminds-google`, `madminds-rentumo` compose projects | **`madminds-machine`** — a brand-new, separate compose project |

The two worlds never touch. We do **not** edit `compose.yaml`, `compose.google.yaml`, or
`compose.rentumo.yaml`, and we do not add write tools or service credentials to the marketer servers.

### Why a parallel stack instead of reusing the marketer servers
The existing Google Ads / GSC / Meta servers build their upstream client from
`get_access_token()` — the OAuth token of *the marketer making the request* (confirmed in
`gads-mcp/src/gads_mcp/client.py::get_client`). A cron job has no signed-in user, so it has no token.
A machine needs **its own credential**. Bolting a static service credential onto the marketer servers
would entangle it with the per-user model and the spend-gate. Cleaner and safer: a new stack whose
servers authenticate with a service identity and expose only read tools.

### You already have the pattern
**Thribee** and **Rentumo Trials** are already exactly this model: read-only, one shared server-side
bearer, no per-user OAuth (`rentumo.env` → `RENTUMO_BEARER_TOKEN` is the only secret). The machine
world is just "do Thribee/Rentumo for every source."

---

## 2. Per-source machine-credential plan

Each source needs a credential a machine can hold (no human sign-in) and that is read-only.

| Source | Machine credential | Read-only how | Effort | Notes |
|---|---|---|---|---|
| **Thribee** | Existing shared bearer | Already read-only | **None** | Reuse as-is — instant win. |
| **Rentumo Trials** | Existing shared bearer | Already read-only | **None** | Reuse as-is — instant win. |
| **Meta Ads ×2** (onlineminds.io, Rentumo ApS) | **System User token** per Business (Business Settings → Users → System Users → generate, scope `ads_read` only, non-expiring) | `ads_read` scope only; no write tools registered | **Low** | The clean machine path. *Simpler* than the marketer server — no OAuth proxy, just the token. One token per business. |
| **Google Analytics (GA4)** | **Service account** added to the GA4 property as Viewer | Analytics Data API is read; Viewer role | **Low–Med** | Not wired in the human stack yet — GA4's natural auth *is* a service account, so it can ship first here. |
| **Google Search Console** | Same **service account**, added to each property (Restricted/Full user) | `webmasters.readonly` scope | **Low–Med** | Read-only scope is the guardrail. |
| **Google Drive (Hub)** | Same **service account**; share the Hub folder with its email as Viewer | `drive.readonly` scope + Viewer share | **Low** | One Google service account covers Drive + GSC + GA4. |
| **Google Ads** | Dedicated read-access Google login's **OAuth refresh token** + existing org developer token | Register only `get_*` reporting tools; `READONLY_MODE=true` backstop | **Med** | Service accounts on Google Ads need awkward domain-wide delegation; a refresh token from a dedicated viewer login is the simplest reliable path. Build the client from the refresh token instead of `get_access_token()`. |
| **Supabase** | Dedicated **read-only Postgres role** (SELECT-only) — *not* `service_role` | Role has no write grants | **Low** | Connect via a read-only connection string / PostgREST with that role. |
| **Notion** | **Internal integration token**, read capability only; share the needed pages/DBs with it | Integration capability set to read | **Low** | Optional. |
| **Slack** | **Bot token** with read scopes (`channels:history`, …) | Read scopes only | **Low** | Optional. |

Defense in depth everywhere: **read-only upstream scope/role** + **only read tools registered** +
`READONLY_MODE=true` as a backstop. Three independent reasons a write can't happen.

---

## 3. Exposure model (internal-first, since "where it runs" is undecided)

- **Default — internal only.** Bind the machine endpoints to the **tailnet** (no Tailscale Funnel /
  no public URL). The agent and cron either run **on the Hetzner box** or **join the tailnet**, and
  reach the servers privately. The machine bearer is a second layer on top of network isolation.
- **External later.** If the agent must run off-net, switch that one service to **Tailscale Funnel +
  require the bearer + IP allowlist**. Documented as a flip, not enabled by default.

This is strictly more locked-down than the marketer connectors (which are public Funnel for the
Connect flow). A machine secret should not sit on a public URL unless it has to.

---

## 4. Interface — simplest that fits what you already run

Keep the **bearer-gated MCP** shape you already use for Thribee/Rentumo. Both an MCP-speaking agent
and a cron script can call it.

- **One small machine MCP per source**, mirroring the existing repo layout (max code reuse), all
  sharing **one `MACHINE_BEARER_TOKEN`**. The agent adds the endpoints it needs; cron scripts call the
  same endpoints with the bearer.
- If the agent later prefers a single URL, front the per-source servers with one **aggregating gateway**
  — but don't build that on day one.
- Cron jobs that hate MCP can hit a couple of plain `GET` endpoints on the same servers (optional add).

---

## 5. Cron jobs

A small **cron host/container on the tailnet** runs scheduled scripts that call the machine endpoints
with the bearer and write output wherever that job needs it (Drive Hub / Supabase / flat files —
**output-agnostic**, decided per job since destination "isn't important" yet). Ship one documented
template script; clone it per pull.

---

## 6. Build phases

| Phase | What | Depends on you for |
|---|---|---|
| **0** | New `madminds-machine` compose project skeleton + `MACHINE_BEARER_TOKEN` + Tailscale internal binding. No sources yet. | Nothing — I can scaffold. |
| **1** | Wire **Thribee + Rentumo Trials** into the machine access point. | Nothing — they're already bearer/read-only. |
| **2** | **Meta ×2** via System User tokens. | Generate 2 system-user tokens (`ads_read`). |
| **3** | **Google service account** → Drive + GSC + **GA4** (one SA, three read APIs). GA4 is net-new capability. | Create SA, share Hub folder + GSC properties + GA4 property with it. |
| **4** | **Google Ads** (refresh token + existing dev token). | Generate a refresh token for a dedicated viewer Google login. |
| **5** | **Supabase** read-only role, **Notion**, **Slack**. | Create the role / tokens. |
| **6** | First end-to-end **cron job** + **agent** connection test. | Confirm where the agent runs. |

Order is by credential difficulty: zero-credential wins first, cleanest new credential (Meta system
user) next, the one shared Google SA covering three sources, then Google Ads, then the long tail.

---

## 7. Security properties

- **No write path exists in the machine world** — no write tools are registered, so there is no
  spend-gate surface to weaken and nothing for a prompt-injected agent to trigger.
- **Separate secrets** (`machine.env`, gitignored) and a **separate bearer** from the marketer servers.
- **Read-only upstream scopes/roles** (`ads_read`, `webmasters.readonly`, `drive.readonly`, GA4
  Viewer, SELECT-only Postgres role) — the credential itself can't write even if the code were wrong.
- **Internal-only by default**; bearer + IP allowlist if ever exposed.
- **Rotation:** bearer + Meta system-user tokens + the Google refresh token rotate on a schedule; Meta
  tokens are individually revocable in Business Settings.
- **Audit:** log every machine call (who/when/what tool) to a machine-side log, mirroring the
  marketer-side logging discipline.

---

## 8. What needs you (can't be done from this repo)

Provisioning happens in your own consoles:
- 2× Meta **System User** tokens (`ads_read`).
- 1× Google **service account** + share the Hub folder, GSC properties, and GA4 property with it.
- 1× Google Ads **refresh token** for a dedicated read-access login.
- Supabase **read-only role**, Notion **read integration token**, optional Slack **bot token**.
- Decide where the agent + cron run (drives internal vs. Funnel exposure).

Everything else — the `madminds-machine` compose project, the read-only machine servers (largely
forks of the existing ones with the credential source swapped and write tools removed), the bearer
wiring, the cron template, and a per-source provisioning checklist — I can scaffold in this repo
without touching the marketer stack.
