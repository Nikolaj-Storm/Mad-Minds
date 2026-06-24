"""Google Search Console MCP Server - Main Server Module"""

import os

from fastmcp import FastMCP, Context
from fastmcp.server.dependencies import get_context

from mcp_gsc import prompts, resources, tools


def _build_auth():
    """Build the Google OAuth-proxy provider with persistent storage.

    Storage backend is selected automatically so the same code runs on Vercel
    and on a Docker/VPS host. Persisting the registered OAuth clients + issued
    tokens means marketers sign in once, ever, and are never logged out by a
    redeploy:
    - Vercel / stateless: set KV_REST_API_URL + KV_REST_API_TOKEN (Vercel KV) or
      UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN (manual Upstash).
    - Docker / VPS / Fly: set CLIENT_STORAGE_DIR to a mounted volume path.
    Without a client_id OR any storage backend, we fall back to FastMCP's
    env-var auto-config (in-memory; fine for local/dev).
    """
    client_id = os.environ.get("FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID")
    redis_url = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
    redis_token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    storage_dir = os.environ.get("CLIENT_STORAGE_DIR")

    if not client_id or not ((redis_url and redis_token) or storage_dir):
        return None  # fall back to env auto-config (in-memory)

    from fastmcp.server.auth.providers.google import GoogleProvider

    # Redis (Vercel KV / Upstash) takes priority; fall back to disk for Docker/Fly.
    if redis_url and redis_token:
        from mcp_gsc.redis_store import RedisStore
        storage = RedisStore(
            url=redis_url,
            token=redis_token,
            prefix=os.environ.get("REDIS_KEY_PREFIX", ""),
        )
    else:
        from key_value.aio.stores.disk import DiskStore
        storage = DiskStore(directory=storage_dir)

    scopes = os.environ.get(
        "FASTMCP_SERVER_AUTH_GOOGLE_REQUIRED_SCOPES",
        "openid,https://www.googleapis.com/auth/userinfo.email,"
        "https://www.googleapis.com/auth/webmasters.readonly",
    )
    kwargs = dict(
        client_id=client_id,
        client_secret=os.environ["FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET"],
        base_url=os.environ.get("FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL", "http://localhost:8000"),
        required_scopes=[s.strip() for s in scopes.split(",") if s.strip()],
        client_storage=storage,
        # Skip FastMCP's extra /consent interstitial. It adds a hop/click that
        # native connectors (Drive/Notion) don't have, and it was timing out the
        # MCP client's localhost callback listener -> "No OAuth flow is in progress".
        require_authorization_consent=False,
    )
    jwt_key = os.environ.get("JWT_SIGNING_KEY")
    if jwt_key:
        kwargs["jwt_signing_key"] = jwt_key
    return GoogleProvider(**kwargs)


# Create FastMCP server instance.
# - With persistence env (CLIENT_STORAGE_DIR + JWT_SIGNING_KEY): explicit provider
#   with disk-backed client storage -> sign in once, survives restarts/redeploys.
# - Without it: FastMCP auto-configures auth from FASTMCP_SERVER_AUTH_* env vars
#   (in-memory). See .env.example.
_auth = _build_auth()
mcp = FastMCP(name="Google Search Console", auth=_auth) if _auth else FastMCP(name="Google Search Console")


# ============================================================================
# CUSTOM ROUTES - Additional HTTP endpoints
# ============================================================================

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request) -> dict:
    """Health check endpoint for monitoring and load balancers."""
    from starlette.responses import JSONResponse
    return JSONResponse({
        "status": "healthy",
        "service": "Google Search Console MCP Server",
        "version": "1.0.0"
    })


# ============================================================================
# TOOLS - Actions that LLMs can perform
# ============================================================================

@mcp.tool(tags=["Analytics"])
async def query_search_analytics(
    site_url: str,
    start_date: str,
    end_date: str,
    dimensions: list[str] | None = None,
    row_limit: int = 1000,
    start_row: int = 0,
) -> dict:
    """
    Query search analytics data for a site with filters and parameters.
    
    Args:
        site_url: The site URL (e.g., "https://example.com/")
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        dimensions: Dimensions to group by (query, page, country, device, searchAppearance, date)
        row_limit: Maximum rows to return (default: 1000, max: 25000)
        start_row: Zero-based index of first row to return
        
    Returns:
        Search analytics data with clicks, impressions, CTR, and position metrics
    """
    from fastmcp import Context
    ctx = get_context()
    return await tools.query_search_analytics(
        site_url, start_date, end_date, dimensions, row_limit, start_row, ctx
    )


@mcp.tool(tags=["Sitemaps"])
async def list_sitemaps(site_url: str) -> dict:
    """
    List all sitemaps for a site.
    
    Args:
        site_url: The site URL
        
    Returns:
        List of sitemaps with submission status and error information
    """
    from fastmcp import Context
    ctx = get_context()
    return await tools.list_sitemaps(site_url, ctx)


@mcp.tool(tags=["Sitemaps"])
async def get_sitemap(site_url: str, feedpath: str) -> dict:
    """
    Get information about a specific sitemap.
    
    Args:
        site_url: The site URL
        feedpath: The sitemap URL
        
    Returns:
        Sitemap details including submission date, errors, and warnings
    """
    from fastmcp import Context
    ctx = get_context()
    return await tools.get_sitemap(site_url, feedpath, ctx)


@mcp.tool(tags=["Sitemaps"])
async def submit_sitemap(site_url: str, feedpath: str) -> dict:
    """
    Submit a sitemap to Google.
    
    Args:
        site_url: The site URL
        feedpath: The sitemap URL to submit
        
    Returns:
        Confirmation of submission
    """
    from fastmcp import Context
    ctx = get_context()
    return await tools.submit_sitemap(site_url, feedpath, ctx)


@mcp.tool(tags=["Sitemaps"])
async def delete_sitemap(site_url: str, feedpath: str) -> dict:
    """
    Delete a sitemap from Google Search Console.
    
    Args:
        site_url: The site URL
        feedpath: The sitemap URL to delete
        
    Returns:
        Confirmation of deletion
    """
    from fastmcp import Context
    ctx = get_context()
    return await tools.delete_sitemap(site_url, feedpath, ctx)


@mcp.tool(tags=["Sites"])
async def list_sites() -> dict:
    """
    List all sites in the user's Search Console account.
    
    Returns:
        List of sites with permission levels
    """
    from fastmcp import Context
    ctx = get_context()
    return await tools.list_sites(ctx)


@mcp.tool(tags=["Sites"])
async def get_site(site_url: str) -> dict:
    """
    Get information about a specific site.
    
    Args:
        site_url: The site URL
        
    Returns:
        Site details and permission level
    """
    from fastmcp import Context
    ctx = get_context()
    return await tools.get_site(site_url, ctx)


@mcp.tool(tags=["Sites"])
async def add_site(site_url: str) -> dict:
    """
    Add a site to Search Console account.
    
    Args:
        site_url: The site URL to add
        
    Returns:
        Confirmation of site addition
    """
    from fastmcp import Context
    ctx = get_context()
    return await tools.add_site(site_url, ctx)


@mcp.tool(tags=["Sites"])
async def delete_site(site_url: str) -> dict:
    """
    Remove a site from Search Console account.
    
    Args:
        site_url: The site URL to remove
        
    Returns:
        Confirmation of site removal
    """
    from fastmcp import Context
    ctx = get_context()
    return await tools.delete_site(site_url, ctx)


@mcp.tool(tags=["Inspection"])
async def inspect_url(
    inspection_url: str,
    site_url: str,
    language_code: str = "en-US"
) -> dict:
    """
    Inspect the Google index status of a specific URL.
    
    Args:
        inspection_url: The URL to inspect
        site_url: The site URL that owns the inspection URL
        language_code: Language code (default: "en-US")
        
    Returns:
        Detailed index status including coverage, indexing issues, mobile usability, etc.
    """
    from fastmcp import Context
    ctx = get_context()
    return await tools.inspect_url(inspection_url, site_url, language_code, ctx)


# ============================================================================
# RESOURCES - Read-only data sources
# ============================================================================

@mcp.resource("gsc://sites", tags=["Sites"])
async def get_sites_resource(ctx: Context) -> str:
    """List all available sites in the user's Search Console account."""
    return await resources.get_sites_list(ctx)


@mcp.resource("gsc://config", tags=["Configuration"])
async def get_config_resource() -> str:
    """Get server configuration and status."""
    return await resources.get_config()


@mcp.resource("gsc://sites/{site_url}/analytics/summary", tags=["Analytics"])
async def get_analytics_summary_resource(site_url: str, ctx: Context) -> str:
    """Get a summary of recent search analytics for a site (last 28 days)."""
    return await resources.get_analytics_summary(site_url, ctx)


@mcp.resource("gsc://sites/{site_url}/sitemaps", tags=["Sitemaps"])
async def get_sitemaps_resource(site_url: str, ctx: Context) -> str:
    """Get all sitemaps for a specific site."""
    return await resources.get_site_sitemaps(site_url, ctx)


@mcp.resource("gsc://sites/{site_url}/top-queries", tags=["Analytics"])
async def get_top_queries_resource(site_url: str, ctx: Context) -> str:
    """Get top performing queries for a site (last 7 days, top 10)."""
    return await resources.get_top_queries(site_url, ctx)


@mcp.resource("gsc://sites/{site_url}/top-pages", tags=["Analytics"])
async def get_top_pages_resource(site_url: str, ctx: Context) -> str:
    """Get top performing pages for a site (last 7 days, top 10)."""
    return await resources.get_top_pages(site_url, ctx)


# ============================================================================
# PROMPTS - Reusable templates for LLM interactions
# ============================================================================

@mcp.prompt(tags=["Analytics"])
def analyze_search_performance(site_url: str, time_period: str = "last 30 days") -> str:
    """
    Generate a prompt for analyzing search performance.
    
    Args:
        site_url: The site to analyze
        time_period: Time period description (e.g., "last 30 days")
    """
    return prompts.analyze_search_performance(site_url, time_period)


@mcp.prompt(tags=["SEO"])
def seo_recommendations(site_url: str, focus_area: str = "general") -> str:
    """
    Generate a prompt for SEO recommendations.
    
    Args:
        site_url: The site to analyze
        focus_area: Specific area to focus on (queries, pages, technical, general)
    """
    return prompts.seo_recommendations(site_url, focus_area)


@mcp.prompt(tags=["Analytics"])
def compare_periods(
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
    """
    return prompts.compare_periods(
        site_url, period1_start, period1_end, period2_start, period2_end
    )


@mcp.prompt(tags=["Inspection"])
def indexing_health_check(site_url: str) -> str:
    """
    Generate a prompt for checking indexing health.
    
    Args:
        site_url: The site to check
    """
    return prompts.indexing_health_check(site_url)


# ============================================================================
# Entry point for running the server
# ============================================================================

if __name__ == "__main__":
    # Run the server with HTTP transport support
    # Usage:
    #   Development (STDIO): fastmcp dev src/mcp_gsc/server.py
    #   Production (HTTP): fastmcp run src/mcp_gsc/server.py --transport http --host localhost --port 8000
    mcp.run()

