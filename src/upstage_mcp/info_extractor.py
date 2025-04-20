"""Information extraction functionality for Upstage AI services."""

import os
import json
import base64
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Set, List

import aiofiles
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# API Endpoints
INFORMATION_EXTRACTION_URL = "https://api.upstage.ai/v1/information-extraction"
SCHEMA_GENERATION_URL = "https://api.upstage.ai/v1/information-extraction/schema-generation"
REQUEST_TIMEOUT = 300  # 5 minutes

# Supported file formats for Information Extraction
SUPPORTED_EXTRACTION_FORMATS: Set[str] = {
    ".jpeg", ".jpg", ".png", ".bmp", ".pdf", ".tiff", ".tif", 
    ".heic", ".docx", ".pptx", ".xlsx"
}

# Setup output directories
def setup_output_directories() -> tuple:
    """Set up output directories for information extraction results."""
    output_dir = Path.home() / ".upstage-mcp-server" / "outputs"
    info_extraction_dir = output_dir / "information_extraction"
    schemas_dir = info_extraction_dir / "schemas"
    
    os.makedirs(info_extraction_dir, exist_ok=True)
    os.makedirs(schemas_dir, exist_ok=True)
    
    return output_dir, info_extraction_dir, schemas_dir


async def async_json_dump(data, filepath, **kwargs):
    """Save JSON data asynchronously to avoid blocking the event loop."""
    async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, **kwargs))


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.RequestError))
)
async def make_api_request(client: httpx.AsyncClient, url: str, headers: dict, json_data: Dict) -> dict:
    """Make an API request with retry logic."""
    response = await client.post(url, headers=headers, json=json_data)
    response.raise_for_status()
    return response.json()


# Utility functions
def encode_file_to_base64(file_path: str) -> str:
    """Encode a file to base64 string."""
    with open(file_path, "rb") as file:
        return base64.b64encode(file.read()).decode("utf-8")


def validate_file_for_extraction(file_path: str) -> Optional[str]:
    """
    Validate that a file is suitable for information extraction.
    
    Returns an error message if validation fails, None otherwise.
    """
    if not os.path.exists(file_path):
        return f"File not found at {file_path}"
        
    # Check file extension
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext not in SUPPORTED_EXTRACTION_FORMATS:
        return f"Unsupported file format: {file_ext}. Supported formats are: {', '.join(SUPPORTED_EXTRACTION_FORMATS)}"
        
    # Check file size (50MB limit)
    file_size = os.path.getsize(file_path)
    if file_size > 50 * 1024 * 1024:  # 50MB in bytes
        return f"File exceeds maximum size of 50MB. Current size: {file_size / (1024 * 1024):.2f}MB"
        
    return None


async def load_schema_async(schema_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Load a schema from a JSON file asynchronously."""
    if not schema_path:
        return None
        
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Schema file not found: {schema_path}")
    
    async with aiofiles.open(schema_path, 'r', encoding='utf-8') as f:
        content = await f.read()
        return json.loads(content)


def get_mime_type(file_path: str) -> str:
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


async def generate_schema(
    file_base64: str, 
    mime_type: str, 
    api_key: str,
    ctx=None
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
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(REQUEST_TIMEOUT)) as client:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
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
            client,
            SCHEMA_GENERATION_URL,
            headers=headers,
            json_data=request_data
        )
        
        # Extract schema from response
        if "choices" not in result or len(result["choices"]) == 0:
            raise ValueError("Invalid response from schema generation API")
            
        content = result["choices"][0]["message"]["content"]
        schema = json.loads(content)
        
        if "json_schema" not in schema:
            raise ValueError("Invalid schema format returned")
            
        return schema["json_schema"]


async def extract_with_schema(
    file_base64: str, 
    mime_type: str, 
    schema: Dict[str, Any], 
    api_key: str,
    ctx=None
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
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(REQUEST_TIMEOUT)) as client:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
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
            client,
            INFORMATION_EXTRACTION_URL,
            headers=headers,
            json_data=request_data
        )
        
        # Extract content from response
        if "choices" not in result or len(result["choices"]) == 0:
            raise ValueError("Invalid response from information extraction API")
            
        content = result["choices"][0]["message"]["content"]
        return json.loads(content)


async def extract_information_from_file(
    file_path: str,
    api_key: str,
    ctx=None,
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
    # Setup output directories
    _, info_extraction_dir, schemas_dir = setup_output_directories()
    
    # Validate file for extraction
    validation_error = validate_file_for_extraction(file_path)
    if validation_error:
        if ctx:
            ctx.error(validation_error)
        return f"Error: {validation_error}"
    
    try:
        if ctx:
            ctx.info(f"Starting to process {file_path}")
            await ctx.report_progress(5, 100)
        
        # Get file MIME type
        mime_type = get_mime_type(file_path)
        
        # Encode file to base64
        if ctx:
            ctx.info("Encoding file")
        file_base64 = encode_file_to_base64(file_path)
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
                schema = await load_schema_async(schema_path)
                if not schema:
                    return f"Error: Could not load schema from {schema_path}"
            except Exception as e:
                return f"Error loading schema: {str(e)}"
        elif auto_generate_schema:
            if ctx:
                ctx.info("Auto-generating schema from document")
            try:
                # Generate schema
                schema = await generate_schema(file_base64, mime_type, api_key, ctx)
                
                # Save generated schema for future use
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                schema_file = schemas_dir / f"{Path(file_path).stem}_{timestamp}_schema.json"
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
            result = await extract_with_schema(file_base64, mime_type, schema, api_key, ctx)
            
            # Save results with timestamp to prevent overwriting
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_file = info_extraction_dir / f"{Path(file_path).stem}_{timestamp}_extraction.json"
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