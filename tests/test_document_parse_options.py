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

from upstage_mcp import document_parser, info_extractor
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
            # standard is the API default; the field is omitted for compatibility
            assert "mode" not in data
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


    @pytest.mark.asyncio
    async def test_should_send_auto_mode(self, mock_api_key: str, temp_pdf_file: Path):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _response(200, _api_body({"pages": 1, "enhanced": [1]}))

            await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file), api_key=mock_api_key, mode="auto"
            )

            assert mock_post.call_args.kwargs["data"]["mode"] == "auto"


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
        assert "WARNING" not in text
        assert "Could not confirm" not in text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("usage", [{"pages": 3}, None])
    async def test_should_note_unconfirmed_enhanced_without_per_mode_usage(
        self, mock_api_key: str, temp_pdf_file: Path, usage
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _response(200, _api_body(usage))

            text = await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file), api_key=mock_api_key, mode="enhanced"
            )

        assert "Note: Could not confirm mode 'enhanced' was applied" in text
        assert "WARNING" not in text

    @pytest.mark.asyncio
    async def test_should_stay_silent_for_standard_without_per_mode_usage(self, mock_api_key: str, temp_pdf_file: Path):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _response(200, _api_body({"pages": 3}))

            text = await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file), api_key=mock_api_key
            )

        assert 'Processed by document-parse-260930 | usage: {"pages": 3}' in text
        assert "WARNING" not in text
        assert "Could not confirm" not in text

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
    """Only failures where the request was not processed (connect errors, 429, 503) are retried."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [429, 503])
    async def test_should_retry_when_request_not_processed(
        self, mock_api_key: str, temp_pdf_file: Path, no_retry_wait, status_code: int
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [
                _response(status_code, {"error": "try again"}),
                _response(200, _api_body({"pages": 1, "standard": [1]})),
            ]

            text = await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file), api_key=mock_api_key
            )

        assert mock_post.call_count == 2
        assert "Processed by document-parse-260930" in text

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [400, 500, 502, 504])
    async def test_should_not_retry_when_server_may_have_processed(
        self, mock_api_key: str, temp_pdf_file: Path, no_retry_wait, mock_ctx: MagicMock, status_code: int
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _response(status_code, {"error": "failed"})

            with pytest.raises(Exception, match=f"HTTP error from Upstage API: {status_code}"):
                await document_parser.parse_and_save_document(
                    file_path=str(temp_pdf_file), api_key=mock_api_key, ctx=mock_ctx
                )

        assert mock_post.call_count == 1
        mock_ctx.error.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("error_cls", [httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout])
    async def test_should_retry_on_pre_send_failure(
        self, mock_api_key: str, temp_pdf_file: Path, no_retry_wait, error_cls
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [
                error_cls("boom", request=httpx.Request("POST", API_URL)),
                _response(200, _api_body({"pages": 1, "standard": [1]})),
            ]

            await document_parser.parse_and_save_document(
                file_path=str(temp_pdf_file), api_key=mock_api_key
            )

        assert mock_post.call_count == 2

    @pytest.mark.asyncio
    @pytest.mark.parametrize("error_cls", [httpx.ReadTimeout, httpx.ReadError, httpx.RemoteProtocolError])
    async def test_should_not_retry_after_request_was_sent(
        self, mock_api_key: str, temp_pdf_file: Path, no_retry_wait, error_cls
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = error_cls("boom", request=httpx.Request("POST", API_URL))

            with pytest.raises(Exception, match="Request error connecting to Upstage API"):
                await document_parser.parse_and_save_document(
                    file_path=str(temp_pdf_file), api_key=mock_api_key
                )

        assert mock_post.call_count == 1

    @pytest.mark.asyncio
    async def test_should_give_up_after_three_attempts(self, mock_api_key: str, temp_pdf_file: Path, no_retry_wait):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = _response(503, {"error": "unavailable"})

            with pytest.raises(Exception, match="HTTP error from Upstage API: 503"):
                await document_parser.parse_and_save_document(
                    file_path=str(temp_pdf_file), api_key=mock_api_key
                )

        assert mock_post.call_count == 3

    @pytest.mark.asyncio
    async def test_should_fail_without_retry_on_non_json_success_response(
        self, mock_api_key: str, temp_pdf_file: Path, no_retry_wait, mock_ctx: MagicMock
    ):
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = httpx.Response(
                200, content=b"<html>gateway page</html>", request=httpx.Request("POST", API_URL)
            )

            with pytest.raises(Exception, match="Error during document parsing"):
                await document_parser.parse_and_save_document(
                    file_path=str(temp_pdf_file), api_key=mock_api_key, ctx=mock_ctx
                )

        assert mock_post.call_count == 1
        mock_ctx.error.assert_awaited_once()


class TestInfoExtractorContextLogging:
    """info_extractor must await the async Context logging methods."""

    @pytest.mark.asyncio
    async def test_should_await_info_logs_during_extraction(
        self, mock_api_key: str, temp_pdf_file: Path, mock_ctx: MagicMock
    ):
        schema_response = {"choices": [{"message": {"content": json.dumps(
            {"json_schema": {"type": "object", "properties": {"total": {"type": "string"}}}}
        )}}]}
        extraction_response = {"choices": [{"message": {"content": json.dumps({"total": "10,000원"})}}]}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [_response(200, schema_response), _response(200, extraction_response)]

            text = await info_extractor.extract_information_from_file(
                file_path=str(temp_pdf_file), api_key=mock_api_key, ctx=mock_ctx, auto_generate_schema=True
            )

        assert '"total": "10,000원"' in text
        # Every info() call must have been awaited (an un-awaited call is counted but not awaited).
        assert mock_ctx.info.call_count >= 5
        assert mock_ctx.info.await_count == mock_ctx.info.call_count


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
