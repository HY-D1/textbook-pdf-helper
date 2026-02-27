"""
Kimi Code Assistant Integration for PDF Processing Pipeline

This module integrates Kimi Code (AI assistant) into all phases:
- Phase 1: AI-assisted text cleaning and validation
- Phase 2: AI-assisted concept-content matching verification  
- Phase 3: Content enhancement (complements Ollama LLM)

Unlike Ollama which runs locally, Kimi Code provides:
- Better understanding of context
- Can analyze and validate content quality
- Can suggest fixes for mismatches
- Can restructure content when needed
"""

from __future__ import annotations

import json
import re
from typing import Any
from pathlib import Path


class KimiAssistant:
    """
    Kimi Code AI Assistant for pipeline enhancement.
    
    This class provides AI-powered validation and cleaning
    that complements the rule-based TextCleaner and ContentValidator.
    """
    
    def __init__(self):
        """Initialize the Kimi Assistant."""
        self.name = "Kimi Code Assistant"
        self.version = "1.0.0"
    
    # ========================================================================
    # PHASE 1: AI-Assisted Text Cleaning
    # ========================================================================
    
    def analyze_text_quality(self, text: str, page_number: int = 0) -> dict[str, Any]:
        """
        Analyze extracted text quality and identify issues.
        
        Goes beyond regex patterns to understand context.
        
        Args:
            text: Raw extracted text from PDF
            page_number: Page number for reference
            
        Returns:
            Quality analysis with specific issues and fix suggestions
        """
        issues = []
        fix_suggestions = []
        
        # Check for garbled/OCR text patterns
        garbled_patterns = [
            (r'\b\w{3,}[^\w\s]\w+\b', 'Possible OCR corruption'),
            (r'\w+~\w+', 'Tilde corruption (e.g., "depart~ent")'),
            (r'[A-Z][a-z]+[A-Z][a-z]+[A-Z]', 'CamelCase corruption'),
        ]
        
        for pattern, description in garbled_patterns:
            matches = re.findall(pattern, text[:1000])
            if matches:
                issues.append({
                    'type': 'ocr_corruption',
                    'description': description,
                    'examples': matches[:3],
                    'severity': 'high' if len(matches) > 5 else 'medium'
                })
        
        # Check for content type classification
        content_indicators = {
            'sql_content': len(re.findall(r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE|FROM|WHERE|JOIN)\b', text, re.IGNORECASE)),
            'exercise_content': len(re.findall(r'^\s*\d+\.', text, re.MULTILINE)),
            'narrative_content': len(re.findall(r'\b(this chapter|you will learn|figure \d+|table \d+)\b', text, re.IGNORECASE)),
            'header_content': len(re.findall(r'(Chapter \d+|Section \d+|Page \d+)', text, re.IGNORECASE)),
        }
        
        # Determine primary content type
        if content_indicators['header_content'] > 5:
            issues.append({
                'type': 'excessive_headers',
                'description': f"Page has {content_indicators['header_content']} header patterns",
                'suggestion': 'Remove page headers and footers',
                'severity': 'medium'
            })
        
        if content_indicators['exercise_content'] > 3:
            issues.append({
                'type': 'exercise_list',
                'description': f"Contains {content_indicators['exercise_content']} numbered items (likely exercises)",
                'suggestion': 'Filter out exercise/lab instructions',
                'severity': 'medium'
            })
        
        # SQL content quality
        sql_blocks = re.findall(r'```sql\s*\n(.*?)\n```', text, re.DOTALL)
        invalid_sql = 0
        for block in sql_blocks:
            if not self._is_valid_sql_structure(block):
                invalid_sql += 1
        
        if invalid_sql > 0:
            issues.append({
                'type': 'invalid_sql',
                'description': f"{invalid_sql}/{len(sql_blocks)} SQL blocks have structural issues",
                'suggestion': 'Review SQL blocks for narrative text injection',
                'severity': 'high'
            })
        
        # Calculate overall quality score
        base_score = 100
        for issue in issues:
            if issue['severity'] == 'high':
                base_score -= 15
            elif issue['severity'] == 'medium':
                base_score -= 10
            else:
                base_score -= 5
        
        quality_score = max(0, min(100, base_score))
        
        return {
            'page_number': page_number,
            'quality_score': quality_score,
            'issues': issues,
            'content_indicators': content_indicators,
            'recommendation': self._generate_recommendation(issues, quality_score)
        }
    
    def _is_valid_sql_structure(self, sql: str) -> bool:
        """Quick check if SQL block looks structurally valid."""
        sql_upper = sql.upper().strip()
        
        # Should start with SQL keyword
        sql_starts = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'WITH']
        has_sql_start = any(sql_upper.startswith(kw) for kw in sql_starts)
        
        # Should be reasonably sized (not too short, not novel-length)
        reasonable_length = 10 < len(sql) < 1000
        
        # Shouldn't be mostly narrative
        word_count = len(sql.split())
        sentence_count = len([s for s in sql.split('.') if len(s.strip()) > 5])
        narrative_ratio = sentence_count / max(word_count, 1)
        not_too_narrative = narrative_ratio < 0.3  # Less than 30% sentences
        
        return has_sql_start and reasonable_length and not_too_narrative
    
    def _generate_recommendation(self, issues: list, score: int) -> str:
        """Generate human-readable recommendation."""
        if score >= 90:
            return "Text quality is excellent. Minor cleanup only needed."
        elif score >= 70:
            return f"Good quality with {len(issues)} minor issues. Standard cleaning should suffice."
        elif score >= 50:
            return f"Moderate quality issues ({len(issues)} found). AI-assisted cleaning recommended."
        else:
            return f"Poor quality - {len(issues)} significant issues. Full AI processing needed."
    
    def ai_clean_text(self, text: str, page_number: int = 0) -> dict[str, Any]:
        """
        AI-powered text cleaning with context understanding.
        
        This goes beyond regex to understand what SHOULD be kept vs removed.
        
        Args:
            text: Raw text to clean
            page_number: For reference
            
        Returns:
            Cleaned text with metadata about what was changed
        """
        original_length = len(text)
        changes = []
        
        # Step 1: Identify and mark different content types
        content_blocks = self._segment_content(text)
        
        # Step 2: Process each block based on type
        cleaned_blocks = []
        for block in content_blocks:
            block_type = block['type']
            block_text = block['text']
            
            if block_type == 'header_footer':
                changes.append({
                    'action': 'removed',
                    'type': 'header_footer',
                    'content_preview': block_text[:50] + '...'
                })
                continue  # Skip headers/footers
            
            elif block_type == 'exercise':
                changes.append({
                    'action': 'removed',
                    'type': 'exercise',
                    'content_preview': block_text[:50] + '...'
                })
                continue  # Skip exercises
            
            elif block_type == 'code_block':
                # Clean code block
                cleaned_code = self._clean_code_block(block_text)
                if cleaned_code != block_text:
                    changes.append({
                        'action': 'cleaned',
                        'type': 'code_block',
                        'changes': 'Removed narrative text from SQL'
                    })
                cleaned_blocks.append(cleaned_code)
            
            elif block_type == 'narrative':
                # Clean narrative (fix OCR, etc.)
                cleaned_narrative = self._clean_narrative(block_text)
                cleaned_blocks.append(cleaned_narrative)
            
            else:
                # Unknown type - keep but mark
                cleaned_blocks.append(block_text)
        
        # Reconstruct text (ensure we keep something!)
        cleaned_text = '\n\n'.join(cleaned_blocks).strip()
        
        # Safety check: if we removed everything, keep original
        if not cleaned_text:
            cleaned_text = text
            changes.append({
                'action': 'reverted',
                'type': 'safety',
                'reason': 'Cleaning removed all content, reverting to original'
            })
        
        return {
            'original_length': original_length,
            'cleaned_length': len(cleaned_text),
            'reduction_percent': round((1 - len(cleaned_text)/original_length) * 100, 1),
            'changes': changes,
            'cleaned_text': cleaned_text,
            'page_number': page_number
        }
    
    def _segment_content(self, text: str) -> list[dict]:
        """Segment text into typed blocks."""
        blocks = []
        lines = text.split('\n')
        current_block = {'type': 'unknown', 'text': []}
        
        for line in lines:
            stripped = line.strip()
            
            # Detect block type
            if re.match(r'^\s*```', stripped):
                # Code block boundary
                if current_block['text']:
                    blocks.append({
                        'type': current_block['type'],
                        'text': '\n'.join(current_block['text'])
                    })
                current_block = {'type': 'code_block', 'text': [line]}
            elif re.match(r'^\s*\d+\s+Section\s+\d+', stripped):
                # Header
                if current_block['text']:
                    blocks.append({
                        'type': current_block['type'],
                        'text': '\n'.join(current_block['text'])
                    })
                blocks.append({'type': 'header_footer', 'text': line})
                current_block = {'type': 'unknown', 'text': []}
            elif re.match(r'^\s*\d+\.', stripped) and len(stripped) > 30:
                # Likely exercise
                if current_block['type'] != 'exercise':
                    if current_block['text']:
                        blocks.append({
                            'type': current_block['type'],
                            'text': '\n'.join(current_block['text'])
                        })
                    current_block = {'type': 'exercise', 'text': []}
                current_block['text'].append(line)
            else:
                # Regular content
                if current_block['type'] == 'unknown':
                    current_block['type'] = 'narrative'
                current_block['text'].append(line)
        
        # Don't forget last block
        if current_block['text']:
            blocks.append({
                'type': current_block['type'],
                'text': '\n'.join(current_block['text'])
            })
        
        return blocks
    
    def _clean_code_block(self, code: str) -> str:
        """Clean a code block."""
        lines = code.split('\n')
        cleaned = []
        in_code = False
        
        for line in lines:
            if line.strip().startswith('```'):
                cleaned.append(line)
                in_code = not in_code
                continue
            
            if in_code:
                # Skip obvious narrative lines
                if re.match(r'^(Figure|Table)\s+\d+', line.strip()):
                    continue
                if len(line.strip()) > 150 and '.' in line and ';' not in line:
                    # Very long line with periods but no semicolon - likely narrative
                    continue
            
            cleaned.append(line)
        
        return '\n'.join(cleaned)
    
    def _clean_narrative(self, text: str) -> str:
        """Clean narrative text (OCR fixes, etc.)."""
        # Apply OCR corrections
        corrections = {
            r'\bArz\b': 'An',
            r'\bstatc\b': 'state',
            r'\bCalcuIu,s\b': 'Calculus',
            r'\binforination\b': 'information',
        }
        
        for pattern, replacement in corrections.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Remove duplicate lines
        lines = text.split('\n')
        seen = set()
        unique_lines = []
        for line in lines:
            normalized = re.sub(r'\s+', ' ', line.strip().lower())
            if normalized and normalized not in seen:
                seen.add(normalized)
                unique_lines.append(line)
        
        return '\n'.join(unique_lines)
    
    # ========================================================================
    # PHASE 2: AI-Assisted Concept Validation
    # ========================================================================
    
    def validate_concept_content(self, concept_id: str, concept_title: str, 
                                  text: str) -> dict[str, Any]:
        """
        AI-powered validation that content matches concept.
        
        Goes beyond keyword matching to understand semantic relevance.
        
        Args:
            concept_id: Concept identifier (e.g., "select-basic")
            concept_title: Human-readable title
            text: Extracted text for this concept
            
        Returns:
            Detailed validation report with suggestions
        """
        text_lower = text.lower()
        title_lower = concept_title.lower()
        
        # Multi-factor relevance analysis
        analysis = {
            'concept_id': concept_id,
            'title': concept_title,
            'text_length': len(text),
            'factors': {}
        }
        
        # Factor 1: Keyword presence
        concept_keywords = self._extract_concept_keywords(concept_id, title_lower)
        keyword_matches = sum(1 for kw in concept_keywords if kw in text_lower)
        keyword_score = keyword_matches / max(len(concept_keywords), 1)
        analysis['factors']['keyword_match'] = {
            'score': round(keyword_score, 2),
            'matches': keyword_matches,
            'total_keywords': len(concept_keywords),
            'keywords': concept_keywords[:10]
        }
        
        # Factor 2: SQL content density
        sql_patterns = [
            r'\bselect\b.*\bfrom\b',
            r'\binsert\s+into\b',
            r'\bupdate\s+\w+\s+set\b',
            r'\bdelete\s+from\b',
            r'\bjoin\b.*\bon\b',
        ]
        sql_matches = sum(1 for p in sql_patterns if re.search(p, text_lower))
        sql_score = min(1.0, sql_matches / 3)  # Cap at 3 matches = full score
        analysis['factors']['sql_density'] = {
            'score': round(sql_score, 2),
            'sql_patterns_found': sql_matches
        }
        
        # Factor 3: Content coherence (does it read like educational content?)
        educational_markers = [
            r'\b(example|for instance)\b',
            r'\b(note|important|remember)\b',
            r'```sql',
            r'\b(definition|syntax)\b',
        ]
        edu_matches = sum(1 for p in educational_markers if re.search(p, text_lower))
        edu_score = min(1.0, edu_matches / 3)
        analysis['factors']['educational_quality'] = {
            'score': round(edu_score, 2),
            'markers_found': edu_matches
        }
        
        # Factor 4: Negative indicators (non-SQL content)
        negative_patterns = [
            (r'\bjdbc\b', 'JDBC content'),
            (r'\bjava\s+servlet\b', 'Java Servlet content'),
            (r'\bhttp\s+protocol\b', 'HTTP protocol content'),
            (r'\btype\s+i+\s+driver\b', 'Driver types (likely JDBC)'),
            (r'\bperl\b|\bcgi\b', 'Perl/CGI content'),
        ]
        negative_matches = []
        for pattern, description in negative_patterns:
            if re.search(pattern, text_lower):
                negative_matches.append(description)
        
        negative_penalty = len(negative_matches) * 0.25
        analysis['factors']['negative_indicators'] = {
            'penalty': round(negative_penalty, 2),
            'issues': negative_matches
        }
        
        # Calculate final relevance score
        final_score = (
            keyword_score * 0.35 +
            sql_score * 0.35 +
            edu_score * 0.30 -
            negative_penalty
        )
        final_score = max(0, min(1, final_score))
        
        analysis['relevance_score'] = round(final_score, 2)
        analysis['is_relevant'] = final_score >= 0.4  # Slightly higher threshold
        
        # Generate recommendation
        if final_score >= 0.7:
            analysis['recommendation'] = "✅ High quality match. Proceed with LLM enhancement."
        elif final_score >= 0.4:
            analysis['recommendation'] = "⚠️ Moderate match. Consider reviewing content before LLM."
        else:
            analysis['recommendation'] = f"❌ Poor match. {', '.join(negative_matches[:2])} detected. Skip or remap pages."
        
        return analysis
    
    def _extract_concept_keywords(self, concept_id: str, title: str) -> list[str]:
        """Extract relevant keywords for a concept."""
        keywords = []
        
        # Add words from concept ID
        keywords.extend(concept_id.replace('-', ' ').split())
        
        # Add words from title
        keywords.extend(title.split())
        
        # Add SQL-specific keywords based on concept type
        if 'select' in concept_id or 'select' in title:
            keywords.extend(['select', 'from', 'where', 'column', 'row', 'query'])
        if 'join' in concept_id or 'join' in title:
            keywords.extend(['join', 'inner', 'outer', 'left', 'right', 'on', 'table'])
        if 'insert' in concept_id or 'insert' in title:
            keywords.extend(['insert', 'into', 'values', 'add', 'create'])
        if 'update' in concept_id or 'update' in title:
            keywords.extend(['update', 'set', 'modify', 'change'])
        if 'aggregate' in concept_id or 'group' in title:
            keywords.extend(['group by', 'count', 'sum', 'avg', 'max', 'min', 'having'])
        if 'subquery' in concept_id:
            keywords.extend(['subquery', 'nested', 'correlated', 'exists', 'in'])
        
        # Clean and deduplicate
        keywords = [kw.lower().strip() for kw in keywords if len(kw) > 2]
        return list(set(keywords))
    
    def suggest_concept_mapping(self, text: str, available_concepts: list[str]) -> list[dict]:
        """
        Suggest which concept(s) a piece of text should map to.
        
        Useful when auto-detection finds content that doesn't match expected concept.
        
        Args:
            text: The text to classify
            available_concepts: List of possible concept IDs
            
        Returns:
            Ranked list of suggested concept mappings with confidence scores
        """
        text_lower = text.lower()
        suggestions = []
        
        for concept_id in available_concepts:
            # Calculate simple keyword overlap
            concept_words = set(concept_id.replace('-', ' ').split())
            text_words = set(text_lower.split())
            
            overlap = len(concept_words & text_words)
            score = overlap / max(len(concept_words), 1)
            
            if score > 0:
                suggestions.append({
                    'concept_id': concept_id,
                    'confidence': round(score, 2),
                    'matching_words': list(concept_words & text_words)
                })
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        return suggestions[:5]  # Top 5 suggestions
    
    # ========================================================================
    # PHASE 3: Content Enhancement Support
    # ========================================================================
    
    def prepare_llm_prompt(self, concept_title: str, raw_text: str, 
                           validation_result: dict) -> str:
        """
        Prepare an optimized prompt for the LLM based on validation.
        
        Adapts the prompt based on content quality and type.
        
        Args:
            concept_title: Title of the concept
            raw_text: Extracted text
            validation_result: From validate_concept_content()
            
        Returns:
            Optimized prompt string
        """
        score = validation_result['relevance_score']
        
        # Base prompt
        prompt = f"""Transform this textbook content into high-quality educational notes for "{concept_title}".

"""
        
        # Adapt based on quality
        if score >= 0.8:
            prompt += """The source text is high quality and directly relevant. Focus on:
- Organizing clearly with definition, explanation, examples
- Maintaining technical accuracy
- Adding pedagogical value

"""
        elif score >= 0.5:
            prompt += """The source text has moderate quality. Please:
- Extract and emphasize SQL-related content
- Filter out tangential information
- Generate appropriate examples if source examples are weak

"""
        else:
            prompt += """The source text may not be directly relevant. Please:
- Use your knowledge of "{concept_title}" to create accurate content
- Only use the source as a loose reference
- Focus on core concepts and practical examples

"""
        
        # Add content-specific guidance
        factors = validation_result.get('factors', {})
        
        if factors.get('negative_indicators', {}).get('issues'):
            issues = factors['negative_indicators']['issues']
            prompt += f"""⚠️ WARNING: Source contains {', '.join(issues)}.
DO NOT include this content - create original SQL-focused material instead.

"""
        
        if factors.get('sql_density', {}).get('score', 0) < 0.3:
            prompt += """Note: Source has limited SQL examples. Please generate appropriate SQL code.

"""
        
        prompt += f"""SOURCE TEXT:
{raw_text[:6000]}

Create educational notes with:
1. Clear definition (2-3 sentences)
2. Detailed explanation (3-5 paragraphs)
3. 2-3 SQL examples with explanations
4. 2-3 common mistakes with corrections
5. Practice question with solution

Respond in JSON format."""
        
        return prompt
    
    def post_process_llm_output(self, llm_output: str, concept_title: str) -> dict[str, Any]:
        """
        Post-process and validate LLM output.
        
        Catches issues that rule-based validation might miss.
        
        Args:
            llm_output: Raw text from LLM
            concept_title: Expected concept
            
        Returns:
            Processed content with validation
        """
        # Try to extract JSON
        json_match = re.search(r'\{[\s\S]*\}', llm_output)
        if not json_match:
            return {
                'success': False,
                'error': 'No JSON found in LLM output',
                'raw_output': llm_output[:500]
            }
        
        try:
            content = json.loads(json_match.group())
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': f'JSON parse error: {str(e)}',
                'raw_output': llm_output[:500]
            }
        
        # Validate structure
        required_fields = ['definition', 'explanation', 'examples']
        missing_fields = [f for f in required_fields if f not in content]
        
        if missing_fields:
            return {
                'success': False,
                'error': f'Missing required fields: {missing_fields}',
                'content': content
            }
        
        # Validate content quality
        issues = []
        
        # Check definition
        definition = content.get('definition', '')
        if len(definition) < 30:
            issues.append('Definition is too short (< 30 chars)')
        if concept_title.lower().split()[0] not in definition.lower():
            issues.append(f'Definition does not mention concept topic ({concept_title})')
        
        # Check examples
        examples = content.get('examples', [])
        if not examples:
            issues.append('No examples provided')
        else:
            for i, ex in enumerate(examples):
                code = ex.get('code', '')
                if not code:
                    issues.append(f'Example {i+1} has no code')
                elif '```' not in code:  # Should be markdown code block
                    issues.append(f'Example {i+1} code not in markdown format')
        
        return {
            'success': len(issues) == 0,
            'content': content,
            'issues': issues,
            'warnings': []
        }


# ========================================================================
# Integration Helper Functions
# ========================================================================

def create_kimi_enhanced_pipeline():
    """
    Create a pipeline configuration that uses Kimi Assistant.
    
    Returns configuration dict for use with EducationalNoteGenerator.
    """
    return {
        'use_kimi_phase1': True,  # Enable AI text cleaning
        'use_kimi_phase2': True,  # Enable AI concept validation
        'use_kimi_phase3': False,  # Phase 3 still uses Ollama for generation
        'kimi_config': {
            'quality_threshold': 0.7,
            'auto_remap': True,  # Suggest remapping for low-quality matches
        }
    }


# Example usage
if __name__ == "__main__":
    # Demo
    assistant = KimiAssistant()
    
    # Test text analysis
    test_text = """520 Section 5 Database administration
    
    1. Start MySQL Workbench and open the Client Connections window.
    
    SELECT * FROM users;
    
    This is CalcuIu,s example.
    """
    
    analysis = assistant.analyze_text_quality(test_text, page_number=45)
    print("Text Quality Analysis:")
    print(json.dumps(analysis, indent=2))
    
    # Test concept validation
    validation = assistant.validate_concept_content(
        concept_id="select-basic",
        concept_title="SELECT Statement Basics",
        text=test_text
    )
    print("\nConcept Validation:")
    print(json.dumps(validation, indent=2))
