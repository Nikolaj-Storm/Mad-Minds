"""Google Search Console MCP Server - Resources Module"""

from typing import Any, Optional
from fastmcp import Context
from fastmcp.server.dependencies import get_access_token

from .auth import get_gsc_service
from .utils import decode_site_url, format_analytics_response, format_error_message, get_date_range


async def get_sites_list(ctx: Context = None) -> str:
    """
    Resource: gsc://sites
    List all available sites in the user's Search Console account.
    
    Returns:
        JSON string with list of sites and permission levels
    """
    try:
        if ctx:
            ctx.info("Requesting access token for gsc://sites")

        token = get_access_token()
        access_token = token.token
        
        if ctx:
            ctx.info(f"Got access token (type: {type(token)})")
        
        service = get_gsc_service(access_token)
        
        if ctx:
            ctx.info("Calling Google Search Console API: sites.list")
            
        response = service.sites().list().execute()
        
        sites = response.get('siteEntry', [])
        
        if ctx:
            ctx.info(f"Found {len(sites)} sites")
        
        import json
        return json.dumps({
            'sites': sites,
            'total': len(sites)
        }, indent=2)
        
    except Exception as e:
        if ctx:
            ctx.error(f"Error in get_sites_list: {e}")
            
        import json
        return json.dumps({
            'error': format_error_message(e)
        }, indent=2)


async def get_config() -> str:
    """
    Resource: gsc://config
    Get server configuration and status.
    
    Returns:
        JSON string with server configuration
    """
    import json
    return json.dumps({
        'server': 'Google Search Console MCP',
        'version': '0.1.0',
        'api_version': 'v1',
        'authentication': 'Google OAuth 2.0',
        'scopes': [
            'openid',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/webmasters'
        ]
    }, indent=2)


async def get_analytics_summary(site_url: str, ctx: Context = None) -> str:
    """
    Resource: gsc://sites/{site_url}/analytics/summary
    Get a summary of recent search analytics for a site (last 28 days).
    
    Args:
        site_url: The site URL (URL-encoded)
        
    Returns:
        JSON string with analytics summary
    """
    try:
        # Decode the site URL
        decoded_url = decode_site_url(site_url)
        
        if ctx:
            ctx.info(f"Getting analytics summary for {decoded_url}")
        
        token = get_access_token()
        access_token = token.token
        
        service = get_gsc_service(access_token)
        
        # Get last 28 days of data
        start_date, end_date = get_date_range(28)
        
        if ctx:
            ctx.info(f"Querying analytics for period: {start_date} to {end_date}")
        
        request_body = {
            'startDate': start_date,
            'endDate': end_date,
            'rowLimit': 1
        }
        
        response = service.searchanalytics().query(
            siteUrl=decoded_url,
            body=request_body
        ).execute()
        
        rows = response.get('rows', [])
        summary = {
            'site_url': decoded_url,
            'period': f'{start_date} to {end_date}',
            'total_clicks': rows[0].get('clicks', 0) if rows else 0,
            'total_impressions': rows[0].get('impressions', 0) if rows else 0,
            'average_ctr': round(rows[0].get('ctr', 0) * 100, 2) if rows else 0,
            'average_position': round(rows[0].get('position', 0), 1) if rows else 0
        }
        
        import json
        return json.dumps(summary, indent=2)
        
    except Exception as e:
        if ctx:
            ctx.error(f"Error in get_analytics_summary: {e}")
            
        import json
        return json.dumps({
            'error': format_error_message(e)
        }, indent=2)


async def get_site_sitemaps(site_url: str, ctx: Context = None) -> str:
    """
    Resource: gsc://sites/{site_url}/sitemaps
    Get all sitemaps for a specific site.
    
    Args:
        site_url: The site URL (URL-encoded)
        
    Returns:
        JSON string with list of sitemaps
    """
    try:
        decoded_url = decode_site_url(site_url)
        
        if ctx:
            ctx.info(f"Getting sitemaps for {decoded_url}")
        
        token = get_access_token()
        access_token = token.token
        
        service = get_gsc_service(access_token)
        
        response = service.sitemaps().list(siteUrl=decoded_url).execute()
        
        sitemaps = response.get('sitemap', [])
        
        if ctx:
            ctx.info(f"Found {len(sitemaps)} sitemaps")
        
        import json
        return json.dumps({
            'site_url': decoded_url,
            'sitemaps': sitemaps,
            'total': len(sitemaps)
        }, indent=2)
        
    except Exception as e:
        if ctx:
            ctx.error(f"Error in get_site_sitemaps: {e}")
            
        import json
        return json.dumps({
            'error': format_error_message(e)
        }, indent=2)


async def get_top_queries(site_url: str, ctx: Context = None) -> str:
    """
    Resource: gsc://sites/{site_url}/top-queries
    Get top performing queries for a site (last 7 days, top 10).
    
    Args:
        site_url: The site URL (URL-encoded)
        
    Returns:
        JSON string with top queries
    """
    try:
        decoded_url = decode_site_url(site_url)
        
        if ctx:
            ctx.info(f"Getting top queries for {decoded_url}")
        
        token = get_access_token()
        access_token = token.token
        
        service = get_gsc_service(access_token)
        
        # Get last 7 days of data
        start_date, end_date = get_date_range(7)
        
        if ctx:
            ctx.info(f"Querying top queries for period: {start_date} to {end_date}")
        
        request_body = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': ['query'],
            'rowLimit': 10
        }
        
        response = service.searchanalytics().query(
            siteUrl=decoded_url,
            body=request_body
        ).execute()
        
        formatted = format_analytics_response(response)
        
        import json
        return json.dumps({
            'site_url': decoded_url,
            'period': f'{start_date} to {end_date}',
            'top_queries': formatted['rows']
        }, indent=2)
        
    except Exception as e:
        if ctx:
            ctx.error(f"Error in get_top_queries: {e}")
            
        import json
        return json.dumps({
            'error': format_error_message(e)
        }, indent=2)


async def get_top_pages(site_url: str, ctx: Context = None) -> str:
    """
    Resource: gsc://sites/{site_url}/top-pages
    Get top performing pages for a site (last 7 days, top 10).
    
    Args:
        site_url: The site URL (URL-encoded)
        
    Returns:
        JSON string with top pages
    """
    try:
        decoded_url = decode_site_url(site_url)
        
        if ctx:
            ctx.info(f"Getting top pages for {decoded_url}")
        
        token = get_access_token()
        access_token = token.token
        
        service = get_gsc_service(access_token)
        
        # Get last 7 days of data
        start_date, end_date = get_date_range(7)
        
        if ctx:
            ctx.info(f"Querying top pages for period: {start_date} to {end_date}")
        
        request_body = {
            'startDate': start_date,
            'endDate': end_date,
            'dimensions': ['page'],
            'rowLimit': 10
        }
        
        response = service.searchanalytics().query(
            siteUrl=decoded_url,
            body=request_body
        ).execute()
        
        formatted = format_analytics_response(response)
        
        import json
        return json.dumps({
            'site_url': decoded_url,
            'period': f'{start_date} to {end_date}',
            'top_pages': formatted['rows']
        }, indent=2)
        
    except Exception as e:
        if ctx:
            ctx.error(f"Error in get_top_pages: {e}")
            
        import json
        return json.dumps({
            'error': format_error_message(e)
        }, indent=2)
