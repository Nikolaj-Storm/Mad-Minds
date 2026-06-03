# Build-Hub Runbook — paste this into Claude Cowork

**Purpose:** Have Cowork build the entire Mad Minds hub in Google Drive for you, so you don't create folders by hand. *(The Mad Minds Hub has already been built once at https://drive.google.com/drive/folders/1aLu66XMaCKptC3GEYql20tHsbzDUCCpN — this runbook is kept for reruns or recovery.)*

**Before you start:**
- Open Claude Cowork signed into the OnlineMinds Hub owner Google account (the one that owns the Mad Minds root folder).
- Connect the Google Drive connector (Customize → Connectors → Google Drive → authorize).
- Build the Hub as a regular **folder in My Drive**, not a Workspace Shared Drive — the Cowork Drive connector currently can't see content in Shared Drives.
- Then paste everything in the "PROMPT TO PASTE" block below into Cowork.
- After it finishes, you do the permission/sharing step manually (Cowork can't set Google sharing reliably) — see "After Cowork finishes" at the bottom.

---

## PROMPT TO PASTE

You have access to my Google Drive. Build a shared workspace exactly as specified. Create real folders and files in Drive. Work top-down, confirm each major step, and give me the link to the root folder at the end.

1. In My Drive, create a root folder named: **Mad Minds**

2. Inside it, create these folders and subfolders:
   - `00_START_HERE`
   - `01_Knowledge_Base` with subfolders: `brand/rentumo`, `brand/adsumo`, `brand/printumo`, `brand/bidumo`, `playbooks`, `ICP-and-personas`, `past-campaigns`
   - `02_Brand_Assets` with subfolders: `logos`, `fonts`, `imagery`, `templates`
   - `03_Data` with subfolders: `raw_exports`, `cleaned`, `connectors-cache`
   - `04_Reports` with subfolders: `_templates`, `weekly`, `monthly`, `quarterly`, `ad-hoc`
   - `05_Plans_and_Strategy` with subfolders: `campaign-briefs`, `content-calendars`, `growth-experiments`
   - `06_Automation_Outputs` with subfolders: `logs`, `scheduled`
   - `07_People` — and inside it create one subfolder per marketer. Use these names (lowercase first names): nikolaj, silas, frederik, caroline, nilas. (Tell me if I should add or remove any.)

3. In `00_START_HERE`, create a Google Doc named **README** with this content:

   Title: Mad Minds
   Body:
   This Drive folder is the shared workspace for the marketing department. Each person runs their own Claude Cowork session against it via the onlineminds-marketing plugin. Sessions are private; the files here are shared.
   How it works: Skills read from 03_Data and write finished work to 04_Reports or 05_Plans_and_Strategy. Drafts and WIP go to your personal folder under 07_People. Naming: YYYY-MM-DD_<brand>_<type>[_<detail>] — date-prefixed, brand-tagged, lowercase. Brands: rentumo, adsumo, printumo, bidumo (use portfolio for cross-brand). Never put API keys or secrets in any file here.
   First-time setup for a marketer: install the onlineminds-marketing plugin, connect this Hub folder, authorize your own Google Ads + Meta Ads, then try /monthly-paid-review rentumo.

4. In `00_START_HERE`, create a Google Doc named **naming-conventions** with this content:
   Format: YYYY-MM-DD_<brand>_<type>[_<detail>].<ext>
   Brand: rentumo | adsumo | printumo | bidumo | portfolio
   Type slug: monthly-paid-review | wasted-spend | seo-geo-audit | content-brief | campaign-plan | competitor-scan
   Examples: 2026-06-01_rentumo_monthly-paid-review ; 2026-06-01_portfolio_competitor-scan_nl

5. In `07_People`, create a Google Doc named **README** explaining: one subfolder per marketer (lowercase first name); skills save here by default; say "publish to the team" to copy a finished file into the shared folders; everyone with an `@onlineminds.io` account has Editor on the entire Hub (Drive version history is the safety net if something is overwritten by accident).

6. In `04_Reports/_templates`, create a Google Doc named **monthly-paid-review-template** with this structure (leave the values blank for skills to fill):
   Heading: Monthly Paid Review — {{brand}} — {{month}}
   Line: Data source / Date range / Currency / Attribution
   Section: Executive summary (3 sentences)
   Section: KPI dashboard — a table with columns Metric | This month | Prior month | MoM change | Target | Status, and rows Spend, Conversions, CPA, ROAS, Conversion rate
   Section: Per-channel breakdown — one table for Google Ads, one for Meta Ads (same columns)
   Section: What worked (1,2,3)
   Section: What needs fixing (1,2,3)
   Section: Recommendations — table Action | Why | Impact | Effort | Priority
   Section: Next month focus (1,2,3)

7. In each `01_Knowledge_Base/brand/<brand>` folder, create a placeholder Google Doc named **brand-voice** with headings: Voice attributes; Tone; Preferred terms; Banned terms; Positioning; Language (DK/EN). Leave the content for me to fill.

8. In `06_Automation_Outputs/logs`, create a Google Doc **action-log** with a header row: Timestamp | Person | Brand | Platform | Entity | Change | Accept-phrase used. This is the audit trail for ad changes.

9. When done, list the full folder tree you created and give me the shareable link to the root **Mad Minds** folder.

---

## After Cowork finishes (you do this, ~1 min)
Set Google sharing by hand (Cowork can't do this):
1. Open the root **Mad Minds** folder → **Share** → set General access to **OnlineMinds.io: Editor**. Every `@onlineminds.io` account now has Editor on the entire Hub.
2. Open a Cowork session as a normal team member and confirm they can read the Hub AND write a test file. If they can't see it, switch to Google Drive for Desktop local sync.

> `01_Knowledge_Base/` and `04_Reports/_templates/` are intentionally **editable** by everyone. Drive's per-file version history (File → Version history) is the safety net if something gets accidentally overwritten.
