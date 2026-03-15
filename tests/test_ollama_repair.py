"""
Unit tests for structured Ollama repair.

Tests cover:
- Valid structured repair acceptance
- Malformed/incomplete repair rejection
- Safe fallback when parsing fails
- Schema validation
- Repair result handling
"""

from __future__ import annotations

import json
from unittest.mock import Mock, patch

import pytest

from algl_pdf_helper.ollama_repair import (
    OllamaRepair,
    RepairResult,
    RepairCache,
    RECOMMENDED_REPAIR_MODEL,
    REPAIR_PROMPT_VERSION,
)

try:
    from algl_pdf_helper.ollama_repair import StructuredL3Repair, ExampleRepair, HAS_PYDANTIC
except ImportError:
    HAS_PYDANTIC = False
    StructuredL3Repair = None
    ExampleRepair = None


class TestRepairResult:
    """Tests for RepairResult dataclass."""
    
    def test_get_content_to_use_returns_repaired_when_accepted(self):
        """Test that repaired content is returned when accepted."""
        original = {"definition": "Weak def"}
        repaired = {"definition": "Strong definition"}
        
        result = RepairResult(
            repair_accepted=True,
            original_content=original,
            repaired_content=repaired,
        )
        
        assert result.get_content_to_use() == repaired
    
    def test_get_content_to_use_returns_original_when_rejected(self):
        """Test that original content is returned when repair rejected."""
        original = {"definition": "Original def"}
        
        result = RepairResult(
            repair_accepted=False,
            original_content=original,
            error="Validation failed",
        )
        
        assert result.get_content_to_use() == original
    
    def test_get_content_to_use_returns_original_when_no_repair(self):
        """Test fallback to original when no repaired content."""
        original = {"definition": "Original def"}
        
        result = RepairResult(
            repair_accepted=True,  # Shouldn't happen but test safety
            original_content=original,
            repaired_content=None,
        )
        
        assert result.get_content_to_use() == original
    
    def test_to_dict_serializes_correctly(self):
        """Test serialization to dictionary."""
        result = RepairResult(
            repair_accepted=True,
            original_content={"def": "orig"},
            repaired_content={"def": "fixed"},
            model_used="qwen3.5:9b",
            repair_metadata={"confidence": 0.9},
        )
        
        data = result.to_dict()
        assert data["repair_accepted"] is True
        assert data["model_used"] == "qwen3.5:9b"
        assert data["repair_metadata"]["confidence"] == 0.9


class TestOllamaRepairAvailability:
    """Tests for availability checking."""
    
    def test_available_when_ollama_running(self):
        """Test availability when Ollama is running."""
        mock_response = {"models": [{"name": "qwen3.5:9b"}]}
        
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_cm = Mock()
            mock_cm.__enter__ = Mock(return_value=Mock(
                status=200,
                read=Mock(return_value=json.dumps(mock_response).encode())
            ))
            mock_cm.__exit__ = Mock(return_value=False)
            mock_urlopen.return_value = mock_cm
            
            repair = OllamaRepair()
            assert repair.available is True
    
    def test_not_available_when_ollama_down(self):
        """Test availability when Ollama is not running."""
        with patch('urllib.request.urlopen') as mock_urlopen:
            from urllib.error import URLError
            mock_urlopen.side_effect = URLError("Connection refused")
            
            repair = OllamaRepair()
            assert repair.available is False


class TestStructuredRepair:
    """Tests for structured repair functionality."""
    
    def test_repair_when_ollama_unavailable(self):
        """Test that unavailable Ollama returns safe fallback."""
        repair = OllamaRepair()
        repair._available = False
        
        result = repair.repair_l3_content_structured(
            concept_id="joins",
            weak_content={"definition": "Weak"},
            source_evidence="Evidence text",
        )
        
        assert result.repair_accepted is False
        assert result.error == "Ollama not available"
        assert result.get_content_to_use()["concept_id"] == "joins"
    
    def test_valid_structured_response_accepted(self):
        """Test that valid structured JSON is accepted."""
        if not HAS_PYDANTIC:
            pytest.skip("Pydantic not available")
        
        valid_response = json.dumps({
            "definition": "A JOIN combines rows from two or more tables based on related columns.",
            "why_it_matters": "JOINs are essential for querying normalized databases.",
            "explanation": "When data is normalized across tables, JOINs reconstruct relationships.",
            "confidence_score": 0.85,
            "uses_only_source_evidence": True,
            "repair_reasons": ["improved_definition"],
        })
        
        repair = OllamaRepair()
        repair._available = True
        repair.model = "qwen3.5:9b"
        
        with patch.object(repair, '_call_ollama_structured', return_value=valid_response):
            result = repair.repair_l3_content_structured(
                concept_id="joins",
                weak_content={"definition": "Weak"},
                source_evidence="Evidence",
            )
            
            assert result.repair_accepted is True
            assert result.repaired_content is not None
            assert result.repaired_content["definition"] == "A JOIN combines rows from two or more tables based on related columns."
            assert result.repair_metadata.get("confidence") == 0.85
    
    def test_malformed_json_rejected_safely(self):
        """Test that malformed JSON is rejected with safe fallback."""
        if not HAS_PYDANTIC:
            pytest.skip("Pydantic not available")
        
        malformed_response = "This is not JSON { invalid"
        
        repair = OllamaRepair()
        repair._available = True
        
        with patch.object(repair, '_call_ollama_structured', return_value=malformed_response):
            result = repair.repair_l3_content_structured(
                concept_id="joins",
                weak_content={"definition": "Original"},
                source_evidence="Evidence",
            )
            
            assert result.repair_accepted is False
            assert result.error == "Failed to parse structured response"
            assert result.get_content_to_use()["definition"] == "Original"
    
    def test_incomplete_schema_rejected(self):
        """Test that incomplete schema (missing required fields) is rejected."""
        if not HAS_PYDANTIC:
            pytest.skip("Pydantic not available")
        
        # Missing required 'why_it_matters'
        incomplete_response = json.dumps({
            "definition": "A JOIN combines tables.",
            # why_it_matters missing
            "confidence_score": 0.5,
        })
        
        repair = OllamaRepair()
        repair._available = True
        
        with patch.object(repair, '_call_ollama_structured', return_value=incomplete_response):
            result = repair.repair_l3_content_structured(
                concept_id="joins",
                weak_content={"definition": "Original"},
                source_evidence="Evidence",
            )
            
            assert result.repair_accepted is False
            assert "validation" in result.error.lower() or "parse" in result.error.lower()
    
    def test_short_definition_rejected(self):
        """Test that too-short definition fails validation."""
        if not HAS_PYDANTIC:
            pytest.skip("Pydantic not available")
        
        short_response = json.dumps({
            "definition": "Short",  # Less than 20 chars
            "why_it_matters": "This is important for students to understand properly.",
            "confidence_score": 0.5,
        })
        
        repair = OllamaRepair()
        repair._available = True
        
        with patch.object(repair, '_call_ollama_structured', return_value=short_response):
            result = repair.repair_l3_content_structured(
                concept_id="joins",
                weak_content={"definition": "Original"},
                source_evidence="Evidence",
            )
            
            assert result.repair_accepted is False


class TestStructuredL3RepairSchema:
    """Tests for Pydantic schema validation."""
    
    def test_valid_repair_object_creation(self):
        """Test creating valid StructuredL3Repair object."""
        if not HAS_PYDANTIC:
            pytest.skip("Pydantic not available")
        
        repair = StructuredL3Repair(
            definition="A clear definition of the SQL concept.",
            why_it_matters="This matters because it helps students.",
            confidence_score=0.85,
        )
        
        assert repair.definition == "A clear definition of the SQL concept."
        assert repair.confidence_score == 0.85
    
    def test_confidence_score_validation(self):
        """Test that confidence score must be 0.0-1.0."""
        if not HAS_PYDANTIC:
            pytest.skip("Pydantic not available")
        
        with pytest.raises(Exception):  # ValidationError
            StructuredL3Repair(
                definition="Valid definition here",
                why_it_matters="Valid why it matters",
                confidence_score=1.5,  # Invalid
            )
    
    def test_example_repair_nested(self):
        """Test nested ExampleRepair schema."""
        if not HAS_PYDANTIC:
            pytest.skip("Pydantic not available")
        
        example = ExampleRepair(
            original_example="SELECT * FROM a",
            repaired_example="SELECT * FROM customers",
            example_valid=True,
        )
        
        repair = StructuredL3Repair(
            definition="A clear and detailed definition of the SQL concept",
            why_it_matters="This matters because it helps students understand",
            example_repairs=[example],
        )
        
        assert len(repair.example_repairs) == 1
        assert repair.example_repairs[0].original_example == "SELECT * FROM a"


class TestRepairCache:
    """Tests for repair caching."""
    
    def test_cache_hit_returns_cached_content(self):
        """Test that cache hit returns cached repair."""
        cache = RepairCache()
        
        # Mock cache file
        cached_content = {"definition": "Cached definition"}
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open := Mock()):
                mock_open.return_value.__enter__ = Mock(return_value=Mock(
                    read=Mock(return_value=json.dumps(cached_content))
                ))
                mock_open.return_value.__exit__ = Mock(return_value=False)
                
                result = cache.get_cached_repair(
                    "joins", "L3", "qwen3.5:9b", "abc123", "v1.0"
                )
                
                assert result is not None
                assert result["definition"] == "Cached definition"
    
    def test_cache_miss_returns_none(self):
        """Test that cache miss returns None."""
        cache = RepairCache()
        
        with patch('pathlib.Path.exists', return_value=False):
            result = cache.get_cached_repair(
                "joins", "L3", "qwen3.5:9b", "abc123", "v1.0"
            )
            
            assert result is None


class TestFactoryFunction:
    """Tests for create_ollama_repair_if_enabled."""
    
    def test_returns_none_when_disabled(self):
        """Test factory returns None when repair disabled."""
        from algl_pdf_helper.ollama_repair import create_ollama_repair_if_enabled
        
        repair, status = create_ollama_repair_if_enabled(enabled=False)
        
        assert repair is None
        assert status["enabled"] is False
    
    def test_returns_repair_when_enabled_and_available(self):
        """Test factory returns repair instance when enabled and available."""
        from algl_pdf_helper.ollama_repair import create_ollama_repair_if_enabled
        
        with patch('algl_pdf_helper.ollama_repair.OllamaRepair') as MockRepair:
            mock_instance = Mock()
            mock_instance.available = True
            mock_instance.model = "qwen3.5:9b"
            MockRepair.return_value = mock_instance
            
            repair, status = create_ollama_repair_if_enabled(enabled=True)
            
            assert repair is not None
            assert status["enabled"] is True
            assert status["available"] is True


class TestRecommendedModel:
    """Tests that recommended model is configured correctly."""
    
    def test_recommended_model_is_qwen35_9b(self):
        """Test that RECOMMENDED_REPAIR_MODEL is qwen3.5:9b."""
        assert RECOMMENDED_REPAIR_MODEL == "qwen3.5:9b"
    
    def test_recommended_model_in_preferred_list(self):
        """Test that recommended model is first in preferred list."""
        from algl_pdf_helper.ollama_repair import PREFERRED_MODELS
        assert PREFERRED_MODELS[0] == "qwen3.5:9b"
    
    def test_model_config_exists_for_recommended(self):
        """Test that model config exists for recommended model."""
        from algl_pdf_helper.ollama_repair import MODEL_CONFIGS
        assert "qwen3.5:9b" in MODEL_CONFIGS
        assert MODEL_CONFIGS["qwen3.5:9b"]["temperature"] == 0.1


class TestLegacyCompatibility:
    """Tests for backwards compatibility."""
    
    def test_legacy_repair_method_calls_structured(self):
        """Test that legacy repair_l3_content calls structured repair."""
        if not HAS_PYDANTIC:
            pytest.skip("Pydantic not available")
        
        valid_response = json.dumps({
            "definition": "A JOIN combines rows from tables.",
            "why_it_matters": "Important for database queries.",
            "confidence_score": 0.8,
        })
        
        repair = OllamaRepair()
        repair._available = True
        repair.model = "qwen3.5:9b"
        
        with patch.object(repair, '_call_ollama_structured', return_value=valid_response):
            result = repair.repair_l3_content(
                concept_id="joins",
                weak_content={"definition": "Weak"},
                source_evidence="Evidence",
            )
            
            assert result is not None
            assert result["definition"] == "A JOIN combines rows from tables."
            assert result["_repaired_by_ollama"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
