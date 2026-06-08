"""Google Search Console MCP Server - Utility Functions"""

from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote, unquote


def validate_date(date_str: str) -> bool:
    """
    Validate date string is in YYYY-MM-DD format.
    
    Args:
        date_str: Date string to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def format_date(date_str: str) -> str:
    """
    Format date string to YYYY-MM-DD format.
    
    Args:
        date_str: Date string to format
        
    Returns:
        Formatted date string
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%Y-%m-%d")


def get_date_range(days: int = 28) -> tuple[str, str]:
    """
    Get date range for the last N days.
    
    Args:
        days: Number of days to go back (default: 28)
        
    Returns:
        Tuple of (start_date, end_date) in YYYY-MM-DD format
    """
    end_date = datetime.now() - timedelta(days=3)  # GSC data has ~3 day delay
    start_date = end_date - timedelta(days=days)
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


def encode_site_url(site_url: str) -> str:
    """
    URL encode a site URL for use in API calls.
    
    Args:
        site_url: Site URL to encode
        
    Returns:
        URL-encoded site URL
    """
    return quote(site_url, safe='')


def decode_site_url(encoded_url: str) -> str:
    """
    URL decode a site URL.
    
    Args:
        encoded_url: Encoded site URL
        
    Returns:
        Decoded site URL
    """
    return unquote(encoded_url)


def format_analytics_response(response: dict[str, Any]) -> dict[str, Any]:
    """
    Format Google Search Console analytics response for better readability.
    
    Args:
        response: Raw API response
        
    Returns:
        Formatted response with cleaner structure
    """
    rows = response.get('rows', [])
    
    formatted_rows = []
    for row in rows:
        formatted_row = {}
        
        # Add dimensions (keys)
        if 'keys' in row:
            for i, key in enumerate(row['keys']):
                dimension_name = response.get('responseAggregationType', 'dimension')
                formatted_row[f'dimension_{i}'] = key
        
        # Add metrics
        formatted_row['clicks'] = row.get('clicks', 0)
        formatted_row['impressions'] = row.get('impressions', 0)
        formatted_row['ctr'] = round(row.get('ctr', 0) * 100, 2)  # Convert to percentage
        formatted_row['position'] = round(row.get('position', 0), 1)
        
        formatted_rows.append(formatted_row)
    
    return {
        'rows': formatted_rows,
        'total_rows': len(formatted_rows)
    }


def format_error_message(error: Exception) -> str:
    """
    Format error message for user-friendly display.
    
    Args:
        error: Exception object
        
    Returns:
        Formatted error message
    """
    error_str = str(error)
    
    # Common error patterns
    if "403" in error_str:
        return "Permission denied. Please check that you have access to this site in Google Search Console."
    elif "404" in error_str:
        return "Resource not found. Please verify the site URL or resource path."
    elif "401" in error_str:
        return "Authentication failed. Please re-authenticate with Google."
    elif "429" in error_str:
        return "Rate limit exceeded. Please try again later."
    elif "400" in error_str:
        return f"Invalid request: {error_str}"
    else:
        return f"An error occurred: {error_str}"
