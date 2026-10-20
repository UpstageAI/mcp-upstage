"""Tests for parse_document options (mode/ocr/model), applied-mode reporting and retries."""

import json
import os
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from mcp.server.fastmcp import Context
from tenacity import wait_none

from upstage_mcp import document_parser
from upstage_mcp.utils import api_client

API_URL = document_parser.DOCUMENT_DIGITIZATION_URL


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
    pdf_path.write_bytes(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF")
    return pdf_path


@pytest.fixture
def no_retry_wait(monkeypatch):
    """Remove the exponential backoff between retries so tests run instantly."""
    monkeypatch.setattr(api_client._post_with_retry.retry, "wait", wait_none())


@pytest.fixture
def mock_ctx() -> MagicMock:
    """A Context mock that only exposes the real Context API (no `warn`)."""
    return MagicMock(spec=Context)


def _response(status_code: int, body: dict | None = None) -> httpx.Response:
    """Build a real httpx response so raise_for_status behaves like production."""
    return httpx.Response(
        status_code,
        json=body if body is not None else {},
        request=httpx.Request("POST", API_URL),
    )


def _api_body(usage: dict | None, model: str | None = "document-parse-260930") -> dict:
    body = {"content": {"html": "", "markdown": "", "text": "영수증 합계 10,000원"}}
    if model is not None:
        body["model"] = model
    if usage is not None:
        body["usage"] = usage
    return body


class TestParseOptionsSentToApi:
    """mode/ocr/model must reach the multipart form sent to the API."""

    @pytest.mark.asyncio
    async def test_should_send_default_options_when_not_specified(self, mock_api_key: str, temp_pdf_file: Path):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _response(200, _api_body({"pages": 1, "standard": [1]}))

            await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file),
                api_key=mock_api_key,
            )

            data = mock_post.call_args.kwargs["data"]
            assert data["mode"] == "standard"
            assert data["ocr"] == "force"
            assert data["model"] == "document-parse"

    @pytest.mark.asyncio
    async def test_should_send_enhanced_mode_and_custom_options(self, mock_api_key: str, temp_pdf_file: Path):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _response(200, _api_body({"pages": 1, "enhanced": [1]}))

            await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file),
                api_key=mock_api_key,
                mode="enhanced",
                ocr="auto",
                model="document-parse-260930",
            )

            data = mock_post.call_args.kwargs["data"]
            assert data["mode"] == "enhanced"
            assert data["ocr"] == "auto"
            assert data["model"] == "document-parse-260930"


class TestAppliedModeReporting:
    """The tool response must state how the API actually processed the document."""

    @pytest.mark.asyncio
    async def test_should_report_model_and_usage_when_mode_applied(self, mock_api_key: str, temp_pdf_file: Path):
        usage = {"pages": 1, "enhanced": [1]}
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _response(200, _api_body(usage))

            text = await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file), api_key=mock_api_key, mode="enhanced"
            )

        assert f"Processed by document-parse-260930 | usage: {json.dumps(usage)}" in text
        assert "WARNING" not in text

    @pytest.mark.asyncio
    async def test_should_warn_when_enhanced_requested_but_standard_applied(self, mock_api_key: str, temp_pdf_file: Path):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _response(200, _api_body({"pages": 1, "standard": [1]}))

            text = await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file), api_key=mock_api_key, mode="enhanced"
            )

        assert "Processed by document-parse-260930" in text
        assert "WARNING: Requested mode 'enhanced' was not applied" in text
        assert "applied: standard" in text

    @pytest.mark.asyncio
    async def test_should_warn_when_requested_mode_only_partially_applied(self, mock_api_key: str, temp_pdf_file: Path):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _response(200, _api_body({"pages": 2, "standard": [1], "enhanced": [2]}))

            text = await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file), api_key=mock_api_key, mode="standard"
            )

        assert "WARNING: Requested mode 'standard' was not applied" in text

    @pytest.mark.asyncio
    async def test_should_not_warn_for_auto_mode(self, mock_api_key: str, temp_pdf_file: Path):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _response(200, _api_body({"pages": 2, "standard": [1], "enhanced": [2]}))

            text = await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file), api_key=mock_api_key, mode="auto"
            )

        assert "Processed by document-parse-260930" in text
        assert "WARNING" not in text

    @pytest.mark.asyncio
    async def test_should_handle_missing_model_and_usage(self, mock_api_key: str, temp_pdf_file: Path):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _response(200, _api_body(usage=None, model=None))

            text = await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file), api_key=mock_api_key
            )

        assert "Processed by unknown model | usage: not reported" in text
        assert "WARNING: Could not confirm that mode 'standard' was applied" in text

    @pytest.mark.asyncio
    async def test_should_not_escape_non_ascii_content(self, mock_api_key: str, temp_pdf_file: Path):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _response(200, _api_body({"pages": 1, "standard": [1]}))

            text = await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file), api_key=mock_api_key
            )

        assert "영수증 합계" in text
        assert "\\u" not in text


class TestContextLogging:
    """Context logging calls must use the real async Context API."""

    @pytest.mark.asyncio
    async def test_should_await_info_logs(self, mock_api_key: str, temp_pdf_file: Path, mock_ctx: MagicMock):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _response(200, _api_body({"pages": 1, "standard": [1]}))

            await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file), api_key=mock_api_key, ctx=mock_ctx
            )

        assert mock_ctx.info.await_count >= 2

    @pytest.mark.asyncio
    async def test_should_warn_via_ctx_warning_when_save_fails(
        self, mock_api_key: str, temp_pdf_file: Path, mock_ctx: MagicMock
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post, \
                patch.object(document_parser, "async_json_dump", AsyncMock(side_effect=OSError("disk full"))):
            mock_post.return_value = _response(200, _api_body({"pages": 1, "standard": [1]}))

            text = await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file), api_key=mock_api_key, ctx=mock_ctx
            )

        mock_ctx.warning.assert_awaited_once()
        assert "disk full" in mock_ctx.warning.await_args.args[0]
        assert "Could not save the full response to disk" in text


class TestRetry:
    """Only transient failures (connection errors, 429, 5xx) are retried."""

    @pytest.mark.asyncio
    async def test_should_retry_on_503_then_succeed(self, mock_api_key: str, temp_pdf_file: Path, no_retry_wait):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [
                _response(503, {"error": "unavailable"}),
                _response(200, _api_body({"pages": 1, "standard": [1]})),
            ]

            text = await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file), api_key=mock_api_key
            )

        assert mock_post.call_count == 2
        assert "Processed by document-parse-260930" in text

    @pytest.mark.asyncio
    async def test_should_retry_on_connection_error(self, mock_api_key: str, temp_pdf_file: Path, no_retry_wait):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [
                httpx.ConnectError("boom", request=httpx.Request("POST", API_URL)),
                _response(200, _api_body({"pages": 1, "standard": [1]})),
            ]

            await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file), api_key=mock_api_key
            )

        assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_should_give_up_after_three_5xx(self, mock_api_key: str, temp_pdf_file: Path, no_retry_wait):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _response(500, {"error": "internal"})

            with pytest.raises(Exception, match="HTTP error from Upstage API: 500"):
                await document_parser.parse_and_save_document(
                    file_path=str(temp_pdf_file), api_key=mock_api_key
                )

        assert mock_post.call_count == 3

    @pytest.mark.asyncio
    async def test_should_not_retry_on_400(
        self, mock_api_key: str, temp_pdf_file: Path, no_retry_wait, mock_ctx: MagicMock
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _response(400, {"error": "bad request"})

            with pytest.raises(Exception, match="HTTP error from Upstage API: 400"):
                await document_parser.parse_and_save_document(
                    file_path=str(temp_pdf_file), api_key=mock_api_key, ctx=mock_ctx
                )

        assert mock_post.call_count == 1
        mock_ctx.error.assert_awaited_once()


class TestServerTool:
    """The MCP tool must expose the options and pass them through to the parser."""

    @pytest.mark.asyncio
    async def test_should_expose_options_in_tool_schema(self):
        from upstage_mcp import server

        tools = {tool.name: tool for tool in await server.mcp.list_tools()}
        properties = tools["parse_document"].inputSchema["properties"]

        assert properties["mode"]["enum"] == ["standard", "enhanced", "auto"]
        assert properties["mode"]["default"] == "standard"
        assert properties["ocr"]["enum"] == ["auto", "force"]
        assert properties["ocr"]["default"] == "force"
        assert properties["model"]["default"] == "document-parse"
        assert "enhanced" in properties["mode"]["description"]

    @pytest.mark.asyncio
    async def test_should_pass_options_from_tool_call_to_parser(self, temp_pdf_file: Path):
        from upstage_mcp import server

        with patch.object(server.document_parser, "parse_and_save_document", AsyncMock(return_value="ok")) as mock_parse:
            await server.mcp.call_tool(
                "parse_document",
                {"file_path": str(temp_pdf_file), "mode": "enhanced", "ocr": "auto", "model": "document-parse-260930"},
            )

        kwargs = mock_parse.await_args.kwargs
        assert (kwargs["mode"], kwargs["ocr"], kwargs["model"]) == ("enhanced", "auto", "document-parse-260930")
