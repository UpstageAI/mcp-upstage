"""File utilities for Upstage MCP server."""

import json
import aiofiles
from typing import Any


async def async_json_dump(data: Any, filepath: str, **kwargs) -> None:
    """
    Save JSON data asynchronously to avoid blocking the event loop.
    
    Args:
        data: Data to serialize to JSON
        filepath: Path to save the JSON file
        **kwargs: Additional arguments for json.dumps
    """
    async with aiofiles.open(filepath, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, **kwargs))


async def async_json_load(filepath: str) -> Any:
    """
    Load JSON data asynchronously to avoid blocking the event loop.
    
    Args:
        filepath: Path to the JSON file to load
        
    Returns:
        Loaded JSON data
    """
    async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
        content = await f.read()
        return json.loads(content)
