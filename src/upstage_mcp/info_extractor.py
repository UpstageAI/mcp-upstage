"""Information extraction functionality for Upstage AI services."""

import os
import json
import base64
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List
from mcp.server.fastmcp import Context

import httpx

from .utils import (
    make_api_request,
    async_json_dump,
    async_json_load,
    MB,
    validate_file_exists,
    validate_file_size,
    validate_file_extension,
)

# Information Extraction Configuration
INFORMATION_EXTRACTION_URL = "https://api.upstage.ai/v1/information-extraction"
SCHEMA_GENERATION_URL = "https://api.upstage.ai/v1/information-extraction/schema-generation"

# Supported file formats for Information Extraction
SUPPORTED_EXTRACTION_FORMATS = {
    ".jpeg", ".jpg", ".png", ".bmp", ".pdf", ".tiff", ".tif", 
    ".heic", ".docx", ".pptx", ".xlsx"
}

# File size limits for Information Extraction
MAX_FILE_SIZE_BYTES = 50 * MB
MAX_PAGES = 100

# Output directories
INFO_EXTRACTION_DIR = Path.home() / ".mcp-upstage" / "outputs" / "information_extraction"
SCHEMAS_DIR = INFO_EXTRACTION_DIR / "schemas"
os.makedirs(INFO_EXTRACTION_DIR, exist_ok=True)
os.makedirs(SCHEMAS_DIR, exist_ok=True)


# Utility functions
def _encode_file_to_base64(file_path: str) -> str:
    """Encode a file to base64 string."""
    with open(file_path, "rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")


def _validate_file_for_extraction(file_path: str) -> None:
    """
    Validate that a file is suitable for information extraction.
    
    Raises:
        FileNotFoundError: If the file does not exist
        ValueError: If the file format is not supported or file size exceeds limit
    """
    validate_file_exists(file_path)
    validate_file_extension(file_path, SUPPORTED_EXTRACTION_FORMATS)
    validate_file_size(file_path, MAX_FILE_SIZE_BYTES)


async def _load_schema_async(schema_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Load a schema from a JSON file asynchronously."""
    if not schema_path:
        return None
        
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    
    return await async_json_load(schema_path)


def _get_mime_type(file_path: str) -> str:
    """Get MIME type for a file with fallbacks for common extensions."""
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        # Default to generic type based on extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.heic']:
            mime_type = 'image/png'  # Default for images
        elif ext == '.pdf':
            mime_type = 'application/pdf'
        elif ext == '.docx':
            mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif ext == '.xlsx':
            mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif ext == '.pptx':
            mime_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        else:
            mime_type = 'application/octet-stream'  # Generic fallback
    return mime_type


async def _generate_schema(
    file_base64: str, 
    mime_type: str, 
    api_key: str,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Generate a schema using the Schema Generation API.
    
    Args:
        file_base64: Base64 encoded file content
        mime_type: MIME type of the file
        api_key: Upstage API key
        ctx: Optional MCP Context for progress reporting
    
    Returns:
        Generated schema for information extraction
    """
    if ctx:
        ctx.info("Connecting to schema generation API")
    
    # Prepare request data in OpenAI format
    request_data = {
        "model": "information-extract",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{file_base64}"
                        }
                    }
                ]
            }
        ]
    }
    
    # Make request with retry
    result = await make_api_request(
        SCHEMA_GENERATION_URL,
        headers={"Content-Type": "application/json"},
        api_key=api_key,
        ctx=ctx,
        operation="schema generation",
        json=request_data
    )
    
    # Extract schema from response
    if "choices" not in result or len(result["choices"]) == 0:
        raise ValueError("Invalid response from schema generation API")
        
    content = result["choices"][0]["message"]["content"]
    schema = json.loads(content)
    
    if "json_schema" not in schema:
        raise ValueError("Invalid schema format returned")
        
    return schema["json_schema"]


async def _extract_with_schema(
    file_base64: str, 
    mime_type: str, 
    schema: Dict[str, Any], 
    api_key: str,
    ctx: Optional[Context] = None
) -> Dict[str, Any]:
    """
    Extract information using the Information Extraction API.
    
    Args:
        file_base64: Base64 encoded file content
        mime_type: MIME type of the file
        schema: JSON schema defining what to extract
        api_key: Upstage API key
        ctx: Optional MCP Context for progress reporting
    
    Returns:
        Extracted information as a dictionary
    """
    if ctx:
        ctx.info("Connecting to information extraction API")
    
    # Prepare request data in OpenAI format
    request_data = {
        "model": "information-extract",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{file_base64}"
                        }
                    }
                ]
            }
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": schema
        }
    }
    
    # Make request with retry
    result = await make_api_request(
        INFORMATION_EXTRACTION_URL,
        headers={"Content-Type": "application/json"},
        api_key=api_key,
        ctx=ctx,
        operation="information extraction",
        json=request_data
    )
    
    # Extract content from response
    if "choices" not in result or len(result["choices"]) == 0:
        raise ValueError("Invalid response from information extraction API")
        
    content = result["choices"][0]["message"]["content"]
    return json.loads(content)


async def extract_information_from_file(
    file_path: str,
    api_key: str,
    ctx: Optional[Context] = None,
    schema_path: Optional[str] = None,
    schema_json: Optional[str] = None,
    auto_generate_schema: bool = True
) -> str:
    """
    Extract structured information from a document.
    
    This is a complete function that performs extraction and saving in one operation.
    
    Args:
        file_path: Path to the document file to process
        api_key: Upstage API key
        ctx: Optional MCP Context for progress reporting
        schema_path: Optional path to a JSON file containing the extraction schema
        schema_json: Optional JSON string containing the extraction schema
        auto_generate_schema: Whether to automatically generate a schema
        
    Returns:
        Extracted information as a JSON string
    """
    # Output directories are already set up at module level
    
    # Validate file for extraction
    try:
        _validate_file_for_extraction(file_path)
    except (FileNotFoundError, ValueError) as e:
        if ctx:
            ctx.error(str(e))
        return f"Error: {str(e)}"
    
    try:
        if ctx:
            ctx.info(f"Starting to process {file_path}")
            await ctx.report_progress(5, 100)
        
        # Get file MIME type
        mime_type = _get_mime_type(file_path)
        
        # Encode file to base64
        if ctx:
            ctx.info("Encoding file")
        file_base64 = _encode_file_to_base64(file_path)
        if ctx:
            await ctx.report_progress(15, 100)
        
        # Determine schema
        schema = None
        schema_file = None
        
        # Priority: 1. schema_json (direct JSON), 2. schema_path (file), 3. auto-generate
        if schema_json:
            try:
                schema = json.loads(schema_json)
            except json.JSONDecodeError:
                return f"Error: Invalid JSON in schema_json"
        elif schema_path:
            if ctx:
                ctx.info(f"Loading schema from {schema_path}")
            try:
                schema = await _load_schema_async(schema_path)
                if not schema:
                    return f"Error: Could not load schema from {schema_path}"
            except Exception as e:
                return f"Error loading schema: {str(e)}"
        elif auto_generate_schema:
            if ctx:
                ctx.info("Auto-generating schema from document")
            try:
                # Generate schema
                schema = await _generate_schema(file_base64, mime_type, api_key, ctx)
                
                # Save generated schema for future use
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                schema_file = SCHEMAS_DIR / f"{Path(file_path).stem}_{timestamp}_schema.json"
                await async_json_dump(schema, schema_file, indent=2)
                
                if ctx:
                    ctx.info(f"Generated schema saved to {schema_file}")
            except Exception as e:
                return f"Error generating schema: {str(e)}"
        
        # If we don't have a schema at this point, return an error
        if not schema:
            return "Error: No schema provided or generated. Please provide a schema or enable auto_generate_schema."
        
        if ctx:
            await ctx.report_progress(50, 100)
            ctx.info("Extracting information with schema")
        
        # Extract information using schema
        try:
            result = await _extract_with_schema(file_base64, mime_type, schema, api_key, ctx)
            
            # Save results with timestamp to prevent overwriting
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_file = INFO_EXTRACTION_DIR / f"{Path(file_path).stem}_{timestamp}_extraction.json"
            await async_json_dump(result, result_file, indent=2)
            
            if ctx:
                await ctx.report_progress(100, 100)
                ctx.info(f"Extraction complete. Results saved to {result_file}")
            
            # Return results with metadata
            response = {
                "extracted_data": result,
                "metadata": {
                    "file": os.path.basename(file_path),
                    "result_saved_to": str(result_file),
                    "schema_used": str(schema_file) if schema_file else schema_path
                }
            }
            
            return json.dumps(response, indent=2)
        except Exception as e:
            return f"Error extracting information: {str(e)}"
            
    except Exception as e:
        error_msg = f"Error extracting information: {str(e)}"
        if ctx:
            ctx.error(error_msg)
        return error_msg