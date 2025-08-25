"""Validation utilities for Upstage MCP server."""

import os
from typing import Optional

from upstage_mcp.utils import MB


def validate_file_exists(file_path: str) -> None:
    """
    Validate that a file exists at the given path.
    
    Args:
        file_path: Path to the file to validate
        
    Raises:
        FileNotFoundError: If the file does not exist
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at {file_path}")


def validate_file_size(file_path: str, max_size_bytes: int) -> None:
    """
    Validate that a file does not exceed the maximum size.
    
    Args:
        file_path: Path to the file to validate
        max_size_bytes: Maximum file size in bytes
        
    Raises:
        ValueError: If the file exceeds the maximum size
    """
    file_size = os.path.getsize(file_path)
    if file_size > max_size_bytes:
        max_size_mb = max_size_bytes / MB
        current_size_mb = file_size / MB
        raise ValueError(f"File exceeds maximum size of {max_size_mb:.0f}MB. Current size: {current_size_mb:.2f}MB")


def validate_file_extension(file_path: str, supported_extensions: set[str]) -> None:
    """
    Validate that a file has a supported extension.
    
    Args:
        file_path: Path to the file to validate
        supported_extensions: Set of supported file extensions (e.g., {'.pdf', '.jpg'})
        
    Raises:
        ValueError: If the file extension is not supported
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext not in supported_extensions:
        raise ValueError(f"Unsupported file format: {file_ext}. Supported formats are: {', '.join(supported_extensions)}")
