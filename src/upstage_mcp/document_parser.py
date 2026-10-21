"""Document parsing functionality for Upstage AI services."""

import os
import json
from datetime import datetime
import httpx
from pathlib import Path
from typing import Optional, Dict, Any, List, Literal
from mcp.server.fastmcp import Context

from .utils import (
    make_api_request,
    async_json_dump,
    validate_file_exists,
)

# Document Parsing Configuration
DOCUMENT_DIGITIZATION_URL = "https://api.upstage.ai/v1/document-digitization"

# Parsing options
ParseMode = Literal["standard", "enhanced", "auto"]
OcrMode = Literal["auto", "force"]
DEFAULT_MODE = "standard"
DEFAULT_OCR = "force"
DEFAULT_MODEL = "document-parse"
# Per-page processing modes reported as keys of the response `usage` field
USAGE_MODE_KEYS = ("standard", "enhanced")

# Output directory
DOCUMENT_PARSING_DIR = Path.home() / ".mcp-upstage" / "outputs" / "document_parsing"
os.makedirs(DOCUMENT_PARSING_DIR, exist_ok=True)


async def _parse_document_api(
    file_path: str,
    api_key: str,
    ctx: Optional[Context] = None,
    output_formats: Optional[List[str]] = None,
    mode: ParseMode = DEFAULT_MODE,
    ocr: OcrMode = DEFAULT_OCR,
    model: str = DEFAULT_MODEL
) -> Dict[str, Any]:
    """
    Parse a document using Upstage AI's document digitization API.
    
    Args:
        file_path: Path to the document file to be processed
        api_key: Upstage API key
        ctx: Optional MCP context for progress reporting
        output_formats: List of output formats (default: None)
        mode: Parsing mode ("standard", "enhanced" or "auto")
        ocr: OCR mode ("auto" or "force")
        model: Model name or pinned version (e.g. "document-parse-260930")
        
    Returns:
        API response as a dict
    """
    validate_file_exists(file_path)
    
    # Initialize progress reporting if context provided
    if ctx:
        await ctx.info(f"Starting to process {file_path} (mode={mode}, ocr={ocr}, model={model})")
        await ctx.report_progress(30, 100)
    
    # Process document
    with open(file_path, "rb") as file:
        files = {"document": file}
        data = {
            "ocr": ocr,
            "base64_encoding": "['table']",
            "model": model
        }
        
        # The API defaults to standard; only send mode when it differs so that
        # older models or gateways that do not accept the field keep working.
        if mode != DEFAULT_MODE:
            data["mode"] = mode
        
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
            await ctx.info(f"Document processed and saved to {response_file}")
            
        return response_file
    except Exception as e:
        if ctx:
            await ctx.warning(f"Could not save response: {str(e)}")
        return None


def _format_processing_info(result: Dict[str, Any], requested_mode: str) -> str:
    """
    Describe how the API actually processed the document.
    
    Reports the model and usage returned by the API, and warns when the
    requested mode (standard or enhanced) is not reflected in the usage.
    If the usage has no per-mode keys, a note is added for enhanced only.
    
    Args:
        result: The API response
        requested_mode: The mode sent in the request
        
    Returns:
        One or two lines of text to append to the tool response
    """
    model = result.get("model") or "unknown model"
    usage = result.get("usage")
    usage_text = json.dumps(usage, ensure_ascii=False) if usage is not None else "not reported"
    info = f"Processed by {model} | usage: {usage_text}"

    if requested_mode == "auto":
        return info

    applied_modes = (
        [key for key in USAGE_MODE_KEYS if usage.get(key)] if isinstance(usage, dict) else []
    )

    # No per-mode breakdown (e.g. older pinned models): the applied mode cannot be confirmed.
    if not applied_modes:
        if requested_mode == DEFAULT_MODE:
            return info
        return info + (
            f"\nNote: Could not confirm mode '{requested_mode}' was applied "
            "because the API response has no per-mode usage."
        )

    other_modes = [key for key in applied_modes if key != requested_mode]
    if requested_mode not in applied_modes or other_modes:
        return info + (
            f"\nWARNING: Requested mode '{requested_mode}' was not applied as requested "
            f"(applied: {', '.join(applied_modes)}). Check the usage above."
        )

    return info


async def parse_and_save_document(
    file_path: str,
    api_key: str,
    ctx: Optional[Context] = None,
    output_formats: Optional[List[str]] = None,
    mode: ParseMode = DEFAULT_MODE,
    ocr: OcrMode = DEFAULT_OCR,
    model: str = DEFAULT_MODEL
) -> str:
    """
    Parse a document and save the results to disk.
    
    This is a complete function that performs parsing and saving in one operation.
    
    Args:
        file_path: Path to the document file to be processed
        api_key: Upstage API key
        ctx: Optional MCP context for progress reporting
        output_formats: List of output formats (default: None)
        mode: Parsing mode ("standard", "enhanced" or "auto")
        ocr: OCR mode ("auto" or "force")
        model: Model name or pinned version (e.g. "document-parse-260930")
        
    Returns:
        Formatted response text, followed by the model and usage reported by the API
    """
    # Process document
    result = await _parse_document_api(
        file_path, api_key, ctx, output_formats, mode=mode, ocr=ocr, model=model
    )
    
    # Extract content
    content = result.get("content", {})
    response_text = json.dumps(content, ensure_ascii=False)
    
    # Report how the document was actually processed
    response_text += "\n\n" + _format_processing_info(result, mode)
    
    # Save results
    response_file = await _save_document_parsing_result(result, file_path, ctx)
    
    # Add file path info to response if save succeeded
    if response_file:
        return response_text + f"\n\nThe full response has been saved to {response_file} for your reference."

    return response_text + "\n\nNote: Could not save the full response to disk."