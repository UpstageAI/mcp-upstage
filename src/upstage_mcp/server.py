"""MCP server for Upstage AI services."""

import os
from typing import Annotated, Literal, Optional, List
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context
from pydantic import Field

# Import our functionality modules
from upstage_mcp import document_parser, info_extractor

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.environ.get("UPSTAGE_API_KEY")

if not API_KEY:
    raise ValueError("UPSTAGE_API_KEY not set in environment variables")

mcp = FastMCP("mcp-upstage")

# Output directories are created when modules are imported
output_dir = Path.home() / ".mcp-upstage" / "outputs"
print(f"Output directories created at: {output_dir}")

# Document Parsing Tool
@mcp.tool()
async def parse_document(
    file_path: Annotated[str, Field(description="Path to the document file to be processed")],
    output_formats: Annotated[Optional[List[str]], Field(description="Output formats (e.g., 'html', 'text', 'markdown')")] = None,
    mode: Annotated[Literal["standard", "enhanced", "auto"], Field(description=(
        "Parsing mode. 'standard' (default): fast and cheapest, good for ordinary text-centric documents. "
        "'enhanced': use for complex tables, charts, handwriting or low-quality scans; "
        "it costs more per page and is slower. "
        "'auto': let the API decide per page whether enhanced processing is needed."
    ))] = "standard",
    ocr: Annotated[Literal["auto", "force"], Field(description=(
        "OCR mode. 'force' (default): always run OCR. "
        "'auto': use the embedded text of digital documents and run OCR only when needed."
    ))] = "force",
    model: Annotated[str, Field(description=(
        "Document Parse model name. Use the default 'document-parse' for the latest version, "
        "or a dated version such as 'document-parse-260930' to pin it."
    ))] = "document-parse",
    ctx: Context = None
) -> str:
    """Parse a document using Upstage AI's document digitization API.
    
    This tool extracts the structure and content from various document types,
    including PDFs, images, and Office files. It preserves the original formatting
    and layout while converting the document into a structured format.
    
    Use mode='enhanced' for documents with complex tables, charts, handwriting or
    low-quality scans (higher cost, slower), or mode='auto' to let the API decide
    per page. The response ends with the model and per-mode page usage reported
    by the API, plus a WARNING line if the requested mode was not applied.
    
    Supported file formats include: PDF, JPEG, PNG, TIFF, and other common document formats.
    """
    return await document_parser.parse_and_save_document(
        file_path=file_path,
        api_key=API_KEY,
        ctx=ctx,
        output_formats=output_formats,
        mode=mode,
        ocr=ocr,
        model=model
    )


# Information Extraction Tool
@mcp.tool()
async def extract_information(
    file_path: Annotated[str, Field(description="Path to the document file to process")],
    ctx: Context,
    schema_path: Annotated[Optional[str], Field(description="Path to JSON file containing the extraction schema (optional)")] = None,
    schema_json: Annotated[Optional[str], Field(description="JSON string containing the extraction schema (optional)")] = None,
    auto_generate_schema: Annotated[bool, Field(description="Whether to automatically generate a schema")] = True
) -> str:
    """Extract structured information from documents using Upstage Universal Information Extraction.
    
    This tool can extract key information from any document type without pre-training.
    You can either provide a schema defining what information to extract, or let the system
    automatically generate an appropriate schema based on the document content.
    
    Supported file formats: JPEG, PNG, BMP, PDF, TIFF, HEIC, DOCX, PPTX, XLSX
    Max file size: 50MB
    Max pages: 100
    
    Args:
        file_path: Path to the document file to process
        schema_path: Optional path to a JSON file containing the extraction schema
        schema_json: Optional JSON string containing the extraction schema
        auto_generate_schema: Whether to automatically generate a schema if none is provided
    """
    return await info_extractor.extract_information_from_file(
        file_path=file_path,
        api_key=API_KEY,
        ctx=ctx,
        schema_path=schema_path,
        schema_json=schema_json,
        auto_generate_schema=auto_generate_schema
    )


def main():
    """Run the Upstage MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()