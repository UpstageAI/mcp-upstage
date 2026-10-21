"""API client utilities for Upstage MCP server."""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from typing import Dict, Any, Optional
from mcp.server.fastmcp import Context

from upstage_mcp.utils.constants import MINUTE

# API Configuration
REQUEST_TIMEOUT = 5 * MINUTE


# Failures where the request never reached the server, so retrying cannot
# cause a second (billed) processing of the same document.
RETRYABLE_REQUEST_ERRORS = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)
# Responses that mean the server did not process the request.
RETRYABLE_STATUS_CODES = (429, 503)


def _is_retryable_error(exc: BaseException) -> bool:
    """
    Decide whether a failed request is safe to retry.
    
    The parsing endpoint is paid and not idempotent: a read timeout, a dropped
    connection or a 500/502/504 may arrive after the server already processed
    (and billed) the document. Only failures before the request was sent
    (connect errors, connect/pool timeouts) and explicit "not processed"
    responses (429, 503) are retried.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_STATUS_CODES
    return isinstance(exc, RETRYABLE_REQUEST_ERRORS)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception(_is_retryable_error),
    reraise=True,
)
async def _post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    headers: Dict[str, str],
    **kwargs
) -> dict:
    """POST to the API, letting httpx errors propagate so tenacity can retry them."""
    response = await client.post(url, headers=headers, **kwargs)
    response.raise_for_status()
    return response.json()


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
    
    Only failures where the request was not processed are retried (up to 3
    attempts): connect errors, connect/pool timeouts, and 429/503 responses.
    Read timeouts, other 5xx and 4xx responses fail immediately, because the
    server may already have processed and billed the request.
    
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
    # Merge headers: Upstage headers (base) | provided headers (override)
    final_headers = (headers or {}) | _get_upstage_headers(api_key)

    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
        try:
            return await _post_with_retry(client, url, final_headers, **kwargs)
        except httpx.HTTPStatusError as e:
            cause = e
            error_msg = f"HTTP error from Upstage API: {e.response.status_code} - {e.response.text}"
        except httpx.RequestError as e:
            cause = e
            error_msg = f"Request error connecting to Upstage API: {e}"
        except Exception as e:
            cause = e
            error_msg = f"Error during {operation}: {str(e)}"

    if ctx:
        await ctx.error(error_msg)
    raise Exception(error_msg) from cause


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



