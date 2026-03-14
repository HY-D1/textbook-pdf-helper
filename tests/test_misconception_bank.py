"""Tests for the misconception bank module."""

import pytest


class TestMisconceptionBankPrereqValidation:
    """Tests for validating prerequisite references in the misconception bank."""

    def test_all_prereq_references_valid(self):
        """Ensure all prerequisite references in misconception bank are valid."""
        from algl_pdf_helper.sql_ontology import ConceptOntology
        from algl_pdf_helper.misconception_bank import COMMON_MISCONCEPTIONS
        
        ontology = ConceptOntology()
        
        for pattern in COMMON_MISCONCEPTIONS:
            if pattern.likely_prereq_failure:
                assert ontology.validate_concept_id(pattern.likely_prereq_failure), \
                    f"Invalid prereq reference: {pattern.likely_prereq_failure} in {pattern.pattern_id}"
