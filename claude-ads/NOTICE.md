# Attribution — claude-ads

This directory is a **vendored copy** of the open-source plugin **claude-ads** by AgriciDaniel, distributed under the MIT license. It is included inside the Mad-Minds marketplace so OnlineMinds marketers get its capabilities by installing the single marketplace.

- **Upstream repo:** https://github.com/AgriciDaniel/claude-ads
- **Upstream commit vendored:** `283d9d4917cb7c4f2ce9181e125bb1970f74ab04` (2026-05-18)
- **Upstream version:** 1.7.0
- **License:** MIT — see `LICENSE` in this directory.

## What we vendored
- `.claude-plugin/plugin.json` — plugin manifest
- `ads/` — orchestrator skill + 25 reference files
- `agents/` — 10 audit + creative agents
- `skills/` — 22 sub-skills (ads-google, ads-meta, ads-amazon, etc.)
- `scripts/` — Python helpers (landing-page analysis, PDF report generation, image generation)
- `LICENSE`, `UPSTREAM-README.md`, `UPSTREAM-CLAUDE.md`

## What we omitted
- `evals/`, `tests/`, `research/`, `branding/`, `assets/` (dev artifacts and README images — not used at runtime)
- `install.sh`, `install.ps1`, `uninstall.*` (only needed for standalone install — Mad-Minds marketplace handles install)
- `requirements.txt`, `requirements-dev.txt` (Python deps — marketers don't run the installer)
- `CHANGELOG.md`, `CITATION.cff`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md` (project metadata)

## Updating
Run `scripts/sync-claude-ads.sh` from the Mad-Minds repo root to refresh this directory from upstream. Bump the marketplace + plugin versions afterward and commit.

## Boundary with onlineminds-marketing
This plugin is **analysis-only**. All write actions (pause campaigns, change budgets, edit GTM, etc.) go through the `/ad-actions` skill in the **onlineminds-marketing** plugin, which enforces the Tier 1 / Tier 2 spend-gate (verbatim typed accept-phrase for spend increases). Do not use claude-ads outputs to bypass that gate; surface findings, then apply through `/ad-actions`.
