
# Upstage MCP

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

This guide provides step-by-step instructions to set up and configure the mcp-upstage

### Using `uv` (Recommended)

No additional installation is required when using `uvx` as it handles execution. However, if you prefer to install the package directly:
```bash
uv pip install mcp-upstage
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
    "mcp-upstage": {
      "command": "uvx",
      "args": ["mcp-upstage"],
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
  `~/.mcp-upstage/outputs/document_parsing/`
- **Information Extraction Results:**  
  `~/.mcp-upstage/outputs/information_extraction/`
- **Generated Schemas:**  
  `~/.mcp-upstage/outputs/information_extraction/schemas/`

## Local/Development Setup

Follow these steps to set up and run the project locally:

### Step 1: Clone the Repository

```bash
git clone https://github.com/UpstageAI/mcp-upstage.git
cd mcp-upstage
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
       "mcp-upstage": {
         "command": "uv",
         "args": [
           "run",
           "--directory",
           "C:\\path\\to\\cloned\\mcp-upstage",
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
   Replace `C:\\path\\to\\cloned\\mcp-upstage` with your actual repository path.

   **For macOS/Linux:**
   ```json
   {
     "mcpServers": {
       "mcp-upstage": {
         "command": "/Users/username/.local/bin/uv",
         "args": [
           "run",
           "--directory",
           "/path/to/cloned/mcp-upstage",
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
   - `/path/to/cloned/mcp-upstage` with the absolute path to your local clone.

> **Tip for macOS/Linux users:** If connection issues occur, using the full path to your uv executable can improve reliability.

After configuring, restart Claude Desktop.

## Available Tools

The server exposes two primary tools for AI models:

1. **Document Parsing (`parse_document`):**
   - **Description:** Processes documents and extracts content while preserving structure.
   - **Parameters:**  
     `file_path` – the path to the document to be processed;  
     `output_formats` (optional) – output formats such as `html`, `text`, `markdown`;  
     `mode` (default `standard`) – `standard`, `enhanced` or `auto`. Use `enhanced` for complex tables, charts, handwriting or low-quality scans; `auto` lets the API decide per page;  
     `ocr` (default `force`) – `force` always runs OCR, `auto` uses embedded text of digital documents when possible;  
     `model` (default `document-parse`) – the latest model, or a dated version such as `document-parse-260930` to pin it.
   - **Applied mode:** The response ends with the model and per-mode page usage reported by the API, e.g. `Processed by document-parse-260930 | usage: {"pages": 1, "enhanced": [1]}`. If the requested `standard`/`enhanced` mode was not applied, a `WARNING` line follows.
   - **Cost note:** `enhanced` (and pages that `auto` routes to enhanced) is billed at a higher per-page price than `standard` and is slower. Keep the default `standard` unless the document needs it.
   - **Example Query:**  
     *"Can you parse the document at `C:\Users\username\Documents\contract.pdf` and provide a summary?"*  
     *"Parse the scanned form at `~/Documents/form.pdf` in enhanced mode."*

2. **Information Extraction (`extract_information`):**
   - **Description:** Extracts structured information from documents based on predefined or auto-generated schemas.
   - **Parameters:**  
     `file_path` – the document file path;  
     `schema_path` (optional) – a JSON file with an extraction schema;  
     `auto_generate_schema` (default true) – whether to auto-generate a schema.
   - **Example Query:**  
     *"Extract the invoice number, date, and total from `C:\Users\username\Documents\invoice.pdf`."*

## Troubleshooting

### Common Issues

- **API Key Missing:**  
  Ensure that your UPSTAGE_API_KEY is correctly set in your `claude_desktop_config.json` file. Obtain a valid API key from [Upstage Console](https://console.upstage.ai/api-keys).

- **File Not Found:**  
  Double-check the file path for correctness and accessibility. Ensure that file paths are absolute (e.g., `C:\Users\name\Documents\file.pdf`) and that any special characters in the path are properly escaped.

- **Server Not Starting:**  
  Verify that your virtual environment is activated and all dependencies are installed. Additionally, review the Claude Desktop log files for errors:  
  - **Windows:** `%APPDATA%\Claude\logs\mcp-upstage.log`  
  - **macOS:** `~/Library/Logs/Claude/mcp-upstage.log`

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
  `%APPDATA%\Claude\logs\mcp-upstage.log`
- **macOS:**  
  `~/Library/Logs/Claude/mcp-upstage.log`

## Release / Deployment (Maintainers)

This repository publishes a Python package. MCP clients run it locally over stdio; the workflows do not deploy a hosted HTTP server.

### Deployment triggers and credentials

| Destination | Trigger | Workflow | GitHub environment | Secret |
| --- | --- | --- | --- | --- |
| TestPyPI | Push to `dev` | [Publish to TestPyPI](.github/workflows/test-publish.yml) | `test-pypi` | `TEST_PYPI_API_TOKEN` |
| PyPI | Publish a GitHub Release | [Publish to PyPI](.github/workflows/python-publish.yml) | `pypi` | `PYPI_API_TOKEN` |

Configure the secrets as GitHub Actions repository secrets or in the corresponding environment. These workflows currently use API tokens, not Trusted Publishing. `UPSTAGE_API_KEY` is required to run the MCP server and call Upstage APIs; it is separate from the publishing credentials.

Merging into `main` or pushing a tag alone does **not** publish to PyPI. A draft release does not publish either. Publishing a GitHub Release, including a prerelease, triggers the PyPI workflow. Use TestPyPI to validate a package before a public release.

### 1. Prepare a new package version

1. Fetch the latest `main` and `dev`, reconcile changes, and review the commits included in the release.
2. Set `__version__` in [src/upstage_mcp/__init__.py](src/upstage_mcp/__init__.py). Hatch reads the package version from this file; the release tag does not set it. Use a patch increment for fixes and a minor increment for new functionality, consistent with recent releases.
3. Run `uv lock` after changing the version or dependencies, and commit the updated `uv.lock` when it changes.
4. Use a version whose distribution filenames have not already been uploaded to the target index. PyPI and TestPyPI cannot overwrite existing distribution files. Additional package changes after a TestPyPI upload need a new version before another upload; do not reuse the same version for different artifacts on the same index.

### 2. Validate and publish to TestPyPI

Run these checks from the repository root before pushing release changes to `dev`:

```bash
uv lock --check
uv sync --frozen --extra dev
UPSTAGE_API_KEY=dummy uv run --frozen pytest -q
uv build
```

A dummy key is sufficient for the automated tests, but not for real API calls. [CI](.github/workflows/ci.yml) also tests fresh installations without the lockfile on Python 3.10 and 3.12, plus a locked installation.

After pushing to `dev`, confirm both CI and `Publish to TestPyPI` succeeded for the intended commit, and check that the expected wheel and source distribution exist on [TestPyPI](https://test.pypi.org/project/mcp-upstage/). CI and publishing run independently; a successful upload does not prove CI passed. Inspect the built package and test its MCP behavior before promoting it.

### 3. Promote `dev` to `main`

Create a release PR with `dev` as the head and `main` as the base. The [branch-policy workflow](.github/workflows/protect-main.yml) automatically closes newly opened PRs to `main` unless their head is this repository's `dev` branch.

```bash
gh pr create --base main --head dev --title "release: <version>"
```

Describe the included changes and validation results in the PR description.

Wait for the release PR's checks and required reviews to pass, then merge it. Verify that the merged commit contains exactly the version and changes you intend to publish. CI is not a dependency of the PyPI publishing workflow, so complete this verification **before** publishing the release.

### 4. Publish the GitHub Release

Use the merged release PR's exact commit as the tag target. Replace the placeholders below; the version must match `__version__` and must be unused on PyPI. Existing releases use tags without a `v` prefix, such as `0.2.0`.

```bash
RELEASE_VERSION="<new-version>"
RELEASE_PR="<merged-release-pr-number>"
RELEASE_SHA=$(gh pr view "$RELEASE_PR" --json mergeCommit --jq '.mergeCommit.oid')

git fetch origin main --tags
git show "$RELEASE_SHA:src/upstage_mcp/__init__.py"

# Run only after confirming the commit and version above.
gh release create "$RELEASE_VERSION" \
  --target "$RELEASE_SHA" \
  --title "Upstage MCP v$RELEASE_VERSION" \
  --generate-notes \
  --latest
```

Confirm that the tag points to the intended commit. If the tag already exists, `--target` does not move it; verify the existing tag before publishing. Do not retag a published release to repair a package.

### 5. Verify the public package

1. In [GitHub Actions](https://github.com/UpstageAI/mcp-upstage/actions), wait for **both** `build` and `publish` in `Publish to PyPI` to finish successfully. Check the run's commit SHA against the release commit; a queued run or a published GitHub Release alone is not deployment proof.
2. Confirm the version, wheel, and source distribution on [PyPI](https://pypi.org/project/mcp-upstage/).
3. Install the exact version from the public index, without loading the local checkout:

```bash
uv run --no-project --index-url https://pypi.org/simple \
  --refresh-package mcp-upstage --with "mcp-upstage==$RELEASE_VERSION" \
  python -c 'from importlib.metadata import version; print(version("mcp-upstage"))'
```

Configure an MCP client with the following command and arguments, replacing `<version>` with the released version. Supply a real `UPSTAGE_API_KEY` through the client's environment settings.

```json
{
  "command": "uvx",
  "args": ["--index-url", "https://pypi.org/simple", "--refresh-package", "mcp-upstage", "mcp-upstage==<version>"]
}
```

Restart the client, initialize the MCP connection, and list tools. Confirm `parse_document` and `extract_information` are available and the parsing schema exposes `mode`, `ocr`, and `model`.

For an end-to-end check, use a small synthetic document with known values. Verify default/standard, enhanced, and auto parsing, the API-reported model and per-mode `usage`, information extraction, and the saved result files under `~/.mcp-upstage/outputs/`. Test automatic schema generation and an explicit schema. These calls use the real Upstage API and incur normal usage charges; enhanced processing can cost more than standard. Import or tool-list checks alone do not verify document processing.

**Known limitation observed with `mcp-upstage 0.2.0` and `mcp 1.30.0`:** passing a JSON object encoded as a `schema_json` string fails MCP argument validation before the extraction API is called. Automatic schema generation and `schema_path` with a JSON schema file were verified successfully. Record this limitation when validating 0.2.0; do not count the failing path as passed.

If publishing fails, inspect the failed job before retrying. Check token access, the version, and whether either distribution was already uploaded. Do not assume a failed workflow means no files reached the index. For a faulty published package, fix the code and release a new version rather than overwriting the existing one.

## Contributing

Contributions are welcome! If you wish to enhance the project or add new features, please fork the repository and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License.

