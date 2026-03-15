"""
Unit tests for GLM-OCR client.

Tests cover:
- Availability checking
- Happy path OCR flow
- Missing Ollama handling
- Error handling
- Batch processing
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from algl_pdf_helper.glm_ocr_client import (
    GLMOCRClient,
    GLMOCResult,
    GLMOCRFallback,
    create_glm_ocr_result_storage,
)


class TestGLMOCResult:
    """Tests for GLMOCResult dataclass."""
    
    def test_success_property_true(self):
        """Test success property when result is successful."""
        result = GLMOCResult(
            slice_id="test",
            ocr_text="Extracted text",
            pages_processed=[1, 2],
        )
        assert result.success is True
    
    def test_success_property_false_no_text(self):
        """Test success property when no text extracted."""
        result = GLMOCResult(
            slice_id="test",
            ocr_text="",
            pages_processed=[1, 2],
        )
        assert result.success is False
    
    def test_success_property_false_with_error(self):
        """Test success property when error occurred."""
        result = GLMOCResult(
            slice_id="test",
            error="Something went wrong",
            pages_processed=[1, 2],
        )
        assert result.success is False
    
    def test_to_dict_truncates_long_text(self):
        """Test that to_dict truncates very long text."""
        long_text = "x" * 2000
        result = GLMOCResult(
            slice_id="test",
            ocr_text=long_text,
            pages_processed=[1],
        )
        data = result.to_dict()
        assert data["ocr_text_length"] == 2000
        assert len(data["ocr_text"]) < 1500  # Should be truncated
        assert "..." in data["ocr_text"]


class TestGLMOCRClientAvailability:
    """Tests for client availability checking."""
    
    def test_available_when_model_present(self):
        """Test availability check when model is present."""
        mock_response = {
            "models": [
                {"name": "glm-ocr:latest"},
                {"name": "qwen2.5:3b"},
            ]
        }
        
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_cm = Mock()
            mock_cm.__enter__ = Mock(return_value=Mock(
                status=200,
                read=Mock(return_value=json.dumps(mock_response).encode())
            ))
            mock_cm.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_cm
            
            client = GLMOCRClient()
            assert client.available is True
    
    def test_not_available_when_model_missing(self):
        """Test availability check when model is not present."""
        mock_response = {
            "models": [
                {"name": "qwen2.5:3b"},
            ]
        }
        
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_cm = Mock()
            mock_cm.__enter__ = Mock(return_value=Mock(
                status=200,
                read=Mock(return_value=json.dumps(mock_response).encode())
            ))
            mock_cm.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_cm
            
            client = GLMOCRClient()
            assert client.available is False
    
    def test_not_available_when_ollama_down(self):
        """Test availability check when Ollama is not running."""
        with patch('urllib.request.urlopen') as mock_urlopen:
            from urllib.error import URLError
            mock_urlopen.side_effect = URLError("Connection refused")
            
            client = GLMOCRClient()
            assert client.available is False


class TestGLMOCRClientOCR:
    """Tests for OCR functionality."""
    
    def test_ocr_pdf_slice_not_available(self):
        """Test OCR when client is not available."""
        client = GLMOCRClient()
        client._available = False
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake pdf")
            temp_path = f.name
        
        try:
            result = client.ocr_pdf_slice(temp_path, [1, 2], "test_slice")
            assert result.success is False
            assert "not available" in result.error.lower()
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_ocr_pdf_slice_file_not_found(self):
        """Test OCR when PDF file doesn't exist."""
        client = GLMOCRClient()
        client._available = True
        
        result = client.ocr_pdf_slice("/nonexistent/file.pdf", [1], "test")
        assert result.success is False
        assert "not found" in result.error.lower()
    
    def test_ocr_pdf_slice_empty_pages(self):
        """Test OCR with empty page list."""
        client = GLMOCRClient()
        client._available = True
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake pdf")
            temp_path = f.name
        
        try:
            result = client.ocr_pdf_slice(temp_path, [], "test")
            assert result.success is False
            assert "no page numbers" in result.error.lower()
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestGLMOCRFallback:
    """Tests for GLMOCRFallback high-level handler."""
    
    def test_should_fallback_for_ocr_classification(self):
        """Test that OCR classification triggers fallback."""
        fallback = GLMOCRFallback()
        assert fallback.should_fallback("needs_ocr_fallback") is True
    
    def test_should_fallback_for_layout_classification(self):
        """Test that layout classification triggers fallback."""
        fallback = GLMOCRFallback()
        assert fallback.should_fallback("needs_layout_fallback") is True
    
    def test_should_not_fallback_for_deterministic(self):
        """Test that deterministic classification doesn't trigger fallback."""
        fallback = GLMOCRFallback()
        assert fallback.should_fallback("deterministic_ok") is False
    
    def test_process_slice_returns_none_when_not_needed(self):
        """Test that process_slice returns None when fallback not needed."""
        fallback = GLMOCRFallback()
        
        result = fallback.process_slice(
            pdf_path="test.pdf",
            page_numbers=[1, 2],
            routing_classification="deterministic_ok",
            slice_id="test",
        )
        
        assert result is None
    
    def test_process_slice_returns_result_when_needed(self):
        """Test that process_slice runs OCR when fallback is needed."""
        mock_client = Mock()
        mock_client.available = True
        mock_client.ocr_pdf_slice.return_value = GLMOCResult(
            slice_id="test",
            ocr_text="OCR text",
            pages_processed=[1, 2],
        )
        
        fallback = GLMOCRFallback(client=mock_client)
        
        result = fallback.process_slice(
            pdf_path="test.pdf",
            page_numbers=[1, 2],
            routing_classification="needs_ocr_fallback",
            slice_id="test",
        )
        
        assert result is not None
        assert result.success is True
        mock_client.ocr_pdf_slice.assert_called_once()


class TestCreateStorage:
    """Tests for result storage creation."""
    
    def test_storage_includes_both_extractions(self):
        """Test that storage includes both deterministic and OCR results."""
        ocr_result = GLMOCResult(
            slice_id="test",
            ocr_text="OCR extracted text",
            pages_processed=[1, 2],
        )
        deterministic = "Deterministic extraction"
        
        storage = create_glm_ocr_result_storage(ocr_result, deterministic)
        
        assert storage["deterministic_extraction"] == deterministic
        assert storage["ocr_extraction"] == "OCR extracted text"
        assert storage["ocr_success"] is True
        assert storage["comparison"]["det_length"] == len(deterministic)
        assert storage["comparison"]["ocr_length"] == len("OCR extracted text")
    
    def test_storage_handles_failed_ocr(self):
        """Test storage when OCR failed."""
        ocr_result = GLMOCResult(
            slice_id="test",
            error="OCR failed",
            pages_processed=[1, 2],
        )
        deterministic = "Deterministic extraction"
        
        storage = create_glm_ocr_result_storage(ocr_result, deterministic)
        
        assert storage["ocr_extraction"] is None
        assert storage["ocr_success"] is False
        assert storage["ocr_error"] == "OCR failed"
        assert storage["comparison"]["extraction_method"] == "deterministic"


class TestEnvironmentConfiguration:
    """Tests for environment-based configuration."""
    
    def test_custom_host_from_env(self, monkeypatch):
        """Test that OLLAMA_HOST env var is respected."""
        monkeypatch.setenv("OLLAMA_HOST", "http://custom:11434")
        client = GLMOCRClient()
        assert client.host == "http://custom:11434"
    
    def test_custom_model_from_env(self, monkeypatch):
        """Test that GLM_OCR_MODEL env var is respected."""
        monkeypatch.setenv("GLM_OCR_MODEL", "custom-model:latest")
        client = GLMOCRClient()
        assert client.model == "custom-model:latest"
    
    def test_constructor_overrides_env(self, monkeypatch):
        """Test that constructor parameters override env vars."""
        monkeypatch.setenv("OLLAMA_HOST", "http://env-host:11434")
        client = GLMOCRClient(host="http://explicit:11434")
        assert client.host == "http://explicit:11434"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
