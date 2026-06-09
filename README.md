# Mad Minds — OnlineMinds Marketing Marketplace

A Claude plugin marketplace for the OnlineMinds marketing department. Paste this repo URL once into Claude desktop, get two plugins:

| Plugin | What it does |
|---|---|
| **`onlineminds-marketing`** | In-house skills for the OnlineMinds brands (Rentumo, Adsumo, Printumo, Bidumo, Monetumo, Photumo, Jacob Lund Art). Reads/writes the Mad Minds Google Drive Hub. Includes `/ad-actions` — the **only** skill that touches live ad accounts, behind a non-overridable Tier 1 / Tier 2 typed-phrase spend-gate. |
| **`claude-ads`** | Vendored copy of [AgriciDaniel/claude-ads](https://github.com/AgriciDaniel/claude-ads) (MIT). 250+ paid-advertising audit checks across Google, Meta, YouTube, LinkedIn, TikTok, Microsoft, Apple, Amazon. Health Score 0-100. Industry templates. PDF reports. **Analysis-only.** |

## Install (for marketers)

In Claude desktop → Customize → Plugins → **+ Add marketplace** → **From repository** → paste:

```
https://github.com/Nikolaj-Storm/Mad-Minds
```

Install **both** plugins when prompted. Then open Cowork and type `/setup-marketing`.

See [`EMPLOYEE-ONBOARDING.md`](./EMPLOYEE-ONBOARDING.md) for the full walkthrough.

## Repo layout

```
.claude-plugin/marketplace.json   ← lists both plugins
onlineminds-marketing/            ← in-house plugin
  .claude-plugin/plugin.json
  .mcp.json                       ← vendor-native MCPs (SimilarWeb, etc.)
  skills/                         ← 9 skills incl. /ad-actions, /setup-marketing
claude-ads/                       ← vendored upstream plugin (MIT)
  .claude-plugin/plugin.json
  ads/, agents/, skills/, scripts/
  LICENSE, NOTICE.md, UPSTREAM-CLAUDE.md, UPSTREAM-README.md
scripts/sync-claude-ads.sh        ← refresh vendored copy from upstream
SETUP.md, EMPLOYEE-ONBOARDING.md, COWORK-SETUP-RUNBOOK.md, BUILD-HUB-RUNBOOK.md
```

## Boundary between the two plugins

`claude-ads` is **analysis-only**. To act on its findings, use `/ad-actions` in `onlineminds-marketing` — the spend-gate enforces safety. The natural pattern:

1. `/ads audit` — get the 250-check audit with Health Score
2. `/ad-actions <brand> <change>` — apply the fixes, with the typed-phrase confirmation for anything that spends money

## Updating

- **In-house edits** to `onlineminds-marketing/`: edit, bump that plugin's `version` in `.claude-plugin/marketplace.json` and `onlineminds-marketing/.claude-plugin/plugin.json`, commit + push.
- **Sync `claude-ads/` from upstream**: `bash scripts/sync-claude-ads.sh`, review diff, bump that plugin's `version` in `.claude-plugin/marketplace.json` to the new upstream version, commit + push.

## License

The `onlineminds-marketing/` plugin is proprietary to OnlineMinds ApS. The `claude-ads/` plugin is MIT-licensed by AgriciDaniel — see `claude-ads/LICENSE` and `claude-ads/NOTICE.md`.
