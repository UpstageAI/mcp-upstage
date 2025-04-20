# OpenAI Integration with Upstage MCP Server

This example demonstrates how to use OpenAI's Agents SDK to connect with the Upstage MCP Server for document processing tasks.

## Prerequisites

- Python 3.10+
- Upstage API Key
- OpenAI API Key
- The following Python packages:
  - `upstage-mcp-server`
  - `openai`
  - `openai-agents`
  - `uvx`

## Setup

1. Install the required packages:
   ```
   uv pip install upstage-mcp-server openai openai-agents uvx
   ```

2. Set up your environment variables:
   ```
   export UPSTAGE_API_KEY="your-upstage-api-key"
   export OPENAI_API_KEY="your-openai-api-key"
   ```
   
   Alternatively, the script will prompt for these if not found.

## Running the Example

Execute the script with:

```
python openai_main.py
```

The script will:

1. Connect to the Upstage MCP Server
2. Ask you for a document path to analyze
3. Create an OpenAI Agent that can use the document processing tools
4. Perform three tasks:
   - Parse the document to extract its contents
   - Extract specific information from the document
   - Run a custom analysis based on your query

## How It Works

This example uses the `MCPServerStdio` class from OpenAI's Agents SDK to connect to the Upstage MCP Server. The server provides two main tools:

- `parse_document`: Extracts the full content of a document
- `extract_information`: Extracts specific structured information from documents

The Agent is configured to use these tools to analyze the document you provide.

## Example Usage

Here's an example interaction:

```
Enter the path to a document to analyze: /path/to/invoice.pdf
Connecting to Upstage MCP Server...
Available tools: ['parse_document', 'extract_information']

------------------------------------------------------------
Task 1: Parsing the document
I've parsed the document and here's a summary of its contents:

This is an invoice from Acme Corporation dated January 15, 2023...

------------------------------------------------------------
Task 2: Extracting specific information
I've extracted the following information from the invoice:
- Invoice Number: INV-2023-0042
- Date: January 15, 2023
- Total Amount: $1,250.00
- Vendor: Acme Corporation

------------------------------------------------------------
Task 3: Custom analysis
Enter your own query about the document: Who are the parties involved in this transaction?
The parties involved in this transaction are:
- Vendor: Acme Corporation
- Client: XYZ Enterprises
```

## Troubleshooting

- **Server Connection Issues**: Ensure `uvx` is correctly installed and in your PATH.
- **API Key Errors**: Verify your API keys are correctly set and valid.
- **File Not Found**: Check that the document path is correct and accessible.
- **Unsupported Document Format**: Ensure you're using a supported format (PDF, JPEG, PNG, TIFF, Office files).