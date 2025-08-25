"""API client utilities for Upstage MCP server."""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Dict, Any, Optional
from mcp.server.fastmcp import Context

from upstage_mcp.utils.constants import MINUTE

# API Configuration
REQUEST_TIMEOUT = 5 * MINUTE


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.RequestError))
)
async def make_api_request(
    url: str, 
    headers: Optional[Dict[str, str]] = None,
    api_key: str = None,
    ctx: Optional[Context] = None,
    operation: str = "API operation",
    timeout: int = REQUEST_TIMEOUT,
    **kwargs
) -> dict:
    """
    Make an API request with retry logic, mandatory Upstage headers, and error handling.
    
    Args:
        url: API endpoint URL
        headers: Optional request headers (will be merged with Upstage headers)
        api_key: Upstage API key (required if not in headers)
        ctx: Optional MCP context for error reporting
        operation: Description of the operation for error messages
        timeout: Timeout in seconds (defaults to REQUEST_TIMEOUT)
        **kwargs: Additional arguments for httpx.post (files, data, json, etc.)
        
    Returns:
        API response as a dict
        
    Raises:
        Exception: If the request fails with a formatted error message
    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
        try:
            # Merge headers: Upstage headers (base) | provided headers (override)
            final_headers = (headers or {}) | _get_upstage_headers(api_key)
            
            response = await client.post(url, headers=final_headers, **kwargs)
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP error from Upstage API: {e.response.status_code} - {e.response.text}"
            if ctx:
                await ctx.error(error_msg)
            raise Exception(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Request error connecting to Upstage API: {e}"
            if ctx:
                await ctx.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error during {operation}: {str(e)}"
            if ctx:
                await ctx.error(error_msg)
            raise Exception(error_msg)


def _get_upstage_headers(api_key: str) -> dict:
    """
    Get standard headers for Upstage API requests.
    
    Args:
        api_key: Upstage API key
        
    Returns:
        Dictionary with Authorization and x-upstage-client headers
    """
    return {
        "Authorization": f"Bearer {api_key}",
        "x-upstage-client": "mcp",
    }



