---
name: seo-geo-audit
description: Run an OnlineMinds SEO + GEO (Generative Engine Optimization) audit for a brand and market, covering technical SEO, on-page, content gaps, and AI-citability (llms.txt, schema, Wikidata/entity presence, AI Overview/Perplexity/ChatGPT mentions). Reads account-conventions for brands, markets, and Drive paths. Uses Google Search Console where connected, plus manual SERP/AI checks. Use when asked for an SEO audit, GEO audit, AEO/citability review, or organic-visibility analysis.
argument-hint: "<brand> [market, e.g. NL] [domain]"
---

# SEO + GEO Audit

> Load **account-conventions** first (brand, target markets, domains, Drive paths). This skill encodes OnlineMinds' existing Rentumo SEO/GEO methodology so it can be reused across brands and markets.

## Trigger
`/seo-geo-audit`, or a request for an SEO audit, GEO/AEO audit, citability review, or organic visibility analysis.

## Inputs
1. Brand + market (one of the brand's target markets; ask if missing).
2. Domain / target URL.
3. Competitor set (optional — provide the list).

## Part A — Classic SEO
- **Technical:** indexation, crawlability, site speed signals, structured data presence, robots/sitemap, canonicalization.
- **On-page:** title/meta/heading quality on key pages; thin/duplicate content.
- **Authority / performance:** Google Search Console clicks, impressions, CTR and average position by query and page; top and declining pages/queries. (Backlinks and domain-authority metrics need a dedicated SEO data source, which is not currently connected.)
- **Content gaps:** keywords competitors rank for that the brand does not.

## Part B — GEO / AI citability
- **llms.txt:** present and well-formed? If not, generate one.
- **Schema/entity:** structured data and entity clarity; Wikidata/knowledge-graph presence for the brand entity.
- **AI mentions:** measure brand mentions, share of voice, and cited pages in AI answers (ChatGPT, Perplexity, Google AI Overviews, Gemini) via manual prompt checks — no automated Brand Radar source is connected. Identify which pages get cited and gaps vs. competitors.
- **Citability fixes:** prioritized list to improve being cited (original data/statistics to publish, clear factual phrasing, schema, entity building).

## Output
A prioritized audit report (quick wins vs. strategic investments) saved to `04_Reports/ad-hoc/YYYY-MM-DD_<brand>_seo-geo-audit_<market>/`. Include a citability score/summary and an llms.txt file if generated (save alongside the report). State data sources and dates at top.
