# LangChain Integration with Upstage MCP Server

This example demonstrates how to integrate Upstage MCP Server with LangChain for document processing and information extraction. It uses Upstage's Solar LLM model instead of OpenAI.

## Prerequisites

- Python 3.10+
- Upstage API Key (for both the MCP Server and Solar model)
- The following Python packages:
  - `upstage-mcp-server`
  - `langchain-mcp-adapters`
  - `langchain-upstage`
  - `langchain`
  - `uvx`

## Setup

1. Install the required packages:
   ```
   uv pip install upstage-mcp-server langchain-mcp-adapters langchain-upstage langchain uvx
   ```

2. Set up your environment variable:
   ```
   export UPSTAGE_API_KEY="your-upstage-api-key"
   ```
   
   Alternatively, the script will prompt for the API key if not found.

## Running the Example

Execute the script with:

```
python langchain_main.py
```

The script will:

1. Connect to the Upstage MCP Server
2. Ask you for a document path to analyze
3. Create a LangChain agent using Upstage's Solar model that can use the document processing tools
4. Perform three tasks:
   - Parse the document to extract its contents
   - Extract specific information from the document
   - Run a custom analysis based on your query

## How It Works

This example uses:
- `langchain-mcp-adapters` to connect to the Upstage MCP Server
- `langchain-upstage` to use Upstage's Solar model as the LLM
- `ChatUpstage` class to initialize the Upstage model

The connection is established using the `stdio_client` from the MCP SDK, and the tools are loaded into LangChain's format using `load_mcp_tools`.

The MCP server provides two main tools:

- `parse_document`: Extracts the full content of a document
- `extract_information`: Extracts specific structured information from documents

A LangChain ReAct agent is created to use these tools for document analysis.

## Solar LLM Usage

Here's how to initialize and use the Solar LLM in this example:

```python
from langchain_upstage import ChatUpstage

model = ChatUpstage(
    model_name="solar-pro",  
    temperature=0
)
```

## Example Usage

Here's an example interaction:

```
Enter the path to a document to analyze: /path/to/invoice.pdf
Connecting to Upstage MCP Server...
Available tools: ['parse_document', 'extract_information']

------------------------------------------------------------
Task 1: Parsing the document
I need to parse the document to extract its contents.

Action: parse_document
Action Input: {"file_path": "/path/to/invoice.pdf"}
Observation: Document parsed successfully. It contains an invoice from...

Thought: I'll now provide a summary of the document.

Final Result:
This is an invoice from Acme Corporation dated January 15, 2023...

------------------------------------------------------------
Task 2: Extracting specific information
I need to extract specific information from this invoice.

Action: extract_information
Action Input: {"file_path": "/path/to/invoice.pdf", "auto_generate_schema": true}
Observation: Successfully extracted...

Final Result:
I've extracted the following information from the invoice:
- Invoice Number: INV-2023-0042
- Date: January 15, 2023
- Total Amount: $1,250.00
- Vendor: Acme Corporation

------------------------------------------------------------
Task 3: Custom analysis
Enter your own query about the document: Who are the parties involved in this transaction?

Thought: I need to extract information about the parties involved.

Action: extract_information
Action Input: {"file_path": "/path/to/invoice.pdf", "schema_json": "..."}
Observation: ...

Final Result:
The parties involved in this transaction are:
- Vendor: Acme Corporation
- Client: XYZ Enterprises
```

## Troubleshooting

- **Server Connection Issues**: Ensure `uvx` is correctly installed and in your PATH.
- **API Key Errors**: Verify your Upstage API key is correctly set and valid.
- **File Not Found**: Check that the document path is correct and accessible.
- **Unsupported Document Format**: Ensure you're using a supported format (PDF, JPEG, PNG, TIFF, Office files).
