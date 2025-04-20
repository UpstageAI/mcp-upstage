# Upstage MCP Server Integration Examples

This directory contains examples demonstrating how to integrate the Upstage MCP Server with popular AI frameworks:

- **[OpenAI Example](./openai_agent/)**: Connect the Upstage MCP Server with OpenAI's Agents SDK for document processing and information extraction.
- **[LangChain Example](./langchain/)**: Integrate the Upstage MCP Server with LangChain's agent framework for document analysis.

## Overview

The Upstage MCP Server provides document digitization and information extraction capabilities through the Model Context Protocol (MCP). These examples show how to leverage these capabilities with different AI frameworks.

## Prerequisites

- Python 3.10+
- Upstage API Key (get from [Upstage Console](https://console.upstage.ai/api-keys))
- OpenAI API Key (for both examples)
- The Upstage MCP Server package (`upstage-mcp-server`)

## Getting Started

1. Install the Upstage MCP Server:
   ```
   uv pip install upstage-mcp-server
   ```

2. Set up your environment variables:
   ```
   export UPSTAGE_API_KEY="your-upstage-api-key"
   export OPENAI_API_KEY="your-openai-api-key"
   ```

3. Choose an example directory and follow the README instructions there to run the example.