# Machine Access — setup gameplan

Companion to `MACHINE-ACCESS-DESIGN.md`. This is the ordered, do-this-then-that plan for standing up
the read-only machine access point. (Ahrefs and AirOps were dropped from scope at your request and no
longer appear anywhere in this repo.)

---

## 0. Repository decision — **use a new private repo**

**Recommendation: a separate private GitHub repo, `mad-minds-machine`.** Do not put the machine stack
in the `Mad-Minds` marketplace repo.

Why separate wins:

1. **Distribution surface vs. secret surface.** `Mad-Minds` is the repo marketers paste into Claude
   desktop to install the plugin — it is meant to be handed around. The machine stack holds the most
   dangerous credentials in the org (non-expiring Meta system-user tokens, a Google service-account
   key, a Google Ads refresh token, a read-only DB role, the master machine bearer). A
   credential/distribution repo and a machine-secret repo should never be the same repo, even though
   `.env` is gitignored — you don't want the machine's compose files, internal hostnames, or ops
   docs travelling with the thing every marketer clones.
2. **Different audience & lifecycle.** Marketplace = a product shipped to humans (plugins, skills,
   onboarding). Machine repo = backend infra for an autonomous agent. Different reviewers, cadence,
   and threat model.
3. **Tighter access control.** A private repo can be locked to you/ops; the marketplace is
   deliberately broad.

The one real cost — the machine servers are partly **forks of the existing servers** (`gads-mcp`,
`meta-ads-mcp`, …). Handle it the simplest way: **copy the small modules you need into the new repo
and swap the credential layer.** They diverge anyway (service credential instead of per-user OAuth,
read tools only). If duplication ever bites, extract a shared pip package later — not now.

**What lives where afterward:**

| Repo | Holds |
|---|---|
| `Mad-Minds` (existing) | Marketer plugins, skills, onboarding, the per-user OAuth connectors, the `MACHINE-ACCESS-*.md` design docs (planning only — no secrets). Unchanged operationally. |
| `mad-minds-machine` (new, private) | The `madminds-machine` compose project, the read-only machine servers, the cron runner + templates, `machine.env` (gitignored), the provisioning checklist. |

---

## 1. Proposed structure of the new repo

```
mad-minds-machine/
  README.md                      # what this is, the two-worlds principle, safety model
  PROVISIONING-CHECKLIST.md      # every console step + where each secret goes
  compose.machine.yaml           # the madminds-machine project (internal Tailscale, one bearer)
  machine.env.example            # all machine secrets, documented; real machine.env gitignored
  .gitignore                     # *.env, service-account*.json, tokens/
  servers/
    meta-ads-ro/                 # fork: Meta reader, System User token, read tools only
    google-ro/                   # one server, Google service account -> Drive + GSC + GA4 readers
    gads-ro/                     # fork: Google Ads reader, refresh token, get_* tools only
    supabase-ro/                 # read-only Postgres role queries
    notion-ro/  slack-ro/        # optional
    _shared/                     # bearer auth middleware, logging, common helpers
  passthrough/
    thribee.md  rentumo.md       # already-bearer sources: reuse existing endpoints, no new server
  cron/
    runner/                      # the scheduled-job container (on the tailnet)
    jobs/                        # one script per scheduled pull (output-agnostic template)
  tailscale/                     # serve configs (internal, not Funnel) for each machine host
```

Every machine server shares one `_shared` bearer-auth middleware keyed on `MACHINE_BEARER_TOKEN`, and
registers **read tools only** (write tools are never imported), with `READONLY_MODE=true` as a third
backstop.

---

## 2. Phase-by-phase setup

Each phase lists **you** (console work only you can do) and **scaffold** (what I generate in the repo)
and **verify** (the check that proves it works). Ship phases independently — each is usable on its own.

### Phase 0 — Skeleton (no sources)
- **Scaffold:** create the repo tree, `compose.machine.yaml` (project `madminds-machine`, its own
  network), `_shared` bearer middleware, `machine.env.example`, Tailscale **internal** serve config,
  a `/health` server.
- **You:** create the private repo `mad-minds-machine`; generate `MACHINE_BEARER_TOKEN`
  (`openssl rand -hex 32`) into `machine.env`; deploy on the Hetzner box:
  `docker compose -f compose.machine.yaml up -d`.
- **Verify:** from a tailnet host, `curl -H "Authorization: Bearer $TOKEN" http://machine-health.<tailnet>/health` returns ok; without the token it 401s.

### Phase 1 — Thribee + Rentumo Trials (zero new credentials)
- **Scaffold:** `passthrough/` docs + (if you want one URL) thin read-only proxies; otherwise just
  point the agent/cron at the existing bearer endpoints.
- **You:** nothing — they're already read-only bearer servers.
- **Verify:** agent/cron pull `rentumo_get_all_trials` and `thribee_get_all_spend` with the machine
  bearer (or the existing one) and get data.

### Phase 2 — Meta ×2 (System User tokens — cleanest new credential)
- **You:** in each Meta Business (onlineminds.io, Rentumo ApS): Business Settings → Users →
  **System Users** → add a system user → **Generate token** scoped to **`ads_read` only**,
  no-expiry → assign the ad accounts you want readable. Paste both into `machine.env`.
- **Scaffold:** `servers/meta-ads-ro` — fork of `meta-ads-mcp` with the OAuth proxy removed; it calls
  Graph directly with the system-user token; only `get_*`/reporting tools registered.
- **Verify:** `get_performance` on a known account returns last-30-days spend for both businesses.

### Phase 3 — Google service account → Drive + GSC + GA4 (one credential, three sources)
- **You:** in Google Cloud, create a **service account** + JSON key; enable Drive API, Search Console
  API, Analytics Data API. Then **grant it read access**: share the Hub folder with the SA email
  (Viewer); add the SA as a user on each GSC property; add the SA as **Viewer** on the GA4 property.
  Drop the JSON key on the box (path in `machine.env`).
- **Scaffold:** `servers/google-ro` — one server exposing Drive (`drive.readonly`), GSC
  (`webmasters.readonly`), and GA4 (Analytics Data API) readers off the single SA.
- **Verify:** list Hub files; pull a GSC query report; pull a GA4 sessions report. **GA4 is net-new
  capability** — it isn't wired anywhere in the marketer stack today.

### Phase 4 — Google Ads (refresh token + existing dev token)
- **You:** generate an **OAuth refresh token** for a dedicated Google login that has read access to
  the Ads accounts (a service account needs domain-wide delegation — the refresh token is simpler).
  Reuse the org's existing **developer token**. Paste both into `machine.env`.
- **Scaffold:** `servers/gads-ro` — fork of `gads-mcp` building `GoogleAdsClient` from the refresh
  token instead of `get_access_token()`; only `get_*` reporting tools; `READONLY_MODE=true`.
- **Verify:** `get_performance` / `get_campaigns` on a client account returns metrics (MCC returns
  none — query a client account, per the server's own note).

### Phase 5 — Supabase + optional Notion / Slack
- **You:** create a **read-only Postgres role** (SELECT-only) in Supabase and a connection string for
  it (not `service_role`). Optionally: a Notion **internal integration token** (read) shared to the
  needed pages; a Slack **bot token** with read scopes.
- **Scaffold:** `servers/supabase-ro` (+ `notion-ro`, `slack-ro` if wanted).
- **Verify:** run a SELECT through the reader; confirm an INSERT is rejected by the role.

### Phase 6 — Cron + agent end-to-end
- **Scaffold:** `cron/runner` container on the tailnet + one example job (output-agnostic template).
- **You:** confirm where "OpenClaw" runs (on the box / on the tailnet / off-net). On-net → keep
  internal binding; off-net → flip that service to Tailscale **Funnel + bearer + IP allowlist**.
- **Verify:** the example cron job runs on schedule, calls a machine endpoint with the bearer, writes
  output; the agent connects to the machine endpoint(s) and reads from ≥2 sources.

---

## 3. Secrets & ops

- All machine secrets in **`machine.env`** (gitignored) + the Google SA **JSON key** on the box only.
  One **`MACHINE_BEARER_TOKEN`**, distinct from the marketer/Thribee/Rentumo bearers.
- **Rotation:** bearer + Meta system-user tokens + Google Ads refresh token on a schedule; Meta tokens
  are revocable per-system-user in Business Settings; SA keys rotate in Google Cloud.
- **Audit:** every machine call logs tool + timestamp + caller to a machine-side log.

## 4. Isolation guarantees (why the marketer setup is safe)

- New repo, new `machine.env`, new bearer, **new compose project** (`madminds-machine`) with its own
  network. The three existing projects (`madminds-mcp`, `madminds-google`, `madminds-rentumo`) are
  never edited or recreated.
- **No write tools exist** in the machine world → no spend-gate surface, nothing a prompt-injected
  agent can trigger. Read-only is enforced three ways: upstream scope/role, tools registered, and
  `READONLY_MODE`.
- Machine endpoints are **internal-only** by default; public exposure is an explicit, per-service flip.

## 5. What needs you before we can start building

1. Confirm: create the private repo `mad-minds-machine` (I'll scaffold into it / into a local copy here).
2. (Desktop, separate from the repo) remove the **Ahrefs** and **AirOps** connectors from Claude
   desktop → Customize → Connectors, since they're being dropped from scope.
3. Provisioning happens per phase (Meta system users, Google SA, Ads refresh token, Supabase role) —
   each phase is independent, so we can start with Phases 0–1 immediately while you line up credentials.
