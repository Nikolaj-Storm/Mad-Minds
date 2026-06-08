"""Google Search Console MCP Server - Prompts Module"""


async def analyze_search_performance(site_url: str, time_period: str = "last 30 days") -> str:
    """
    Generate a prompt for analyzing search performance.
    
    Args:
        site_url: The site to analyze
        time_period: Time period description (e.g., "last 30 days")
        
    Returns:
        Structured prompt for LLM analysis
    """
    return f"""Please analyze the search performance for {site_url} over {time_period}.

Focus on the following aspects:
1. **Traffic Trends**: Analyze clicks and impressions trends
2. **Click-Through Rate (CTR)**: Evaluate CTR performance and identify opportunities
3. **Average Position**: Review ranking positions and identify pages that need improvement
4. **Top Queries**: Identify which queries are driving the most traffic
5. **Top Pages**: Determine which pages are performing best
6. **Opportunities**: Suggest specific opportunities for improvement

Please provide:
- Key insights and observations
- Specific recommendations for improvement
- Priority actions to take

Use the available MCP tools to gather the necessary data:
- Use `query_search_analytics` to get detailed analytics data
- Use the resource `gsc://sites/{site_url}/analytics/summary` for a quick overview
- Use the resource `gsc://sites/{site_url}/top-queries` for top queries
- Use the resource `gsc://sites/{site_url}/top-pages` for top pages
"""


async def seo_recommendations(site_url: str, focus_area: str = "general") -> str:
    """
    Generate a prompt for SEO recommendations.
    
    Args:
        site_url: The site to analyze
        focus_area: Specific area to focus on (queries, pages, technical, general)
        
    Returns:
        Prompt for generating SEO recommendations
    """
    focus_guidance = {
        "queries": "Focus specifically on query optimization, keyword targeting, and search intent alignment.",
        "pages": "Focus on page-level optimization, content quality, and on-page SEO factors.",
        "technical": "Focus on technical SEO aspects like indexing, crawlability, and site structure.",
        "general": "Provide comprehensive SEO recommendations across all areas."
    }
    
    guidance = focus_guidance.get(focus_area, focus_guidance["general"])
    
    return f"""Please provide SEO recommendations for {site_url}.

{guidance}

Your analysis should include:
1. **Current Performance Assessment**: Review current search performance metrics
2. **Strengths**: Identify what's working well
3. **Weaknesses**: Identify areas that need improvement
4. **Opportunities**: Suggest specific opportunities to capture more traffic
5. **Threats**: Identify potential issues or risks
6. **Action Plan**: Provide prioritized, actionable recommendations

Use the available MCP tools to gather data:
- Use `query_search_analytics` with different dimensions (query, page, country, device)
- Use `list_sitemaps` to check sitemap status
- Use `inspect_url` to check indexing status of key pages
- Use resources for quick overviews

Provide specific, actionable recommendations with expected impact.
"""


async def compare_periods(
    site_url: str,
    period1_start: str,
    period1_end: str,
    period2_start: str,
    period2_end: str
) -> str:
    """
    Generate a prompt for comparing two time periods.
    
    Args:
        site_url: The site to analyze
        period1_start: First period start date (YYYY-MM-DD)
        period1_end: First period end date (YYYY-MM-DD)
        period2_start: Second period start date (YYYY-MM-DD)
        period2_end: Second period end date (YYYY-MM-DD)
        
    Returns:
        Prompt for period-over-period comparison
    """
    return f"""Please compare search performance for {site_url} between two time periods:

**Period 1**: {period1_start} to {period1_end}
**Period 2**: {period2_start} to {period2_end}

Your comparison should include:

1. **Overall Metrics Comparison**:
   - Total clicks (change and % change)
   - Total impressions (change and % change)
   - Average CTR (change and % change)
   - Average position (change and % change)

2. **Query Analysis**:
   - New queries that appeared in Period 2
   - Queries that disappeared from Period 1
   - Queries with significant performance changes
   - Top gaining and losing queries

3. **Page Analysis**:
   - Pages with the biggest improvements
   - Pages with the biggest declines
   - New pages gaining traffic

4. **Insights**:
   - What changed and why (if identifiable)
   - Seasonal factors to consider
   - Recommendations based on the comparison

Use the `query_search_analytics` tool twice:
1. First call with dates {period1_start} to {period1_end}
2. Second call with dates {period2_start} to {period2_end}

Then compare the results and provide detailed insights.
"""


async def indexing_health_check(site_url: str) -> str:
    """
    Generate a prompt for checking indexing health.
    
    Args:
        site_url: The site to check
        
    Returns:
        Prompt for indexing health check
    """
    return f"""Please perform an indexing health check for {site_url}.

Your analysis should cover:

1. **Sitemap Status**:
   - List all submitted sitemaps
   - Check for errors or warnings
   - Verify sitemap submission dates
   - Identify any issues

2. **Site Verification**:
   - Confirm site is properly added to Search Console
   - Check permission level

3. **URL Inspection** (for key pages):
   - Check indexing status of important pages
   - Identify any indexing issues
   - Review mobile usability
   - Check for rich results eligibility

4. **Recommendations**:
   - Suggest fixes for any issues found
   - Recommend sitemap improvements
   - Suggest pages to inspect if issues are found

Use the following MCP tools:
- `list_sitemaps` to get all sitemaps
- `get_sitemap` to check individual sitemap details
- `get_site` to verify site status
- `inspect_url` to check specific URLs (ask user for important URLs to check)

Provide a comprehensive health report with actionable recommendations.
"""
