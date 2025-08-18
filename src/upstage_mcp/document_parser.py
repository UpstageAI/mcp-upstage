"""Document parsing functionality for Upstage AI services."""

import os
import json
from datetime import datetime
import httpx
from pathlib import Path
from typing import Optional, Dict, Any, List
from mcp.server.fastmcp import Context

from .utils import (
    make_api_request,
    async_json_dump,
    validate_file_exists,
)

# Document Parsing Configuration
DOCUMENT_DIGITIZATION_URL = "https://api.upstage.ai/v1/document-digitization"

# Output directory
DOCUMENT_PARSING_DIR = Path.home() / ".mcp-upstage" / "outputs" / "document_parsing"
os.makedirs(DOCUMENT_PARSING_DIR, exist_ok=True)


async def _parse_document_api(
    file_path: str,
    api_key: str,
    ctx: Optional[Context] = None,
    output_formats: Optional[List[str]] = None
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
    validate_file_exists(file_path)
    
    # Initialize progress reporting if context provided
    if ctx:
        ctx.info(f"Starting to process {file_path}")
        await ctx.report_progress(10, 100)
    
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
            DOCUMENT_DIGITIZATION_URL,
            api_key=api_key,
            ctx=ctx,
            operation="document parsing",
            files=files,
            data=data
        )
    
    if ctx:
        await ctx.report_progress(80, 100)
        
    return result


async def _save_document_parsing_result(
    result: Dict[str, Any], 
    file_path: str, 
    ctx: Optional[Context] = None
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
    try:
        # Add timestamp to prevent overwriting
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        response_file = DOCUMENT_PARSING_DIR / f"{Path(file_path).stem}_{timestamp}_upstage.json"
        
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
    ctx: Optional[Context] = None,
    output_formats: Optional[List[str]] = None
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
    # Process document
    result = await _parse_document_api(file_path, api_key, ctx, output_formats)
    
    # Extract content
    content = result.get("content", {})
    response_text = json.dumps(content)
    
    # Save results
    response_file = await _save_document_parsing_result(result, file_path, ctx)
    
    # Add file path info to response if save succeeded
    if response_file:
        response_text += f"\n\nThe full response has been saved to {response_file} for your reference."
    else:
        response_text += "\n\nNote: Could not save the full response to disk."
        
    return response_text