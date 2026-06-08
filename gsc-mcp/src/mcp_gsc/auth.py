"""Google Search Console MCP Server - Authentication Module"""

import os
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def get_gsc_service(access_token: Optional[str] = None):
    """
    Get authenticated Google Search Console API service.
    
    Args:
        access_token: OAuth access token from FastMCP GoogleProvider
        
    Returns:
        Authenticated Google Search Console API service
        
    Raises:
        ValueError: If no access token is provided
    """
    if not access_token:
        raise ValueError("Access token is required for Google Search Console API")
    
    # Create credentials from access token
    credentials = Credentials(token=access_token)
    
    # Build and return the Search Console service
    service = build('searchconsole', 'v1', credentials=credentials)
    return service


def get_required_scopes() -> list[str]:
    """
    Get the required OAuth scopes for Google Search Console API.
    
    Returns:
        List of required OAuth scope URLs
    """
    return [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/webmasters",  # Full access
    ]


def get_readonly_scopes() -> list[str]:
    """
    Get the read-only OAuth scopes for Google Search Console API.
    
    Returns:
        List of read-only OAuth scope URLs
    """
    return [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/webmasters.readonly",  # Read-only access
    ]
