"""Test validation functions for Upstage MCP server."""

from pathlib import Path

import pytest

from upstage_mcp.utils import validate_file_exists, validate_file_size, validate_file_extension


@pytest.fixture
def temp_pdf_file(tmp_path: Path) -> Path:
    """Create a minimal PDF file for testing."""
    pdf_path = tmp_path / "test_document.pdf"

    # Minimal PDF content (just enough to be recognized as PDF)
    minimal_pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"

    pdf_path.write_bytes(minimal_pdf_content)  # type: ignore
    return pdf_path


class TestValidationFunctions:
    """Test that validation functions work correctly."""

    def test_validate_file_exists_should_pass_for_existing_file(self, temp_pdf_file: Path):
        """Given an existing file
        When validating file existence
        Then validation should pass"""
        
        # When: Validating existing file
        # Then: Should not raise any exception
        validate_file_exists(str(temp_pdf_file))

    def test_validate_file_exists_should_raise_for_nonexistent_file(self, tmp_path: Path):
        """Given a non-existent file path
        When validating file existence
        Then validation should raise FileNotFoundError"""
        
        # Given: Non-existent file path
        nonexistent_file = tmp_path / "nonexistent.pdf"
        
        # When/Then: Validating should raise FileNotFoundError
        with pytest.raises(FileNotFoundError, match="File not found"):
            validate_file_exists(str(nonexistent_file))

    def test_validate_file_extension_should_pass_for_supported_format(self, temp_pdf_file: Path):
        """Given a file with supported extension
        When validating file extension
        Then validation should pass"""
        
        # Given: Supported extensions
        supported_extensions = {".pdf", ".jpg", ".png"}
        
        # When: Validating supported file extension
        # Then: Should not raise any exception
        validate_file_extension(str(temp_pdf_file), supported_extensions)

    def test_validate_file_extension_should_raise_for_unsupported_format(self, temp_pdf_file: Path):
        """Given a file with unsupported extension
        When validating file extension
        Then validation should raise ValueError"""
        
        # Given: Unsupported extensions
        supported_extensions = {".jpg", ".png"}
        
        # When/Then: Validating unsupported file extension should raise ValueError
        with pytest.raises(ValueError, match="Unsupported file format"):
            validate_file_extension(str(temp_pdf_file), supported_extensions)

    def test_validate_file_size_should_pass_for_small_file(self, temp_pdf_file: Path):
        """Given a file within size limit
        When validating file size
        Then validation should pass"""
        
        # Given: Large size limit
        max_size = 1024 * 1024  # 1MB
        
        # When: Validating file size
        # Then: Should not raise any exception
        validate_file_size(str(temp_pdf_file), max_size)

    def test_validate_file_size_should_raise_for_large_file(self, tmp_path: Path):
        """Given a file exceeding size limit
        When validating file size
        Then validation should raise ValueError"""
        
        # Given: Large file
        large_file = tmp_path / "large.txt"
        large_content = "x" * (1024 * 1024 + 1)  # 1MB + 1 byte
        large_file.write_text(large_content)
        
        # Given: Small size limit
        max_size = 1024 * 1024  # 1MB
        
        # When/Then: Validating large file should raise ValueError
        with pytest.raises(ValueError, match="File exceeds maximum size"):
            validate_file_size(str(large_file), max_size)

    def test_validate_file_size_should_handle_edge_case_exact_size(self, tmp_path: Path):
        """Given a file exactly at the size limit
        When validating file size
        Then validation should pass"""
        
        # Given: File exactly at size limit
        exact_file = tmp_path / "exact.txt"
        exact_content = "x" * (1024 * 1024)  # Exactly 1MB
        exact_file.write_text(exact_content)
        
        # Given: Size limit
        max_size = 1024 * 1024  # 1MB
        
        # When: Validating file size
        # Then: Should not raise any exception (exact size is allowed)
        validate_file_size(str(exact_file), max_size)

    def test_validate_file_extension_should_be_case_insensitive(self, tmp_path: Path):
        """Given a file with uppercase extension
        When validating file extension
        Then validation should pass (case insensitive)"""
        
        # Given: File with uppercase extension
        uppercase_file = tmp_path / "test.PDF"
        uppercase_file.write_bytes(b"%PDF-1.4\n%%EOF")  # type: ignore
        
        # Given: Supported extensions in lowercase
        supported_extensions = {".pdf", ".jpg", ".png"}
        
        # When: Validating file extension
        # Then: Should not raise any exception (case insensitive)
        validate_file_extension(str(uppercase_file), supported_extensions)
