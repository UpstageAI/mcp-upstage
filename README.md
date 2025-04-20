
# Upstage MCP Server

> A Model Context Protocol (MCP) server for Upstage AI's document digitization and information extraction capabilities

## Overview

The Upstage MCP Server provides a robust bridge between AI assistants and Upstage AI’s powerful document processing APIs. This server enables AI models—such as Claude—to effortlessly extract and structure content from various document types including PDFs, images, and Office files. The package supports multiple formats and comes with seamless integration options for Claude Desktop.

## Key Features

- **Document Digitization:** Extract structured content from documents while preserving layout.
- **Information Extraction:** Retrieve specific data points using intelligent, customizable schemas.
- **Multi-format Support:** Handles JPEG, PNG, BMP, PDF, TIFF, HEIC, DOCX, PPTX, and XLSX.
- **Claude Desktop Integration:** Effortlessly connect with Claude and other MCP clients.

## Prerequisites

Before using this server, ensure you have the following:

1. **Upstage API Key:** Obtain your API key from [Upstage API](https://console.upstage.ai/api-keys?api=document-parsing).
2. **Python 3.10+:** The server requires Python version 3.10 or higher.
3. The MCP server relies upon **Astral UV** to run, please [install](https://docs.astral.sh/uv/getting-started/installation/)

## Installation & Configuration

This guide provides step-by-step instructions to set up and configure the mcp-server-upstage

### Using `uv` (Recommended)

No additional installation is required when using `uvx` as it handles execution. However, if you prefer to install the package directly:
```bash
uv pip install mcp-server-upstage
```

## Configure Claude Desktop
For integration with Claude Desktop, add the following content to your `claude_desktop_config.json`:

### Configuration Location

- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

### Using uvx Command (Recommended)


```json
{
  "mcpServers": {
    "mcp-server-upstage": {
      "command": "uvx",
      "args": ["mcp-server-upstage"],
      "env": {
        "UPSTAGE_API_KEY": "<your-api-key>"
      }
    }
  }
}
```

If `uvx` is not available globally, you may encounter a `Server disconnected` error. To resolve this, run `which uvx` to find its full path, and replace `"command": "uvx"` above with the returned path.

### After adding the configuration, restart Claude Desktop to apply the changes.

## Output Directories

Processing results are stored in your home directory under:

- **Document Parsing Results:**  
  `~/.mcp-server-upstage/outputs/document_parsing/`
- **Information Extraction Results:**  
  `~/.mcp-server-upstage/outputs/information_extraction/`
- **Generated Schemas:**  
  `~/.mcp-server-upstage/outputs/information_extraction/schemas/`

## Local/Development Setup

Follow these steps to set up and run the project locally:

### Step 1: Clone the Repository

```bash
git clone https://github.com/UpstageAI/mcp-server-upstage.git
cd mcp-server-upstage
```

### Step 2: Set Up the Python Environment

```bash
# Install uv if not already installed
pip install uv

# Create and activate a virtual environment
uv venv

# Activate the virtual environment
# On Windows:
# .venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies in editable mode
uv pip install -e .
```

### Step 3: Configure Claude Desktop for Local Testing

1. **Download Claude Desktop:**  
   [Download Claude Desktop](https://claude.ai/download)

2. **Open and Edit Configuration:**
   - Navigate to **Claude → Settings → Developer → Edit Config**.
   - Edit the `claude_desktop_config.json` file with the following configurations:

   **For Windows:**
   ```json
   {
     "mcpServers": {
       "mcp-server-upstage": {
         "command": "uv",
         "args": [
           "run",
           "--directory",
           "C:\\path\\to\\cloned\\mcp-server-upstage",
           "python",
           "-m",
           "upstage_mcp.server"
         ],
         "env": {
           "UPSTAGE_API_KEY": "your_api_key_here"
         }
       }
     }
   }
   ```
   Replace `C:\\path\\to\\cloned\\mcp-server-upstage` with your actual repository path.

   **For macOS/Linux:**
   ```json
   {
     "mcpServers": {
       "mcp-server-upstage": {
         "command": "/Users/username/.local/bin/uv",
         "args": [
           "run",
           "--directory",
           "/path/to/cloned/mcp-server-upstage",
           "python",
           "-m",
           "upstage_mcp.server"
         ],
         "env": {
           "UPSTAGE_API_KEY": "your_api_key_here"
         }
       }
     }
   }
   ```
   Replace:
   - `/Users/username/.local/bin/uv` with the output of `which uv`.
   - `/path/to/cloned/mcp-server-upstage` with the absolute path to your local clone.

> **Tip for macOS/Linux users:** If connection issues occur, using the full path to your uv executable can improve reliability.

After configuring, restart Claude Desktop.

## Available Tools

The server exposes two primary tools for AI models:

1. **Document Parsing (`parse_document`):**
   - **Description:** Processes documents and extracts content while preserving structure.
   - **Parameter:**  
     `file_path` – the path to the document to be processed.
   - **Example Query:**  
     *"Can you parse the document at `C:\Users\username\Documents\contract.pdf` and provide a summary?"*

2. **Information Extraction (`extract_information`):**
   - **Description:** Extracts structured information from documents based on predefined or auto-generated schemas.
   - **Parameters:**  
     `file_path` – the document file path;  
     `schema_path` (optional) – a JSON file with an extraction schema;  
     `auto_generate_schema` (default true) – whether to auto-generate a schema.
   - **Example Query:**  
     *"Extract the invoice number, date, and total from `C:\Users\username\Documents\invoice.pdf`."*

Below is the revised troubleshooting section formatted as requested. You can copy and paste the following Markdown directly into your README:


## Troubleshooting

### Common Issues

- **API Key Missing:**  
  Ensure that your UPSTAGE_API_KEY is correctly set in your `claude_desktop_config.json` file. Obtain a valid API key from [Upstage Console](https://console.upstage.ai/api-keys).

- **File Not Found:**  
  Double-check the file path for correctness and accessibility. Ensure that file paths are absolute (e.g., `C:\Users\name\Documents\file.pdf`) and that any special characters in the path are properly escaped.

- **Server Not Starting:**  
  Verify that your virtual environment is activated and all dependencies are installed. Additionally, review the Claude Desktop log files for errors:  
  - **Windows:** `%APPDATA%\Claude\logs\mcp-server-mcp-server-upstage.log`  
  - **macOS:** `~/Library/Logs/Claude/mcp-server-mcp-server-upstage.log`

- **Server Connection Issues:**  
  Restart Claude Desktop. Ensure that `uvx` is installed and available in your system PATH, or use its absolute path in your configuration if needed.

- **Processing Failures:**  
  Check that the document is in a supported format (PDF, JPEG, PNG, TIFF, etc.), its file size is under 50MB, and it contains fewer than 100 pages. Test with a simpler document to confirm functionality.

- **Invalid Document Format:**  
  Verify that the document is in a supported, uncorrupted format.

- **Failed to Connect to Upstage API:**  
  Confirm your network connection, firewall settings, and configuration details in `claude_desktop_config.json`. Review the logs for more detailed error messages.

### Log Files

For troubleshooting, view the server logs at:

- **Windows:**  
  `%APPDATA%\Claude\logs\mcp-server-mcp-server-upstage.log`
- **macOS:**  
  `~/Library/Logs/Claude/mcp-server-mcp-server-upstage.log`

## Contributing

Contributions are welcome! If you wish to enhance the project or add new features, please fork the repository and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License.

