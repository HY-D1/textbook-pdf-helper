"""
GLM-OCR Client for ALGL PDF Helper.

This module provides OCR capabilities using the GLM-OCR model via local Ollama.
It is designed as a fallback path when deterministic extraction fails.

Usage:
    from algl_pdf_helper.glm_ocr_client import GLMOCRClient
    
    client = GLMOCRClient()
    if client.available:
        result = client.ocr_pdf_slice(
            pdf_path="textbook.pdf",
            page_numbers=[1, 2, 3],
            slice_id="pages_1_3"
        )
        print(result.ocr_text)

Environment:
    OLLAMA_HOST: Ollama API host (default: http://localhost:11434)
    GLM_OCR_MODEL: Model name (default: glm-ocr:latest)
"""

from __future__ import annotations

import base64
import json
import logging
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF


logger = logging.getLogger(__name__)


@dataclass
class GLMOCResult:
    """Result of GLM-OCR processing.
    
    Attributes:
        slice_id: Identifier for the processed slice
        ocr_text: Extracted text from OCR
        pages_processed: List of page numbers that were processed
        confidence: Optional confidence score if available
        error: Error message if processing failed
        model_used: Name of the Ollama model used
    """
    slice_id: str
    ocr_text: str = ""
    pages_processed: list[int] = None
    confidence: float | None = None
    error: str | None = None
    model_used: str = "glm-ocr:latest"
    
    def __post_init__(self):
        if self.pages_processed is None:
            self.pages_processed = []
    
    @property
    def success(self) -> bool:
        """Check if OCR was successful."""
        return self.error is None and len(self.ocr_text) > 0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "slice_id": self.slice_id,
            "ocr_text": self.ocr_text[:1000] + "..." if len(self.ocr_text) > 1000 else self.ocr_text,
            "ocr_text_length": len(self.ocr_text),
            "pages_processed": self.pages_processed,
            "confidence": self.confidence,
            "error": self.error,
            "model_used": self.model_used,
            "success": self.success,
        }


class GLMOCRClient:
    """
    Client for GLM-OCR via Ollama.
    
    Provides OCR capabilities using the GLM-OCR vision model running locally
    through Ollama. Designed as a fallback when deterministic extraction fails.
    
    The client:
    - Converts PDF pages to base64-encoded images
    - Sends them to GLM-OCR via Ollama API
    - Returns extracted text
    - Handles errors gracefully
    
    Example:
        >>> client = GLMOCRClient()
        >>> if client.available:
        ...     result = client.ocr_pdf_slice(
        ...         pdf_path="textbook.pdf",
        ...         page_numbers=[5, 6, 7]
        ...     )
        ...     if result.success:
        ...         print(f"OCR extracted {len(result.ocr_text)} chars")
    """
    
    DEFAULT_HOST = "http://localhost:11434"
    DEFAULT_MODEL = "glm-ocr:latest"
    DEFAULT_TIMEOUT = 120  # seconds - OCR can be slow
    
    # GLM-OCR supports large context (131K), so we can process multiple pages
    MAX_PAGES_PER_BATCH = 1  # Reduced to 1 to avoid memory issues with local Ollama
    
    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        """
        Initialize the GLM-OCR client.
        
        Args:
            host: Ollama API host URL (defaults to OLLAMA_HOST env var or localhost)
            model: Model name (defaults to GLM_OCR_MODEL env var or glm-ocr:latest)
            timeout: Request timeout in seconds
        """
        import os
        
        self.host = (host or os.environ.get("OLLAMA_HOST", self.DEFAULT_HOST)).rstrip("/")
        self.model = model or os.environ.get("GLM_OCR_MODEL", self.DEFAULT_MODEL)
        self.timeout = timeout
        self._available: bool | None = None
    
    @property
    def available(self) -> bool:
        """Check if GLM-OCR is available via Ollama."""
        if self._available is None:
            self._available = self._check_availability()
        return self._available
    
    def _check_availability(self) -> bool:
        """Check if Ollama is running and GLM-OCR model is available."""
        try:
            req = urllib.request.Request(
                f"{self.host}/api/tags",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    models = data.get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    
                    # Check for our model
                    if self.model in model_names:
                        logger.info(f"GLM-OCR model '{self.model}' is available")
                        return True
                    else:
                        logger.warning(
                            f"GLM-OCR model '{self.model}' not found in Ollama. "
                            f"Available models: {model_names}"
                        )
                        return False
        except urllib.error.URLError as e:
            logger.debug(f"Ollama not available at {self.host}: {e}")
        except Exception as e:
            logger.debug(f"Error checking Ollama availability: {e}")
        
        return False
    
    def ocr_pdf_slice(
        self,
        pdf_path: Path | str,
        page_numbers: list[int],
        slice_id: str = "unknown",
    ) -> GLMOCResult:
        """
        OCR a slice of PDF pages using GLM-OCR.
        
        Converts specified pages to images and processes them through
        the GLM-OCR model.
        
        Args:
            pdf_path: Path to the PDF file
            page_numbers: List of page numbers to OCR (1-based)
            slice_id: Identifier for this slice
            
        Returns:
            GLMOCResult with extracted text or error information
        """
        pdf_path = Path(pdf_path)
        
        if not self.available:
            return GLMOCResult(
                slice_id=slice_id,
                error="GLM-OCR not available. Ensure Ollama is running and glm-ocr:latest is pulled.",
                pages_processed=page_numbers,
            )
        
        if not pdf_path.exists():
            return GLMOCResult(
                slice_id=slice_id,
                error=f"PDF file not found: {pdf_path}",
                pages_processed=page_numbers,
            )
        
        if not page_numbers:
            return GLMOCResult(
                slice_id=slice_id,
                error="No page numbers specified",
                pages_processed=[],
            )
        
        try:
            # Process pages in batches to avoid overwhelming the model
            all_text_parts = []
            
            for batch_start in range(0, len(page_numbers), self.MAX_PAGES_PER_BATCH):
                batch = page_numbers[batch_start:batch_start + self.MAX_PAGES_PER_BATCH]
                batch_text = self._ocr_batch(pdf_path, batch, slice_id)
                all_text_parts.append(batch_text)
            
            full_text = "\n\n".join(filter(None, all_text_parts))
            
            return GLMOCResult(
                slice_id=slice_id,
                ocr_text=full_text,
                pages_processed=page_numbers,
                model_used=self.model,
            )
            
        except Exception as e:
            logger.exception(f"GLM-OCR failed for slice {slice_id}")
            return GLMOCResult(
                slice_id=slice_id,
                error=str(e),
                pages_processed=page_numbers,
                model_used=self.model,
            )
    
    def _ocr_batch(
        self,
        pdf_path: Path,
        page_numbers: list[int],
        slice_id: str,
    ) -> str:
        """
        OCR a batch of pages.
        
        Args:
            pdf_path: Path to PDF
            page_numbers: List of page numbers (1-based, max MAX_PAGES_PER_BATCH)
            slice_id: Slice identifier for logging
            
        Returns:
            Extracted text from the batch
        """
        # Convert pages to base64 images
        images_base64 = []
        
        with fitz.open(pdf_path) as doc:
            for page_num in page_numbers:
                if page_num < 1 or page_num > len(doc):
                    logger.warning(f"Page {page_num} out of range in {pdf_path}")
                    continue
                
                page = doc.load_page(page_num - 1)  # 0-based indexing
                
                # Render page to image (reasonable resolution for OCR)
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))  # 1.5x zoom to reduce memory
                img_data = pix.tobytes("png")
                img_b64 = base64.b64encode(img_data).decode("utf-8")
                images_base64.append(img_b64)
        
        if not images_base64:
            return ""
        
        # Build prompt for OCR
        prompt = self._build_ocr_prompt(len(page_numbers))
        
        # Call Ollama API
        return self._call_ollama_vision(prompt, images_base64)
    
    def _build_ocr_prompt(self, num_pages: int) -> str:
        """Build the OCR prompt for GLM-OCR."""
        return (
            f"Extract all text content from the provided {num_pages} page(s). "
            "Preserve the original layout and formatting as much as possible. "
            "Include all visible text, including headers, footers, body text, "
            "and any tables or code blocks. Output only the extracted text."
        )
    
    def _call_ollama_vision(self, prompt: str, images_base64: list[str]) -> str:
        """
        Call Ollama vision API.
        
        Args:
            prompt: Text prompt
            images_base64: List of base64-encoded images
            
        Returns:
            Model response text
        """
        data = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "images": images_base64,
            "stream": False,
            "options": {
                "temperature": 0.0,  # Deterministic for OCR
                "num_predict": 8000,  # Generous limit for long documents
            }
        }).encode("utf-8")
        
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("response", "")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            raise RuntimeError(f"Ollama API error: {e.code} - {error_body}")
        except Exception as e:
            raise RuntimeError(f"Failed to call Ollama API: {e}")


class GLMOCRFallback:
    """
    High-level fallback handler for GLM-OCR integration.
    
    Coordinates between the fallback router and the GLM-OCR client,
    managing the fallback extraction workflow.
    
    Example:
        >>> fallback = GLMOCRFallback()
        >>> result = fallback.process_slice(
        ...     pdf_path="textbook.pdf",
        ...     routing_decision=decision,
        ...     original_extraction="..."
        ... )
    """
    
    def __init__(self, client: GLMOCRClient | None = None):
        """
        Initialize the fallback handler.
        
        Args:
            client: Optional GLMOCRClient instance (creates default if None)
        """
        self.client = client or GLMOCRClient()
    
    def should_fallback(self, routing_classification: str) -> bool:
        """Check if the routing classification requires OCR fallback."""
        return routing_classification in ("needs_ocr_fallback", "needs_layout_fallback")
    
    def process_slice(
        self,
        pdf_path: Path | str,
        page_numbers: list[int],
        routing_classification: str,
        slice_id: str = "unknown",
    ) -> GLMOCResult | None:
        """
        Process a slice through GLM-OCR if fallback is needed.
        
        Args:
            pdf_path: Path to PDF
            page_numbers: Pages to process
            routing_classification: Classification from fallback router
            slice_id: Slice identifier
            
        Returns:
            GLMOCResult if fallback was performed, None if not needed
        """
        if not self.should_fallback(routing_classification):
            return None
        
        if not self.client.available:
            logger.warning("GLM-OCR fallback requested but client not available")
            return GLMOCResult(
                slice_id=slice_id,
                error="GLM-OCR not available",
                pages_processed=page_numbers,
            )
        
        logger.info(f"Running GLM-OCR fallback for slice {slice_id}")
        return self.client.ocr_pdf_slice(pdf_path, page_numbers, slice_id)


def create_glm_ocr_result_storage(
    ocr_result: GLMOCResult,
    deterministic_extraction: str,
) -> dict[str, Any]:
    """
    Create a storage structure that keeps both deterministic and OCR results.
    
    This allows comparison and selection between extraction methods.
    
    Args:
        ocr_result: Result from GLM-OCR
        deterministic_extraction: Text from deterministic extraction
        
    Returns:
        Dictionary with both results and metadata
    """
    return {
        "deterministic_extraction": deterministic_extraction,
        "ocr_extraction": ocr_result.ocr_text if ocr_result.success else None,
        "ocr_success": ocr_result.success,
        "ocr_error": ocr_result.error,
        "ocr_model": ocr_result.model_used,
        "ocr_pages": ocr_result.pages_processed,
        "comparison": {
            "det_length": len(deterministic_extraction),
            "ocr_length": len(ocr_result.ocr_text) if ocr_result.success else 0,
            "extraction_method": "ocr" if ocr_result.success else "deterministic",
        }
    }
