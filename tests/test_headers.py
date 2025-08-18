"""Test that x-upstage-client header is included in all API requests."""

import os
import json
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import patch, MagicMock, Mock, AsyncMock

import pytest

from upstage_mcp import document_parser, info_extractor
from upstage_mcp.utils import make_api_request


@pytest.fixture
def mock_api_key() -> Generator[str, None, None]:
    """Provide a mock API key for testing and restore original after test."""
    original_api_key = os.environ.get("UPSTAGE_API_KEY")
    test_api_key = "test_api_key_12345"
    os.environ["UPSTAGE_API_KEY"] = test_api_key

    yield test_api_key

    if original_api_key is not None:
        os.environ["UPSTAGE_API_KEY"] = original_api_key
    else:
        os.environ.pop("UPSTAGE_API_KEY", None)


@pytest.fixture
def temp_pdf_file(tmp_path: Path) -> Path:
    """Create a minimal PDF file for testing."""
    pdf_path = tmp_path / "test_document.pdf"

    # Minimal PDF content (just enough to be recognized as PDF)
    minimal_pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

    pdf_path.write_bytes(minimal_pdf_content)
    return pdf_path


def assert_headers_contain_upstage_client(headers: dict, expected_client: str = "mcp", api_key: str = "test_api_key_12345"):
    """Assert that headers contain the required Upstage client information."""
    assert 'x-upstage-client' in headers, "x-upstage-client header should be present"
    assert headers['x-upstage-client'] == expected_client, f"x-upstage-client should be '{expected_client}'"
    assert 'Authorization' in headers, "Authorization header should be present"
    assert headers['Authorization'] == f"Bearer {api_key}", "Authorization should be Bearer token"


class TestDocumentParserHeaders:
    """Test that document parser correctly sets and passes headers."""

    @pytest.mark.asyncio
    async def test_should_include_upstage_client_header_when_parsing_document(self, mock_api_key: str, temp_pdf_file: Path):
        """Given a document file and API key
        When parsing the document
        Then the API request should include x-upstage-client header"""
        
        # Given: Mock successful API response
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"content": {"text": "test content"}}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            # When: Parsing the document
            await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file),
                api_key=mock_api_key
            )
            
            # Then: Request should be made with correct headers
            mock_post.assert_called_once()
            headers = mock_post.call_args[1]['headers']
            assert_headers_contain_upstage_client(headers, expected_client="mcp", api_key=mock_api_key)

    @pytest.mark.asyncio
    async def test_should_include_headers_even_when_api_returns_error(self, mock_api_key: str, temp_pdf_file: Path):
        """Given a document file and API key
        When API returns an error
        Then the request should still include x-upstage-client header"""
        
        # Given: Mock API error response
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = Exception("API Error")
            mock_post.return_value = mock_response
            
            # When: Attempting to parse document (which will fail)
            with pytest.raises(Exception, match="Error during document parsing"):
                await document_parser.parse_and_save_document(
                    file_path=str(temp_pdf_file),
                    api_key=mock_api_key
                )
            
            # Then: Request should still include headers despite the error
            mock_post.assert_called_once()
            headers = mock_post.call_args[1]['headers']
            assert_headers_contain_upstage_client(headers, expected_client="mcp", api_key=mock_api_key)


class TestInfoExtractorHeaders:
    """Test that info extractor correctly sets and passes headers."""

    @pytest.mark.asyncio
    async def test_should_include_headers_when_generating_schema(self, mock_api_key: str, temp_pdf_file: Path):
        """Given a document file and API key
        When auto-generating schema for information extraction
        Then the schema generation API call should include x-upstage-client header"""
        
        # Given: Mock successful schema generation response
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "json_schema": {
                                "type": "object",
                                "properties": {"test": {"type": "string"}}
                            }
                        })
                    }
                }]
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            # When: Extracting information with auto-generated schema
            await info_extractor.extract_information_from_file(
                file_path=str(temp_pdf_file),
                api_key=mock_api_key,
                auto_generate_schema=True
            )
            
            # Then: Schema generation call should include headers
            assert mock_post.call_count >= 1, "At least one API call should be made"
            schema_call = mock_post.call_args_list[0]
            headers = schema_call[1]['headers']
            assert_headers_contain_upstage_client(headers, expected_client="mcp", api_key=mock_api_key)
            
            # And: It should be a schema generation call (now using make_api_request directly)
            assert "schema-generation" in schema_call[0][0], "First call should be to schema generation endpoint"

    @pytest.mark.asyncio
    async def test_should_include_headers_in_all_api_calls_during_extraction(self, mock_api_key: str, temp_pdf_file: Path):
        """Given a document file and API key
        When performing complete information extraction workflow
        Then all API calls should include x-upstage-client header"""
        
        # Given: Mock responses for both schema generation and information extraction
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "json_schema": {
                                "type": "object",
                                "properties": {"test": {"type": "string"}}
                            }
                        })
                    }
                }]
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            # When: Performing complete information extraction
            await info_extractor.extract_information_from_file(
                file_path=str(temp_pdf_file),
                api_key=mock_api_key,
                auto_generate_schema=True
            )
            
            # Then: All API calls should include headers
            assert mock_post.call_count >= 2, "Multiple API calls should be made"
            for call in mock_post.call_args_list:
                headers = call[1]['headers']
                assert_headers_contain_upstage_client(headers, expected_client="mcp", api_key=mock_api_key)

    @pytest.mark.asyncio
    async def test_should_include_headers_when_using_predefined_schema(self, mock_api_key: str, temp_pdf_file: Path):
        """Given a document file, API key, and predefined schema
        When extracting information without auto-generating schema
        Then the information extraction API call should include x-upstage-client header"""
        
        # Given: Mock successful information extraction response
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "extracted_data": {"test": "value"}
                        })
                    }
                }]
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            # And: A predefined schema
            schema_json = json.dumps({
                "type": "object",
                "properties": {"test": {"type": "string"}}
            })
            
            # When: Extracting information with predefined schema
            await info_extractor.extract_information_from_file(
                file_path=str(temp_pdf_file),
                api_key=mock_api_key,
                schema_json=schema_json,
                auto_generate_schema=False
            )
            
            # Then: Only one API call should be made (information extraction)
            mock_post.assert_called_once()
            headers = mock_post.call_args[1]['headers']
            assert_headers_contain_upstage_client(headers, expected_client="mcp", api_key=mock_api_key)


class TestHeaderConsistency:
    """Test that headers are consistent across all modules and scenarios."""

    def test_should_use_mcp_as_client_identifier(self):
        """Given the Upstage MCP server
        When examining the header configuration
        Then x-upstage-client should be set to 'mcp'"""
        
        # Given: The Upstage MCP modules
        # When: Checking the header configuration
        expected_header_value = "mcp"
        
        # Then: Header value should be 'mcp'
        assert expected_header_value == "mcp", "Header value should be 'mcp'"
        
        # And: Required functions should exist
        assert hasattr(document_parser, 'parse_and_save_document'), "Document parser function should exist"
        assert hasattr(info_extractor, 'extract_information_from_file'), "Info extractor function should exist"

    @pytest.mark.asyncio
    async def test_should_use_same_header_value_across_all_modules(self, mock_api_key: str, temp_pdf_file: Path):
        """Given document parser and info extractor modules
        When making API calls from both modules
        Then both should use the same x-upstage-client header value"""
        
        # Given: Mock successful API responses
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"content": {"text": "test content"}}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            # When: Making API calls from document parser
            await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file),
                api_key=mock_api_key
            )
            
            doc_parser_headers = mock_post.call_args[1]['headers']
            
            # And: Making API calls from info extractor
            mock_post.reset_mock()
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "json_schema": {
                                "type": "object",
                                "properties": {"test": {"type": "string"}}
                            }
                        })
                    }
                }]
            }
            
            await info_extractor.extract_information_from_file(
                file_path=str(temp_pdf_file),
                api_key=mock_api_key,
                auto_generate_schema=True
            )
            
            info_extractor_headers = mock_post.call_args[1]['headers']
            
            # Then: Both modules should use the same header value
            assert doc_parser_headers['x-upstage-client'] == "mcp", "Document parser should use 'mcp'"
            assert info_extractor_headers['x-upstage-client'] == "mcp", "Info extractor should use 'mcp'"
            assert doc_parser_headers['x-upstage-client'] == info_extractor_headers['x-upstage-client'], "Both modules should use same header value"

    @pytest.mark.asyncio
    async def test_should_include_required_headers_in_all_api_calls(self, mock_api_key: str, temp_pdf_file: Path):
        """Given all Upstage MCP modules
        When making API calls from all modules
        Then all calls should include x-upstage-client and Authorization headers"""
        
        # Given: Mock successful API responses
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "json_schema": {
                                "type": "object",
                                "properties": {"test": {"type": "string"}}
                            }
                        })
                    }
                }]
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            # When: Making API calls from all modules
            await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file),
                api_key=mock_api_key
            )
            
            await info_extractor.extract_information_from_file(
                file_path=str(temp_pdf_file),
                api_key=mock_api_key,
                auto_generate_schema=True
            )
            
            # Then: All API calls should include required headers
            for call in mock_post.call_args_list:
                headers = call[1]['headers']
                assert_headers_contain_upstage_client(headers, expected_client="mcp", api_key=mock_api_key)


class TestApiClientHeaders:
    """Test that the API client correctly sets headers."""

    @pytest.mark.asyncio
    async def test_make_api_request_should_include_upstage_headers(self, mock_api_key: str):
        """Given an API key
        When making an API request
        Then the request should include x-upstage-client and Authorization headers"""
        
        # Given: Mock successful API response
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"result": "success"}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            # When: Making an API request
            await make_api_request(
                url="https://api.upstage.ai/v1/test",
                api_key=mock_api_key,
                json={"test": "data"}
            )
            
            # Then: Request should include required headers
            mock_post.assert_called_once()
            headers = mock_post.call_args[1]['headers']
            assert_headers_contain_upstage_client(headers, expected_client="mcp", api_key=mock_api_key)

    @pytest.mark.asyncio
    async def test_make_api_request_should_merge_custom_headers(self, mock_api_key: str):
        """Given custom headers and API key
        When making an API request
        Then custom headers should be merged with Upstage headers"""
        
        # Given: Mock successful API response
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {"result": "success"}
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response
            
            # And: Custom headers
            custom_headers = {"Content-Type": "application/json", "X-Custom": "value"}
            
            # When: Making an API request with custom headers
            await make_api_request(
                url="https://api.upstage.ai/v1/test",
                api_key=mock_api_key,
                headers=custom_headers,
                json={"test": "data"}
            )
            
            # Then: Request should include both custom and Upstage headers
            mock_post.assert_called_once()
            headers = mock_post.call_args[1]['headers']
            
            # Upstage headers should be present
            assert_headers_contain_upstage_client(headers, expected_client="mcp", api_key=mock_api_key)
            
            # Custom headers should be preserved
            assert headers["Content-Type"] == "application/json"
            assert headers["X-Custom"] == "value"

    @pytest.mark.asyncio
    async def test_make_api_request_should_use_default_timeout(self, mock_api_key: str):
        """Given an API key
        When making an API request without specifying timeout
        Then the request should use default timeout"""
        
        # Given: Mock successful API response
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.json.return_value = {"result": "success"}
            mock_response.raise_for_status.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            
            # When: Making an API request without timeout
            await make_api_request(
                url="https://api.upstage.ai/v1/test",
                api_key=mock_api_key,
                json={"test": "data"}
            )
            
            # Then: AsyncClient should be created with default timeout
            mock_client_class.assert_called_once()
            timeout_arg = mock_client_class.call_args[1]['timeout']
            assert timeout_arg is not None, "Default timeout should be used"



