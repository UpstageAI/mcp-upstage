"""Document parsing functionality for Upstage AI services."""

import os
import json
from datetime import datetime
import aiofiles
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx
from pathlib import Path
from typing import Optional, Dict, Any, List

# API Endpoints
DOCUMENT_DIGITIZATION_URL = "https://api.upstage.ai/v1/document-digitization"
REQUEST_TIMEOUT = 300  # 5 minutes

# Setup output directories
def setup_output_directories() -> tuple:
    """Set up output directories for document parsing results."""
    output_dir = Path.home() / ".upstage-mcp-server" / "outputs"
    doc_parsing_dir = output_dir / "document_parsing"
    
    os.makedirs(doc_parsing_dir, exist_ok=True)
    return output_dir, doc_parsing_dir


async def async_json_dump(data, filepath, **kwargs):
    """Save JSON data asynchronously to avoid blocking the event loop."""
    async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, **kwargs))


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.RequestError))
)
async def make_api_request(client: httpx.AsyncClient, url: str, headers: dict, **kwargs) -> dict:
    """Make an API request with retry logic."""
    response = await client.post(url, headers=headers, **kwargs)
    response.raise_for_status()
    return response.json()


async def parse_document_api(
    file_path: str,
    api_key: str,
    ctx=None,  # Optional context for progress reporting
    output_formats: List[str] = None
) -> Dict[str, Any]:
    """
    Parse a document using Upstage AI's document digitization API.
    
    Args:
        file_path: Path to the document file to be processed
        api_key: Upstage API key
        ctx: Optional MCP context for progress reporting
        output_formats: List of output formats (default: None)
        
    Returns:
        API response as a dict
    """
    if not os.path.exists(file_path):
        error_msg = f"File not found at {file_path}"
        if ctx:
            ctx.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    # Initialize progress reporting if context provided
    if ctx:
        ctx.info(f"Starting to process {file_path}")
        await ctx.report_progress(10, 100)
    
    try:
        # Initialize API client with timeout
        async with httpx.AsyncClient(timeout=httpx.Timeout(REQUEST_TIMEOUT)) as client:
            headers = {"Authorization": f"Bearer {api_key}"}
            
            if ctx:
                await ctx.report_progress(30, 100)
            
            # Process document
            with open(file_path, "rb") as file:
                files = {"document": file}
                data = {
                    "ocr": "force", 
                    "base64_encoding": "['table']", 
                    "model": "document-parse"
                }
                
                # Add output_formats if provided
                if output_formats:
                    data["output_formats"] = json.dumps(output_formats)
                
                # Make request with retry
                result = await make_api_request(
                    client,
                    DOCUMENT_DIGITIZATION_URL,
                    headers=headers,
                    files=files,
                    data=data
                )
            
            if ctx:
                await ctx.report_progress(80, 100)
                
            return result
            
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error from Upstage API: {e.response.status_code} - {e.response.text}"
        if ctx:
            ctx.error(error_msg)
        raise
    except httpx.RequestError as e:
        error_msg = f"Request error connecting to Upstage API: {e}"
        if ctx:
            ctx.error(error_msg)
        raise
    except Exception as e:
        error_msg = f"Error processing document: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        raise


async def save_document_parsing_result(
    result: Dict[str, Any], 
    file_path: str, 
    ctx=None
) -> Optional[Path]:
    """
    Save document parsing result to disk.
    
    Args:
        result: The API response to save
        file_path: Original document path (used for naming)
        ctx: Optional MCP context for progress reporting
        
    Returns:
        Path to the saved file or None if save failed
    """
    _, doc_parsing_dir = setup_output_directories()
    
    try:
        # Add timestamp to prevent overwriting
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        response_file = doc_parsing_dir / f"{Path(file_path).stem}_{timestamp}_upstage.json"
        
        # Use async file writing
        await async_json_dump(result, response_file, ensure_ascii=False, indent=2)
        
        if ctx:
            await ctx.report_progress(100, 100)
            ctx.info(f"Document processed and saved to {response_file}")
            
        return response_file
    except Exception as e:
        if ctx:
            ctx.warn(f"Could not save response: {str(e)}")
        return None


async def parse_and_save_document(
    file_path: str,
    api_key: str,
    ctx=None,
    output_formats: List[str] = None
) -> str:
    """
    Parse a document and save the results to disk.
    
    This is a complete function that performs parsing and saving in one operation.
    
    Args:
        file_path: Path to the document file to be processed
        api_key: Upstage API key
        ctx: Optional MCP context for progress reporting
        output_formats: List of output formats (default: None)
        
    Returns:
        Formatted response text
    """
    try:
        # Process document
        result = await parse_document_api(file_path, api_key, ctx, output_formats)
        
        # Extract content
        content = result.get("content", {})
        response_text = json.dumps(content)
        
        # Save results
        response_file = await save_document_parsing_result(result, file_path, ctx)
        
        # Add file path info to response if save succeeded
        if response_file:
            response_text += f"\n\nThe full response has been saved to {response_file} for your reference."
        else:
            response_text += "\n\nNote: Could not save the full response to disk."
            
        return response_text
        
    except httpx.HTTPStatusError as e:
        return f"HTTP error from Upstage API: {e.response.status_code} - {e.response.text}"
    except httpx.RequestError as e:
        return f"Request error connecting to Upstage API: {e}"
    except Exception as e:
        return f"Error: {str(e)}"