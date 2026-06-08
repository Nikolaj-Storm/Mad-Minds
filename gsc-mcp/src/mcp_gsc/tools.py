"""Google Search Console MCP Server - Tools Module"""

from typing import Any, Optional

from fastmcp import Context
from fastmcp.server.dependencies import get_access_token

from .auth import get_gsc_service
from .utils import format_analytics_response, format_error_message, validate_date


async def query_search_analytics(
    site_url: str,
    start_date: str,
    end_date: str,
    dimensions: Optional[list[str]] = None,
    row_limit: int = 1000,
    start_row: int = 0,
    ctx: Optional[Context] = None,
) -> dict[str, Any]:
    """
    Query search analytics data for a site.
    
    Args:
        site_url: The site URL (e.g., "https://example.com/")
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        dimensions: Dimensions to group by (query, page, country, device, searchAppearance, date)
        row_limit: Maximum rows to return (default: 1000, max: 25000)
        start_row: Zero-based index of first row to return
        ctx: FastMCP context for logging
        
    Returns:
        Search analytics data with clicks, impressions, CTR, and position metrics
    """
    try:
        if ctx:
            await ctx.info(f"Querying search analytics for {site_url} from {start_date} to {end_date}")
        
        # Validate dates
        if not validate_date(start_date) or not validate_date(end_date):
            raise ValueError("Dates must be in YYYY-MM-DD format")
        
        # Get access token from FastMCP
        token = get_access_token()
        access_token = token.token
        
        # Get authenticated service
        service = get_gsc_service(access_token)
        
        # Build request body
        request_body = {
            'startDate': start_date,
            'endDate': end_date,
            'rowLimit': min(row_limit, 25000),
            'startRow': start_row,
        }
        
        if dimensions:
            request_body['dimensions'] = dimensions
        
        # Execute query
        response = service.searchanalytics().query(
            siteUrl=site_url,
            body=request_body
        ).execute()
        
        if ctx:
            await ctx.info(f"Retrieved {len(response.get('rows', []))} rows")
        
        return format_analytics_response(response)
        
    except Exception as e:
        error_msg = format_error_message(e)
        if ctx:
            await ctx.error(error_msg)
        raise Exception(error_msg)


async def list_sitemaps(
    site_url: str,
    ctx: Optional[Context] = None,
) -> dict[str, Any]:
    """
    List all sitemaps for a site.
    
    Args:
        site_url: The site URL
        ctx: FastMCP context for logging
        
    Returns:
        List of sitemaps with submission status and error information
    """
    try:
        if ctx:
            await ctx.info(f"Listing sitemaps for {site_url}")
        
        token = get_access_token()
        access_token = token.token
        
        service = get_gsc_service(access_token)
        
        response = service.sitemaps().list(siteUrl=site_url).execute()
        
        sitemaps = response.get('sitemap', [])
        if ctx:
            await ctx.info(f"Found {len(sitemaps)} sitemaps")
        
        return {
            'sitemaps': sitemaps,
            'total': len(sitemaps)
        }
        
    except Exception as e:
        error_msg = format_error_message(e)
        if ctx:
            await ctx.error(error_msg)
        raise Exception(error_msg)


async def get_sitemap(
    site_url: str,
    feedpath: str,
    ctx: Optional[Context] = None,
) -> dict[str, Any]:
    """
    Get information about a specific sitemap.
    
    Args:
        site_url: The site URL
        feedpath: The sitemap URL
        ctx: FastMCP context for logging
        
    Returns:
        Sitemap details including submission date, errors, and warnings
    """
    try:
        if ctx:
            await ctx.info(f"Getting sitemap {feedpath} for {site_url}")
        
        token = get_access_token()
        access_token = token.token
        
        service = get_gsc_service(access_token)
        
        response = service.sitemaps().get(
            siteUrl=site_url,
            feedpath=feedpath
        ).execute()
        
        return response
        
    except Exception as e:
        error_msg = format_error_message(e)
        if ctx:
            await ctx.error(error_msg)
        raise Exception(error_msg)


async def submit_sitemap(
    site_url: str,
    feedpath: str,
    ctx: Optional[Context] = None,
) -> dict[str, str]:
    """
    Submit a sitemap to Google.
    
    Args:
        site_url: The site URL
        feedpath: The sitemap URL to submit
        ctx: FastMCP context for logging
        
    Returns:
        Confirmation of submission
    """
    try:
        if ctx:
            await ctx.info(f"Submitting sitemap {feedpath} for {site_url}")
        
        token = get_access_token()
        access_token = token.token
        
        service = get_gsc_service(access_token)
        
        service.sitemaps().submit(
            siteUrl=site_url,
            feedpath=feedpath
        ).execute()
        
        if ctx:
            await ctx.info("Sitemap submitted successfully")
        
        return {
            'status': 'success',
            'message': f'Sitemap {feedpath} submitted successfully'
        }
        
    except Exception as e:
        error_msg = format_error_message(e)
        if ctx:
            await ctx.error(error_msg)
        raise Exception(error_msg)


async def delete_sitemap(
    site_url: str,
    feedpath: str,
    ctx: Optional[Context] = None,
) -> dict[str, str]:
    """
    Delete a sitemap from Google Search Console.
    
    Args:
        site_url: The site URL
        feedpath: The sitemap URL to delete
        ctx: FastMCP context for logging
        
    Returns:
        Confirmation of deletion
    """
    try:
        if ctx:
            await ctx.info(f"Deleting sitemap {feedpath} for {site_url}")
        
        token = get_access_token()
        access_token = token.token
        
        service = get_gsc_service(access_token)
        
        service.sitemaps().delete(
            siteUrl=site_url,
            feedpath=feedpath
        ).execute()
        
        if ctx:
            await ctx.info("Sitemap deleted successfully")
        
        return {
            'status': 'success',
            'message': f'Sitemap {feedpath} deleted successfully'
        }
        
    except Exception as e:
        error_msg = format_error_message(e)
        if ctx:
            await ctx.error(error_msg)
        raise Exception(error_msg)


async def list_sites(
    ctx: Optional[Context] = None,
) -> dict[str, Any]:
    """
    List all sites in the user's Search Console account.
    
    Args:
        ctx: FastMCP context for logging
        
    Returns:
        List of sites with permission levels
    """
    try:
        if ctx:
            await ctx.info("Listing all sites")
        
        token = get_access_token()
        access_token = token.token
        
        service = get_gsc_service(access_token)
        
        response = service.sites().list().execute()
        
        sites = response.get('siteEntry', [])
        if ctx:
            await ctx.info(f"Found {len(sites)} sites")
        
        return {
            'sites': sites,
            'total': len(sites)
        }
        
    except Exception as e:
        error_msg = format_error_message(e)
        if ctx:
            await ctx.error(error_msg)
        raise Exception(error_msg)


async def get_site(
    site_url: str,
    ctx: Optional[Context] = None,
) -> dict[str, Any]:
    """
    Get information about a specific site.
    
    Args:
        site_url: The site URL
        ctx: FastMCP context for logging
        
    Returns:
        Site details and permission level
    """
    try:
        if ctx:
            await ctx.info(f"Getting site information for {site_url}")
        
        token = get_access_token()
        access_token = token.token
        
        service = get_gsc_service(access_token)
        
        response = service.sites().get(siteUrl=site_url).execute()
        
        return response
        
    except Exception as e:
        error_msg = format_error_message(e)
        if ctx:
            await ctx.error(error_msg)
        raise Exception(error_msg)


async def add_site(
    site_url: str,
    ctx: Optional[Context] = None,
) -> dict[str, str]:
    """
    Add a site to Search Console account.
    
    Args:
        site_url: The site URL to add
        ctx: FastMCP context for logging
        
    Returns:
        Confirmation of site addition
    """
    try:
        if ctx:
            await ctx.info(f"Adding site {site_url}")
        
        token = get_access_token()
        access_token = token.token
        
        service = get_gsc_service(access_token)
        
        service.sites().add(siteUrl=site_url).execute()
        
        if ctx:
            await ctx.info("Site added successfully")
        
        return {
            'status': 'success',
            'message': f'Site {site_url} added successfully'
        }
        
    except Exception as e:
        error_msg = format_error_message(e)
        if ctx:
            await ctx.error(error_msg)
        raise Exception(error_msg)


async def delete_site(
    site_url: str,
    ctx: Optional[Context] = None,
) -> dict[str, str]:
    """
    Remove a site from Search Console account.
    
    Args:
        site_url: The site URL to remove
        ctx: FastMCP context for logging
        
    Returns:
        Confirmation of site removal
    """
    try:
        if ctx:
            await ctx.info(f"Deleting site {site_url}")
        
        token = get_access_token()
        access_token = token.token
        
        service = get_gsc_service(access_token)
        
        service.sites().delete(siteUrl=site_url).execute()
        
        if ctx:
            await ctx.info("Site deleted successfully")
        
        return {
            'status': 'success',
            'message': f'Site {site_url} deleted successfully'
        }
        
    except Exception as e:
        error_msg = format_error_message(e)
        if ctx:
            await ctx.error(error_msg)
        raise Exception(error_msg)


async def inspect_url(
    inspection_url: str,
    site_url: str,
    language_code: str = "en-US",
    ctx: Optional[Context] = None,
) -> dict[str, Any]:
    """
    Inspect the Google index status of a specific URL.
    
    Args:
        inspection_url: The URL to inspect
        site_url: The site URL that owns the inspection URL
        language_code: Language code (default: "en-US")
        ctx: FastMCP context for logging
        
    Returns:
        Detailed index status including coverage, indexing issues, mobile usability, etc.
    """
    try:
        if ctx:
            await ctx.info(f"Inspecting URL {inspection_url}")
        
        token = get_access_token()
        access_token = token.token
        
        service = get_gsc_service(access_token)
        
        request_body = {
            'inspectionUrl': inspection_url,
            'siteUrl': site_url,
            'languageCode': language_code
        }
        
        response = service.urlInspection().index().inspect(
            body=request_body
        ).execute()
        
        if ctx:
            await ctx.info("URL inspection completed")
        
        return response
        
    except Exception as e:
        error_msg = format_error_message(e)
        if ctx:
            await ctx.error(error_msg)
        raise Exception(error_msg)
