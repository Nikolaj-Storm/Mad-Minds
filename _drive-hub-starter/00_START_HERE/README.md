# OnlineMinds Marketing Hub

This Drive folder is the shared workspace for the marketing department. Each person runs their own Claude Cowork session against it via the `onlineminds-marketing` plugin. Sessions are private; the files here are shared.

## How it works
- **Skills read from and write to this Hub.** Inputs come from `03_Data/`; finished work lands in `04_Reports/` or `05_Plans_and_Strategy/`.
- **Naming:** `YYYY-MM-DD_<brand>_<type>[_<detail>].<ext>` — date-prefixed, brand-tagged, lowercase.
- **Brands:** rentumo, adsumo, printumo, bidumo, monetumo, photumo, jla (Jacob Lund Art). Use `portfolio` for cross-brand work.
- **Don't** leave finished deliverables only inside a private Cowork session, and **never** put API keys or secrets in any file here.

## Folders
- `01_Knowledge_Base/` — brand voice, playbooks, personas, glossary, past campaigns
- `02_Brand_Assets/` — logos, fonts, imagery, templates
- `03_Data/` — raw_exports/YYYY-MM, cleaned/, connectors-cache/
- `04_Reports/` — _templates/, weekly/ monthly/ quarterly/, ad-hoc/
- `05_Plans_and_Strategy/` — campaign-briefs/, content-calendars/, growth-experiments/
- `06_Automation_Outputs/` — logs/, scheduled/

## First-time setup for a new marketer
1. Install the `onlineminds-marketing` plugin (Cowork → Customize → Plugins).
2. Connect this Hub folder in Cowork's connectors.
3. Authenticate your own Google Ads and Meta Ads accounts (one-time OAuth).
4. Try: `/monthly-paid-review rentumo`
