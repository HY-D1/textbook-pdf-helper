"""
End-to-end pipeline: PDF → Educational Notes → SQL-Adapt Format

This module provides a complete solution that:
1. Extracts PDF content using Marker (high quality)
2. Generates educational notes using LLM
3. Outputs SQL-Adapt compatible format
4. Handles all errors gracefully - no exceptions

PHASE 1: PDF Processing - Clean extraction, OCR correction, layout handling
PHASE 2: Knowledge Extraction - Semantic concept matching, content validation
PHASE 3: LLM Processing - SQL validation, quality checks, content verification
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Configure Marker/Surya memory settings BEFORE importing
# These reduce memory usage for large PDFs (prevents OOM kills)
os.environ.setdefault("SURYA_MAX_WORKERS", "1")  # Limit parallel OCR workers
os.environ.setdefault("MARKER_MAX_WORKERS", "1")  # Limit Marker workers
os.environ.setdefault("TORCH_DEVICE", "cpu")  # Force CPU (MPS can use more memory)

# Try to import marker, but provide fallback
try:
    from marker.converters.pdf import PdfConverter
    from marker.models import create_model_dict
    from marker.output import text_from_rendered
    MARKER_AVAILABLE = True
except ImportError:
    MARKER_AVAILABLE = False

# Try to import OpenAI for LLM generation
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .extract import check_extraction_quality, extract_pages_fitz
from .models import ConceptInfo, ConceptManifest
from .kimi_assistant import KimiAssistant  # AI-assisted Phase 1 & 2


class LLMProvider:
    """Supported LLM providers."""
    OPENAI = "openai"
    KIMI = "kimi"  # Moonshot AI
    OLLAMA = "ollama"  # Local models


class ContentValidator:
    """
    PHASE 2: Validates that extracted content matches expected concept.
    Prevents content-title mismatches like "correlated-subquery" getting JDBC content.
    """
    
    # SQL-related keywords for content validation
    SQL_KEYWORDS = [
        'select', 'from', 'where', 'join', 'inner', 'outer', 'left', 'right',
        'group by', 'order by', 'having', 'insert', 'update', 'delete', 'create',
        'table', 'database', 'index', 'view', 'trigger', 'procedure', 'function',
        'aggregate', 'count', 'sum', 'avg', 'max', 'min', 'distinct', 'union',
        'subquery', 'correlated', 'exists', 'in', 'between', 'like', 'null',
        'primary key', 'foreign key', 'constraint', 'transaction', 'commit', 'rollback'
    ]
    
    # Non-SQL patterns that indicate wrong content
    NON_SQL_PATTERNS = [
        r'JDBC', r'Java\s+Servlet', r'HttpServlet', r'doGet|doPost',
        r'Perl', r'CGI', r'\$[a-zA-Z_]+\s*=',  # Perl variables
        r'HTTP\s+protocol', r'HTML', r'request\.getParameter',
        r'Type\s+I+\s+driver', r'DatabaseMetaData',
        r'import\s+java\.', r'public\s+class\s+\w+',
        r'Figure\s+\d+[-.]\d+',  # Figure references without context
        r'Exercise\s+\d+\.\d+',   # Raw exercise text
        r'Chapter\s+\d+.*?(?:Summary|Review|Exercises)',  # Chapter end matter
    ]
    
    # Concept-specific keyword mappings for validation
    CONCEPT_KEYWORDS = {
        'select': ['select', 'column', 'retrieve', 'query', 'from', 'where'],
        'join': ['join', 'inner', 'outer', 'left', 'right', 'cross', 'natural', 'on', 'table'],
        'subquery': ['subquery', 'nested', 'correlated', 'exists', 'in', 'any', 'all'],
        'aggregate': ['aggregate', 'group by', 'having', 'count', 'sum', 'avg', 'max', 'min'],
        'insert': ['insert', 'into', 'values', 'add', 'row'],
        'update': ['update', 'set', 'modify', 'change'],
        'delete': ['delete', 'remove', 'drop', 'truncate'],
        'create-table': ['create table', 'column', 'datatype', 'constraint', 'schema'],
        'index': ['index', 'create index', 'performance', 'search', 'b-tree'],
        'view': ['view', 'create view', 'virtual table'],
        'transaction': ['transaction', 'commit', 'rollback', 'acid', 'isolation'],
        'function': ['function', 'stored procedure', 'return', 'parameter'],
        'constraint': ['constraint', 'primary key', 'foreign key', 'unique', 'check', 'not null'],
        'data-type': ['datatype', 'int', 'varchar', 'date', 'decimal', 'boolean'],
        'normalization': ['normalization', 'normal form', '1nf', '2nf', '3nf', 'bcnf', 'denormalization'],
        'erd': ['entity', 'relationship', 'attribute', 'cardinality', 'diagram'],
    }
    
    @classmethod
    def calculate_content_relevance(cls, text: str, concept_id: str, concept_title: str) -> dict:
        """
        Calculate how relevant the extracted text is to the concept.
        Returns score 0-1 and analysis.
        """
        text_lower = text.lower()
        concept_id_lower = concept_id.lower()
        title_lower = concept_title.lower()
        
        # Check for non-SQL patterns (penalty)
        non_sql_matches = 0
        for pattern in cls.NON_SQL_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                non_sql_matches += 1
        
        # Calculate non-SQL penalty (0 to -0.5)
        non_sql_penalty = min(0.5, non_sql_matches * 0.1)
        
        # Check for SQL keywords (base score)
        sql_score = 0
        for keyword in cls.SQL_KEYWORDS:
            if keyword in text_lower:
                sql_score += 1
        sql_score = min(1.0, sql_score / 10)  # Normalize, cap at 1.0
        
        # Check concept-specific relevance
        concept_specific_score = 0
        concept_keywords = []
        
        # Find matching concept keywords
        for key, keywords in cls.CONCEPT_KEYWORDS.items():
            if key in concept_id_lower or key in title_lower:
                concept_keywords = keywords
                break
        
        if concept_keywords:
            matches = sum(1 for kw in concept_keywords if kw in text_lower)
            concept_specific_score = matches / len(concept_keywords)
        else:
            # Generic SQL content check
            concept_specific_score = sql_score
        
        # Calculate final score
        final_score = (sql_score * 0.3 + concept_specific_score * 0.5) - non_sql_penalty
        final_score = max(0, min(1, final_score))
        
        return {
            "score": round(final_score, 2),
            "sql_score": round(sql_score, 2),
            "concept_score": round(concept_specific_score, 2),
            "non_sql_penalty": round(non_sql_penalty, 2),
            "is_relevant": final_score >= 0.3,  # Threshold for relevance
            "analysis": "SQL content" if sql_score > 0.3 else "Non-SQL content",
        }
    
    @classmethod
    def clean_non_sql_content(cls, text: str) -> str:
        """Remove non-SQL content like Java code, HTTP references, etc."""
        # Remove Java/Perl code blocks
        patterns = [
            # Java code blocks
            (r'```(?:java|javascript|js|perl|python)\s*\n.*?```', '', re.DOTALL),
            # Inline Java/Perl references
            (r'import\s+java\.[a-z.]+;?', '', 0),
            (r'public\s+(?:static\s+)?(?:void|class|String)\s+\w+', '', 0),
            # HTTP/HTML references
            (r'HTTP\s+protocol.*?(?:\n\n|\Z)', '\n\n', re.DOTALL),
            (r'HTML\s+form.*?(?:\n\n|\Z)', '\n\n', re.DOTALL),
            # Figure references without context
            (r'Figure\s+\d+[-.]\d+.*?(?:\n|$)', '\n', 0),
            # Exercise lists
            (r'Exercise\s+\d+\.\d+.*?(?:\n|$)', '\n', 0),
        ]
        
        for pattern, replacement, flags in patterns:
            text = re.sub(pattern, replacement, text, flags=flags)
        
        return text.strip()


class TextCleaner:
    """
    PHASE 1: Advanced text cleaning for PDF extraction.
    Handles OCR errors, headers/footers, two-column layouts.
    """
    
    # Common OCR error patterns and corrections
    OCR_CORRECTIONS = {
        r'\bArz\b': 'An',
        r'\bstatc\b': 'state',
        r'\binforination\b': 'information',
        r'\bCalcuIu,s\b': 'Calculus',
        r'\bCalcuIus\b': 'Calculus',
        r'\bstaternent\b': 'statement',
        r'\brne\b': 'me',
        r'\bquesry\b': 'query',
        r'\bproblern\b': 'problem',
        r'\bdetcrminc\b': 'determine',
        r'\bopcrator\b': 'operator',
        r'\bfonns\b': 'forms',
        r'\bdepart~ent\b': 'department',
        r'\bempl~yee\b': 'employee',
        r'\bSCALI\'-I\]P': 'SCALABILITY',
        r'\bKACTSiSEC\b': 'FACTS/SEC',
    }
    
    # Header/footer patterns
    HEADER_PATTERNS = [
        r'^\s*\d+\s+Section\s+\d+.*',        # "520 Section 5..." (with number)
        r'^\s*\d+\s+Section\b.*',            # "520 Section..." (without number after)
        r'^\s*Section\s+\d+.*',               # "Section 5..."
        r'^\s*Chapter\s+\d+.*',               # "Chapter 18..."
        r'^\s*\d+\s*Chapter\b.*',            # "525 Chapter 18..."
        r'^\s*\d+\s*$',                       # Standalone page numbers "123"
        r'^\s*Page\s+\d+.*',                  # "Page 123"
        r'^\s*\d+\s+\d+\.\d+.*',             # "160 4.3 Summary"
        r'^\s*Figure\s+\d+[-.]\d+.*$',        # Figure captions
        r'^\s*Table\s+\d+[-.]\d+.*$',         # Table captions
    ]
    
    # Exercise/lab list patterns (lines like "1. Start MySQL...", "2. Use Workbench...")
    EXERCISE_PATTERNS = [
        r'^\s*\d+\.\s+(?:Start|Use|Write|View|Click|Select|Open|Create|Delete|Update|Insert|Modify)\s+[A-Z]',  # Numbered exercises
        r'^\s*Exercise\s+\d+[-.]\d+.*$',  # "Exercise 4.1..."
        r'^\s*Lab\s+\d+.*$',  # Lab exercises
        r'^\s*Review\s+Questions.*$',  # Review questions section
    ]
    
    # Two-column detection patterns
    COLUMN_PATTERNS = [
        r'(\S{10,50}\s*)\1',  # Repeated phrases (column bleed)
    ]
    
    @classmethod
    def clean_pdf_text(cls, text: str) -> str:
        """
        Comprehensive PDF text cleaning pipeline.
        """
        if not text:
            return ""
        
        # Step 1: Fix OCR errors
        text = cls._fix_ocr_errors(text)
        
        # Step 2: Remove headers and footers
        text = cls._remove_headers_footers(text)
        
        # Step 3: Handle two-column layout artifacts
        text = cls._fix_column_repetition(text)
        
        # Step 4: Clean formatting
        text = cls._clean_formatting(text)
        
        # Step 5: Extract and validate SQL code
        text = cls._clean_sql_code(text)
        
        return text.strip()
    
    @classmethod
    def _fix_ocr_errors(cls, text: str) -> str:
        """Fix common OCR artifacts."""
        for pattern, replacement in cls.OCR_CORRECTIONS.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text
    
    @classmethod
    def _remove_headers_footers(cls, text: str) -> str:
        """Remove page headers, footers, section markers, and exercise lists."""
        lines = text.split('\n')
        cleaned_lines = []
        in_exercise_section = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip if matches header pattern
            is_header = False
            for pattern in cls.HEADER_PATTERNS:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    is_header = True
                    break
            
            if is_header:
                continue
            
            # Check for exercise patterns
            is_exercise = False
            for pattern in cls.EXERCISE_PATTERNS:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    is_exercise = True
                    in_exercise_section = True
                    break
            
            if is_exercise:
                continue
            
            # If we were in exercise section and hit an empty line or new section, reset
            if in_exercise_section:
                if not line_stripped or line_stripped.startswith('#') or line_stripped.startswith('```'):
                    in_exercise_section = False
                else:
                    # Skip lines that look like exercise continuations
                    if re.match(r'^\s*\d+\.', line_stripped) or len(line_stripped) > 100 and 'Workbench' in line_stripped:
                        continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    @classmethod
    def _fix_column_repetition(cls, text: str) -> str:
        """Remove repeated content from two-column layouts."""
        lines = text.split('\n')
        seen_phrases = set()
        cleaned_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                cleaned_lines.append(line)
                continue
            
            # Check for repeated phrases (likely column bleed)
            is_duplicate = False
            for phrase_len in range(min(50, len(line_stripped)), 20, -10):
                phrase = line_stripped[:phrase_len]
                if phrase in seen_phrases:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                cleaned_lines.append(line)
                # Add significant phrases to seen set
                if len(line_stripped) > 30:
                    seen_phrases.add(line_stripped[:50])
        
        return '\n'.join(cleaned_lines)
    
    @classmethod
    def _clean_formatting(cls, text: str) -> str:
        """Clean up whitespace and formatting."""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]{2,}', ' ', text)
        
        # Remove standalone punctuation
        text = re.sub(r'\n\s*[-—]\s*\n', '\n', text)
        
        return text
    
    @classmethod
    def _clean_sql_code(cls, text: str) -> str:
        """Clean and validate SQL code blocks - less aggressive version."""
        # Find code blocks and clean them
        def clean_code_block(match):
            code = match.group(1)
            
            # Only clean obvious narrative lines, not SQL with comments
            lines = code.split('\n')
            cleaned_lines = []
            
            for line in lines:
                line_stripped = line.strip()
                
                # Skip lines that are clearly narrative instructions (not SQL)
                # These are lines that start with instructional words and are very long
                if re.match(r'^(Figure|Table)\s+\d+', line_stripped, re.IGNORECASE):
                    continue
                
                # Skip lines that look like exercise instructions
                if re.match(r'^\d+\.', line_stripped) and len(line_stripped) > 50:
                    continue
                
                # Keep the line (it's probably SQL or a comment)
                cleaned_lines.append(line)
            
            return '```sql\n' + '\n'.join(cleaned_lines) + '\n```'
        
        # Clean SQL code blocks
        text = re.sub(r'```sql\s*\n(.*?)\n```', clean_code_block, text, flags=re.DOTALL)
        
        return text
    
    @classmethod
    def extract_clean_sql_examples(cls, text: str) -> list[dict]:
        """Extract clean SQL examples from text."""
        examples = []
        
        # Pattern for SQL statements
        sql_pattern = r'(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|WITH)\s+[^;]{10,500};'
        matches = re.finditer(sql_pattern, text, re.IGNORECASE | re.DOTALL)
        
        for i, match in enumerate(matches, 1):
            code = match.group(0)
            
            # Clean up the code
            code = re.sub(r'\s+', ' ', code)  # Normalize whitespace
            code = code.strip()
            
            # Skip if too short or contains narrative
            if len(code) < 20:
                continue
            if re.search(r'\b(This|That|Figure|Table)\s+', code[:50]):
                continue
            
            # Check if valid SQL (starts with keyword)
            first_word = code.split()[0].upper()
            if first_word in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'WITH']:
                examples.append({
                    'title': f'SQL Example {i}',
                    'code': code,
                    'explanation': 'Example SQL query',
                })
        
        return examples


class SQLValidator:
    """
    PHASE 3: Validates SQL code for correctness and completeness.
    """
    
    # SQL keywords that should be in complete statements
    SQL_KEYWORDS = ['SELECT', 'FROM', 'INSERT', 'UPDATE', 'DELETE', 'WHERE', 'JOIN', 'GROUP BY', 'ORDER BY']
    
    # Patterns that indicate incomplete/fragmented SQL
    FRAGMENT_PATTERNS = [
        r'^\s*(?:SELECT|INSERT|UPDATE|DELETE)\s*$',  # Just keyword
        r'\bSELECT\b[^;]*\bSELECT\b[^;]*;',  # Multiple SELECTs without proper structure
        r'\(\s*SELECT[^)]*$',  # Unclosed subquery
        r'\bFROM\b[^;]*\bFROM\b[^;]*;',  # Multiple FROMs
    ]
    
    @classmethod
    def validate_sql(cls, code: str) -> dict:
        """Validate SQL code and return analysis."""
        code_upper = code.upper().strip()
        
        # Check for SQL statement type (use word boundaries to avoid partial matches)
        has_select = re.search(r'\bSELECT\b', code_upper) is not None
        has_insert = re.search(r'\bINSERT\b', code_upper) is not None
        has_update = re.search(r'\bUPDATE\b', code_upper) is not None
        has_delete = re.search(r'\bDELETE\b', code_upper) is not None
        has_create = re.search(r'\bCREATE\b', code_upper) is not None
        has_from = re.search(r'\bFROM\b', code_upper) is not None
        has_into = re.search(r'\bINTO\b', code_upper) is not None
        has_set = re.search(r'\bSET\b', code_upper) is not None
        has_where = re.search(r'\bWHERE\b', code_upper) is not None
        has_values = re.search(r'\bVALUES\b', code_upper) is not None
        has_semicolon = code.strip().endswith(';')
        
        # Determine SQL type
        is_select = has_select
        is_insert = has_insert
        is_update = has_update
        is_delete = has_delete
        is_create = has_create
        
        # Check for fragments
        is_fragment = False
        for pattern in cls.FRAGMENT_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                is_fragment = True
                break
        
        # Calculate completeness score based on SQL type
        score = 0
        required_parts = 0
        has_required = 0
        
        if is_select:
            # SELECT needs: SELECT + FROM + semicolon (minimum)
            required_parts = 3
            if has_select:
                score += 0.25
                has_required += 1
            if has_from:
                score += 0.35  # FROM is critical for SELECT
                has_required += 1
            if has_where:
                score += 0.15  # WHERE is optional
            if has_semicolon:
                score += 0.25
                has_required += 1
        elif is_insert:
            # INSERT needs: INSERT + INTO + VALUES/SELECT + semicolon
            required_parts = 4
            if has_insert:
                score += 0.25
                has_required += 1
            if has_into:
                score += 0.25
                has_required += 1
            if has_values or has_select:
                score += 0.25
                has_required += 1
            if has_semicolon:
                score += 0.25
                has_required += 1
        elif is_update:
            # UPDATE needs: UPDATE + SET + semicolon
            required_parts = 3
            if has_update:
                score += 0.3
                has_required += 1
            if has_set:
                score += 0.3
                has_required += 1
            if has_semicolon:
                score += 0.4
                has_required += 1
        elif is_delete:
            # DELETE needs: DELETE + FROM + semicolon
            required_parts = 3
            if has_delete:
                score += 0.3
                has_required += 1
            if has_from:
                score += 0.3
                has_required += 1
            if has_semicolon:
                score += 0.4
                has_required += 1
        elif is_create:
            # CREATE needs: CREATE + object + semicolon
            required_parts = 2
            if has_create:
                score += 0.4
                has_required += 1
            if has_semicolon:
                score += 0.6
                has_required += 1
        else:
            # Unknown SQL type - check for basic SQL patterns
            score = 0.3 if len(code.strip()) > 10 else 0
            required_parts = 1
            has_required = 1 if score > 0 else 0
        
        # Penalty for fragments
        if is_fragment:
            score *= 0.5
        
        # Valid if: score >= 0.5 AND has all required parts AND not a fragment
        is_valid = score >= 0.5 and has_required >= required_parts and not is_fragment
        
        return {
            'is_valid': is_valid,
            'score': round(score, 2),
            'sql_type': 'SELECT' if is_select else ('INSERT' if is_insert else ('UPDATE' if is_update else ('DELETE' if is_delete else ('CREATE' if is_create else 'UNKNOWN')))),
            'has_from': has_from,
            'has_where': has_where,
            'is_fragment': is_fragment,
            'issues': cls._get_sql_issues(code),
        }
    
    @classmethod
    def _get_sql_issues(cls, code: str) -> list[str]:
        """Get list of issues with SQL code based on statement type."""
        issues = []
        code_upper = code.upper().strip()
        
        # Determine SQL type
        is_select = 'SELECT' in code_upper
        is_insert = 'INSERT' in code_upper
        is_update = 'UPDATE' in code_upper
        is_delete = 'DELETE' in code_upper
        is_create = 'CREATE' in code_upper
        
        # Type-specific validation
        if is_select:
            if 'FROM' not in code_upper:
                issues.append("Missing FROM clause")
            if re.search(r'\bSELECT\b.*\bSELECT\b', code, re.IGNORECASE) and '(' not in code:
                issues.append("Multiple SELECTs - may be fragmented")
        
        if is_insert:
            if 'INTO' not in code_upper:
                issues.append("Missing INTO clause")
            if 'VALUES' not in code_upper and 'SELECT' not in code_upper:
                issues.append("Missing VALUES or SELECT")
        
        if is_update:
            if 'SET' not in code_upper:
                issues.append("Missing SET clause")
        
        if is_delete:
            if 'FROM' not in code_upper:
                issues.append("Missing FROM clause")
        
        # Common validations
        if not code.strip().endswith(';'):
            issues.append("Missing semicolon")
        
        if len(code.split()) < 4:
            issues.append("SQL statement too short")
        
        return issues
    
    @classmethod
    def fix_sql(cls, code: str) -> str:
        """Attempt to fix common SQL issues."""
        # Add semicolon if missing
        if not code.strip().endswith(';'):
            code = code.strip() + ';'
        
        # Fix spacing
        code = re.sub(r'\s+', ' ', code)
        
        # Capitalize keywords
        keywords = ['SELECT', 'FROM', 'WHERE', 'INSERT', 'UPDATE', 'DELETE', 
                   'JOIN', 'INNER', 'LEFT', 'RIGHT', 'OUTER', 'ON', 'GROUP BY',
                   'ORDER BY', 'HAVING', 'LIMIT', 'AND', 'OR', 'NOT', 'NULL',
                   'CREATE', 'TABLE', 'ALTER', 'DROP', 'INDEX', 'VIEW']
        
        for kw in keywords:
            code = re.sub(r'\b' + kw + r'\b', kw, code, flags=re.IGNORECASE)
        
        return code.strip()


class EducationalNoteGenerator:
    """
    Generates student-ready educational notes from PDF content.
    
    This class handles the complete pipeline:
    PDF extraction → Content structuring → LLM enhancement → SQL-Adapt format
    
    Supports multiple LLM providers:
    - OpenAI (GPT-4, GPT-4o-mini)
    - Kimi/Moonshot AI (Kimi Chat 8K/32K/128K)
    """
    
    # Default Ollama models for M1 Pro 16GB
    OLLAMA_MODELS = {
        "llama3.2:3b": {"desc": "Fast, lightweight", "ram_gb": 4},
        "qwen2.5:7b": {"desc": "Good Chinese/English", "ram_gb": 8},
        "phi4": {"desc": "Microsoft, good reasoning", "ram_gb": 10},
        "mistral:7b": {"desc": "Balanced performance", "ram_gb": 8},
        "gemma2:9b": {"desc": "Google, high quality", "ram_gb": 10},
        "llama3.1:8b": {"desc": "Meta, general purpose", "ram_gb": 8},
    }
    
    def __init__(
        self,
        openai_api_key: str | None = None,
        kimi_api_key: str | None = None,
        llm_provider: str = LLMProvider.OPENAI,
        use_marker: bool = True,
        ollama_model: str | None = None,
        ollama_host: str | None = None,
        skip_llm: bool = False,
        min_content_relevance: float = 0.3,  # Minimum relevance score for content
        use_kimi_assistant: bool = True,  # Enable AI-assisted Phase 1 & 2
    ):
        self.use_marker = use_marker and MARKER_AVAILABLE
        self.llm_provider = llm_provider.lower()
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.skip_llm = skip_llm
        self.min_content_relevance = min_content_relevance
        self.use_kimi_assistant = use_kimi_assistant
        
        # Initialize Kimi Assistant for Phase 1 & 2
        self.kimi = KimiAssistant() if use_kimi_assistant else None
        
        # Auto-select best Ollama model if not specified
        if ollama_model:
            self.ollama_model = ollama_model
        elif os.getenv("OLLAMA_MODEL"):
            self.ollama_model = os.getenv("OLLAMA_MODEL")
        else:
            # Auto-detect best available model
            self.ollama_model = self._get_best_ollama_model() or "llama3.2:3b"
        
        # Initialize OpenAI
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.openai_available = OPENAI_AVAILABLE and bool(self.openai_api_key)
        self.openai_client = None
        if self.openai_available:
            self.openai_client = openai.OpenAI(api_key=self.openai_api_key)
        
        # Initialize Kimi (Moonshot AI)
        self.kimi_api_key = kimi_api_key or os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY")
        self.kimi_available = bool(self.kimi_api_key)
        self.kimi_client = None
        if self.kimi_available:
            # Kimi uses OpenAI-compatible API
            self.kimi_client = openai.OpenAI(
                api_key=self.kimi_api_key,
                base_url="https://api.moonshot.cn/v1",
            )
        
        # Initialize Ollama (local)
        self.ollama_available = self._check_ollama_available()
        
        # Set active client based on provider
        self.llm_available = False
        self.active_client = None
        self.active_model = None
        self.llm_status_message = "No LLM configured"
        
        if self.llm_provider == LLMProvider.OLLAMA and self.ollama_available:
            self.llm_available = True
            self.active_model = self.ollama_model
            self.llm_status_message = f"Ollama ({self.ollama_model})"
        elif self.llm_provider == LLMProvider.KIMI and self.kimi_available:
            self.llm_available = True
            self.active_client = self.kimi_client
            # Allow model selection via env var (kimi-k2-5 for best quality)
            self.active_model = os.getenv("KIMI_MODEL", "moonshot-v1-8k")
            self.llm_status_message = f"Kimi ({self.active_model})"
        elif self.llm_provider == LLMProvider.OPENAI and self.openai_available:
            self.llm_available = True
            self.active_client = self.openai_client
            self.active_model = "gpt-4o-mini"  # Default: cost-effective
            self.llm_status_message = f"OpenAI ({self.active_model})"
        elif self.ollama_available:
            # Fallback to Ollama if requested provider not available
            self.llm_provider = LLMProvider.OLLAMA
            self.llm_available = True
            self.active_model = self.ollama_model
            self.llm_status_message = f"Ollama fallback ({self.ollama_model}) - {self.llm_provider} not available"
        else:
            self.llm_status_message = f"No LLM available - set API key for {self.llm_provider} or start Ollama"
        
        # Cost tracking (per 1K tokens in RMB)
        self.cost_config = {
            LLMProvider.OPENAI: {
                "gpt-4o-mini": {"input": 0.11, "output": 0.44},  # ~$0.015/$0.06
                "gpt-4o": {"input": 2.75, "output": 11.0},  # ~$0.375/$1.50
            },
            LLMProvider.KIMI: {
                "moonshot-v1-8k": {"input": 0.012, "output": 0.012},
                "moonshot-v1-32k": {"input": 0.024, "output": 0.024},
                "moonshot-v1-128k": {"input": 0.12, "output": 0.12},
                "kimi-k2-5": {"input": 0.05, "output": 0.10},  # Best quality for education
            },
            LLMProvider.OLLAMA: {
                # Local models are free (just electricity cost)
                self.ollama_model: {"input": 0.0, "output": 0.0},
            },
        }
    
    def _check_ollama_available(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            import urllib.request
            import urllib.error
            req = urllib.request.Request(
                f"{self.ollama_host}/api/tags",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status == 200
        except Exception:
            return False
    
    def _get_best_ollama_model(self) -> str | None:
        """Auto-select the best available Ollama model."""
        try:
            import urllib.request
            import json
            
            req = urllib.request.Request(
                f"{self.ollama_host}/api/tags",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                models = data.get("models", [])
                
                if not models:
                    return None
                
                # Priority order for educational content
                priority_models = [
                    "qwen2.5-coder:7b",  # Best for SQL/education
                    "qwen2.5:7b",         # Good bilingual
                    "phi4",               # Good reasoning
                    "mistral:7b",         # Balanced
                    "gemma2:9b",          # High quality
                    "llama3.1:8b",        # General purpose
                    "llama3.2:3b",        # Fast fallback
                ]
                
                available = [m.get("name", "") for m in models]
                
                # Return first match from priority list
                for preferred in priority_models:
                    for model_name in available:
                        if preferred in model_name:
                            return model_name
                
                # Return first available if no priority match
                return available[0]
                
        except Exception:
            return None
    
    def _ollama_chat(self, messages: list[dict], temperature: float = 0.7) -> str:
        """Chat with Ollama local model."""
        import urllib.request
        import json
        
        data = {
            "model": self.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 2500,  # Allow longer responses
            },
        }
        
        req = urllib.request.Request(
            f"{self.ollama_host}/api/chat",
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        
        # Longer timeout for educational content generation
        with urllib.request.urlopen(req, timeout=600) as response:
            result = json.loads(response.read().decode("utf-8"))
            content = result.get("message", {}).get("content", "")
            if not content:
                raise ValueError("Empty response from Ollama")
            return content
    
    def process_pdf(
        self,
        pdf_path: Path,
        concepts_config: dict[str, Any] | None = None,
        output_dir: Path | None = None,
        progress_callback: callable | None = None,
    ) -> dict[str, Any]:
        """
        Process PDF into educational notes and SQL-Adapt format.
        
        Args:
            pdf_path: Path to PDF file
            concepts_config: Optional concept mapping configuration
            output_dir: Where to save outputs
            progress_callback: Optional callback function(step, current, total, message)
            
        Returns:
            Dictionary with paths to generated files and metadata
            Never raises exceptions - returns error info in result
        """
        result = {
            "success": False,
            "pdf_path": str(pdf_path),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "outputs": {},
            "errors": [],
            "stats": {},
            "content_validation": {},  # Track content quality
        }
        
        def _progress(step: str, current: int, total: int, message: str = ""):
            if progress_callback:
                progress_callback(step, current, total, message)
        
        try:
            # Step 1: Extract PDF content
            _progress("extract", 0, 100, "Starting PDF extraction...")
            extraction_result = self._extract_pdf_content(pdf_path, _progress)
            if not extraction_result["success"]:
                result["errors"].extend(extraction_result["errors"])
                return result
            _progress("extract", 100, 100, f"Extracted {extraction_result.get('page_count', 0)} pages")
            
            # Step 2: Structure content by sections/concepts
            _progress("structure", 0, 100, "Structuring content...")
            structured_content = self._structure_content(
                extraction_result["content"],
                concepts_config,
            )
            num_concepts = len(structured_content.get("concepts", {}))
            _progress("structure", 100, 100, f"Found {num_concepts} concepts")
            
            # Step 3: Validate and filter content
            _progress("validate", 0, 100, "Validating content relevance...")
            validation_results = self._validate_concept_content(structured_content)
            result["content_validation"] = validation_results
            _progress("validate", 100, 100, f"Validated {len(validation_results)} concepts")
            
            # Step 4: Generate educational notes
            _progress("enhance", 0, 100, f"Generating educational notes for {num_concepts} concepts...")
            educational_notes = self._generate_educational_notes(
                structured_content, 
                progress_callback=_progress
            )
            _progress("enhance", 100, 100, "Educational notes complete")
            
            # Step 5: Create SQL-Adapt compatible output
            _progress("format", 50, 100, "Creating SQL-Adapt format...")
            sqladapt_output = self._create_sqladapt_format(
                educational_notes,
                pdf_path,
            )
            _progress("format", 100, 100, "SQL-Adapt format ready")
            
            # Step 6: Save outputs
            _progress("save", 0, 100, "Saving output files...")
            if output_dir:
                output_paths = self._save_outputs(
                    output_dir,
                    extraction_result,
                    educational_notes,
                    sqladapt_output,
                )
                result["outputs"] = output_paths
            _progress("save", 100, 100, "All files saved")
            
            result["success"] = True
            result["stats"] = {
                "pages_extracted": extraction_result.get("page_count", 0),
                "concepts_generated": len(educational_notes.get("concepts", {})),
                "extraction_method": extraction_result.get("method", "unknown"),
                "llm_enhanced": self.llm_available,
                "content_validation": validation_results.get("summary", {}),
            }
            
        except Exception as e:
            result["errors"].append(f"Processing error: {str(e)}")
            # Still return partial results if available
            if "extraction_result" in locals():
                result["partial_extraction"] = extraction_result
        
        return result
    
    def _extract_pdf_content(
        self, 
        pdf_path: Path,
        progress_callback: callable | None = None,
    ) -> dict[str, Any]:
        """
        Extract content from PDF using best available method.
        
        Strategy:
        1. First try PyMuPDF direct text extraction
        2. Check quality - if good text found, use it (fastest)
        3. If poor quality/empty, try Marker (handles complex layouts)
        4. If Marker fails/unavailable, use OCR fallback
        """
        result = {
            "success": False,
            "content": {},
            "errors": [],
            "method": "none",
        }
        
        def _update_progress(percent: int, message: str = ""):
            if progress_callback:
                progress_callback("extract", percent, 100, message)
        
        # Step 1: Try direct text extraction with PyMuPDF first (fastest)
        _update_progress(5, "Checking for embedded text...")
        try:
            pages = extract_pages_fitz(pdf_path)
            quality_check = check_extraction_quality(pages)
            
            # If we have good quality text, use it directly
            if quality_check["is_quality_good"] and not quality_check["needs_ocr"]:
                _update_progress(50, f"Using embedded text ({quality_check['total_chars']:,} chars)...")
                
                structured_pages = []
                for page_num, text in pages:
                    # PHASE 1: Clean the extracted text
                    # Step 1a: Rule-based cleaning (TextCleaner)
                    cleaned_text = TextCleaner.clean_pdf_text(text)
                    
                    # Step 1b: AI-assisted cleaning (Kimi Assistant) - optional
                    if self.use_kimi_assistant and self.kimi:
                        # Analyze text quality
                        quality_analysis = self.kimi.analyze_text_quality(cleaned_text, page_num)
                        
                        # If quality is poor, use AI cleaning
                        if quality_analysis['quality_score'] < 70:
                            ai_cleaned = self.kimi.ai_clean_text(cleaned_text, page_num)
                            cleaned_text = ai_cleaned['cleaned_text']
                    
                    structured_pages.append({
                        "page_number": page_num,
                        "text": cleaned_text,
                        "raw_text": text,  # Keep raw for reference
                        "ai_enhanced": self.use_kimi_assistant and self.kimi is not None,
                        "sections": self._extract_sections_from_text(cleaned_text),
                    })
                
                _update_progress(100, f"Extracted {len(structured_pages)} pages from embedded text")
                
                result["content"] = {
                    "markdown": "\n\n".join(p["text"] for p in structured_pages),
                    "pages": structured_pages,
                }
                result["page_count"] = len(structured_pages)
                result["method"] = "pymupdf-direct"
                result["quality"] = quality_check
                result["success"] = True
                return result
            else:
                # Text quality poor or needs OCR
                reason = quality_check.get("reason", "poor quality")
                _update_progress(10, f"Embedded text insufficient ({reason}), trying Marker...")
                result["errors"].append(f"Direct text extraction insufficient: {reason}")
                
        except Exception as e:
            _update_progress(10, f"Direct extraction failed: {e}, trying Marker...")
            result["errors"].append(f"Direct text extraction failed: {e}")
        
        # Step 2: Try Marker for better extraction (handles scanned/complex PDFs)
        if self.use_marker:
            pdf_size_mb = pdf_path.stat().st_size / (1024 * 1024)
            max_marker_size_mb = int(os.getenv("MARKER_MAX_SIZE_MB", "50"))
            
            try:
                if pdf_size_mb > max_marker_size_mb:
                    # Split and process in chunks for large PDFs
                    _update_progress(15, f"PDF large ({pdf_size_mb:.1f}MB), using chunked Marker...")
                    return self._extract_large_pdf_with_marker(
                        pdf_path, max_marker_size_mb, _update_progress
                    )
                else:
                    # Process normally for small PDFs
                    _update_progress(20, "Loading Marker models...")
                    converter = PdfConverter(artifact_dict=create_model_dict())
                    
                    _update_progress(40, "Extracting with Marker...")
                    rendered = converter(str(pdf_path))
                    
                    _update_progress(80, "Processing Marker output...")
                    markdown, _, images = text_from_rendered(rendered)
                    
                    # PHASE 1: Clean the markdown
                    markdown = TextCleaner.clean_pdf_text(markdown)
                    
                    _update_progress(90, "Parsing pages...")
                    pages = self._parse_markdown_pages(markdown, rendered)
                    
                    result["content"] = {
                        "markdown": markdown,
                        "pages": pages,
                        "images_count": len(images),
                    }
                    result["page_count"] = len(pages)
                    result["method"] = "marker"
                    result["success"] = True
                    return result
                
            except Exception as e:
                result["errors"].append(f"Marker extraction failed: {e}")
        
        # Step 3: Final fallback - basic PyMuPDF extraction with cleaning
        try:
            _update_progress(50, "Using basic PyMuPDF fallback...")
            import fitz
            doc = fitz.open(str(pdf_path))
            pages = []
            
            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                # PHASE 1: Clean extracted text
                cleaned_text = TextCleaner.clean_pdf_text(text)
                
                pages.append({
                    "page_number": page_num,
                    "text": cleaned_text,
                    "raw_text": text,
                    "sections": self._extract_sections_from_text(cleaned_text),
                })
            
            doc.close()
            
            result["content"] = {
                "markdown": "\n\n".join(p["text"] for p in pages),
                "pages": pages,
            }
            result["page_count"] = len(pages)
            result["method"] = "pymupdf-fallback"
            result["success"] = True
            _update_progress(100, f"Extracted {len(pages)} pages (fallback)")
            
        except Exception as e:
            result["errors"].append(f"PyMuPDF fallback failed: {e}")
        
        return result
    
    def _extract_large_pdf_with_marker(
        self, 
        pdf_path: Path, 
        max_chunk_size_mb: int,
        progress_callback: callable,
    ) -> dict[str, Any]:
        """
        Split large PDF into chunks, process each with Marker, merge results.
        
        This allows high-quality Marker extraction even for large PDFs
        that would normally cause out-of-memory errors.
        """
        import fitz
        import tempfile
        import shutil
        
        result = {
            "success": False,
            "content": {},
            "errors": [],
            "method": "marker-chunked",
        }
        
        temp_dir = None
        try:
            # Open PDF to get page count and estimate chunk size
            doc = fitz.open(str(pdf_path))
            total_pages = len(doc)
            pdf_size_mb = pdf_path.stat().st_size / (1024 * 1024)
            
            # Estimate pages per chunk (aim for smaller chunks to avoid timeouts)
            # Use 20MB target to stay well under limit and reduce timeout risk
            target_chunk_mb = 20  # Fixed smaller size for stability
            pages_per_chunk = max(5, int(total_pages * (target_chunk_mb / pdf_size_mb)))
            pages_per_chunk = min(pages_per_chunk, 50)  # Max 50 pages per chunk
            num_chunks = (total_pages + pages_per_chunk - 1) // pages_per_chunk
            
            progress_callback(15, f"Splitting into {num_chunks} chunks ({pages_per_chunk} pages each)...")
            
            # Create temp directory for chunks
            temp_dir = tempfile.mkdtemp(prefix="algl_pdf_chunk_")
            chunk_files = []
            
            # Split PDF into chunks
            for chunk_idx in range(num_chunks):
                start_page = chunk_idx * pages_per_chunk
                end_page = min((chunk_idx + 1) * pages_per_chunk, total_pages)
                
                chunk_doc = fitz.open()
                chunk_doc.insert_pdf(doc, from_page=start_page, to_page=end_page - 1)
                
                chunk_path = Path(temp_dir) / f"chunk_{chunk_idx:03d}.pdf"
                chunk_doc.save(str(chunk_path))
                chunk_doc.close()
                chunk_files.append((chunk_path, start_page, end_page))
            
            doc.close()
            progress_callback(20, f"Created {len(chunk_files)} chunks")
            
            # Process each chunk with Marker
            all_pages = []
            all_markdown_parts = []
            total_images = 0
            failed_chunks = []
            
            converter = None
            for chunk_idx, (chunk_path, start_page, end_page) in enumerate(chunk_files):
                chunk_progress = 20 + (chunk_idx / len(chunk_files)) * 60
                progress_callback(
                    int(chunk_progress), 
                    f"Chunk {chunk_idx + 1}/{len(chunk_files)} (pages {start_page + 1}-{end_page})..."
                )
                
                try:
                    # Initialize converter on first chunk
                    if converter is None:
                        progress_callback(int(chunk_progress), "Loading Marker models...")
                        converter = PdfConverter(artifact_dict=create_model_dict())
                    
                    # Process chunk with timeout protection
                    progress_callback(int(chunk_progress), f"Processing pages {start_page + 1}-{end_page}...")
                    rendered = converter(str(chunk_path))
                    markdown, _, images = text_from_rendered(rendered)
                    
                    # PHASE 1: Clean the markdown
                    markdown = TextCleaner.clean_pdf_text(markdown)
                    
                    # Parse pages and adjust page numbers
                    chunk_pages = self._parse_markdown_pages(markdown, rendered)
                    for page in chunk_pages:
                        # Adjust page number to match original PDF
                        if "page_number" in page:
                            page["page_number"] = start_page + page["page_number"]
                    
                    all_pages.extend(chunk_pages)
                    all_markdown_parts.append(markdown)
                    total_images += len(images)
                    
                except Exception as e:
                    # Chunk failed - fallback to PyMuPDF for this chunk
                    progress_callback(int(chunk_progress), f"Chunk failed, using PyMuPDF fallback...")
                    chunk_pages = self._extract_chunk_with_pymupdf(chunk_path, start_page)
                    
                    all_pages.extend(chunk_pages)
                    all_markdown_parts.append("\n\n".join(p["text"] for p in chunk_pages))
                    failed_chunks.append((chunk_idx + 1, str(e)))
                
                # Clean up chunk file
                chunk_path.unlink()
            
            # Clean up temp directory
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
            
            progress_callback(90, "Merging results...")
            
            # Merge results
            result["content"] = {
                "markdown": "\n\n".join(all_markdown_parts),
                "pages": all_pages,
                "images_count": total_images,
                "chunks_processed": len(chunk_files),
                "chunks_failed": len(failed_chunks),
            }
            result["page_count"] = len(all_pages)
            result["method"] = "marker-chunked"
            result["success"] = True
            
            if failed_chunks:
                result["errors"].append(
                    f"Chunks with PyMuPDF fallback: {len(failed_chunks)}/{len(chunk_files)}"
                )
            
            progress_callback(100, f"Extracted {len(all_pages)} pages ({len(chunk_files)} chunks, {len(failed_chunks)} fallback)")
            
        except Exception as e:
            result["errors"].append(f"Chunked Marker extraction failed: {e}")
            # Clean up temp directory on error
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        return result
    
    def _extract_chunk_with_pymupdf(self, chunk_path: Path, start_page_offset: int) -> list[dict]:
        """Extract a chunk using PyMuPDF as fallback when Marker fails."""
        import fitz
        
        doc = fitz.open(str(chunk_path))
        pages = []
        
        for page_num, page in enumerate(doc, 1):
            text = page.get_text()
            # PHASE 1: Clean extracted text
            cleaned_text = TextCleaner.clean_pdf_text(text)
            
            pages.append({
                "page_number": start_page_offset + page_num,
                "text": cleaned_text,
                "raw_text": text,
                "sections": self._extract_sections_from_text(cleaned_text),
            })
        
        doc.close()
        return pages
    
    def _parse_markdown_pages(self, markdown: str, rendered: Any) -> list[dict]:
        """Parse Marker markdown into page objects."""
        pages = []
        
        # Split by page markers or headers
        sections = re.split(r'\n(?=#+\s)', markdown)
        current_page = 1
        current_content = []
        
        for section in sections:
            if not section.strip():
                continue
            
            # Detect page breaks ( Marker may include page markers)
            if "<!-- Page " in section or "\f" in section:
                if current_content:
                    page_text = "\n\n".join(current_content)
                    pages.append({
                        "page_number": current_page,
                        "text": page_text,
                        "sections": self._extract_sections_from_text(page_text),
                    })
                    current_page += 1
                    current_content = []
            
            current_content.append(section)
        
        # Don't forget last page
        if current_content:
            page_text = "\n\n".join(current_content)
            pages.append({
                "page_number": current_page,
                "text": page_text,
                "sections": self._extract_sections_from_text(page_text),
            })
        
        # If no pages detected, treat entire markdown as one page
        if not pages:
            pages = [{
                "page_number": 1,
                "text": markdown,
                "sections": self._extract_sections_from_text(markdown),
            }]
        
        return pages
    
    def _extract_sections_from_text(self, text: str) -> list[dict]:
        """Extract sections from text based on headers."""
        sections = []
        
        # Match headers (## or ###)
        header_pattern = r'(?:^|\n)(#{1,3}\s+.+?)(?:\n|$)'
        matches = list(re.finditer(header_pattern, text))
        
        for i, match in enumerate(matches):
            title = match.group(1).strip('# ')
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start:end].strip()
            
            sections.append({
                "title": title,
                "content": content,
                "level": match.group(1).count('#'),
            })
        
        # If no sections found, create one from entire text
        if not sections and text.strip():
            sections = [{
                "title": "Content",
                "content": text,
                "level": 1,
            }]
        
        return sections
    
    def _structure_content(
        self,
        extraction_result: dict,
        concepts_config: dict | None,
    ) -> dict[str, Any]:
        """Structure extracted content by concepts/topics."""
        pages = extraction_result.get("pages", [])
        
        # If concepts config provided, map content to concepts
        if concepts_config and "concepts" in concepts_config:
            return self._map_to_concepts(pages, concepts_config["concepts"])
        
        # Otherwise, auto-detect topics from headers
        return self._auto_detect_topics(pages)
    
    def _map_to_concepts(
        self,
        pages: list[dict],
        concepts: dict[str, Any],
    ) -> dict[str, Any]:
        """Map page content to configured concepts with PHASE 2 validation."""
        structured = {"concepts": {}}
        
        for concept_id, concept_info in concepts.items():
            page_refs = concept_info.get("pages", [])
            sections = concept_info.get("sections", {})
            
            concept_content = {
                "id": concept_id,
                "title": concept_info.get("title", concept_id),
                "definition": concept_info.get("definition", ""),
                "difficulty": concept_info.get("difficulty", "intermediate"),
                "page_references": page_refs,
                "sections": {},
            }
            
            # Extract content for each section
            for section_name, section_pages in sections.items():
                section_text = []
                for page_num in section_pages:
                    for page in pages:
                        if page["page_number"] == page_num:
                            section_text.append(page["text"])
                
                combined_text = "\n\n".join(section_text)
                
                # PHASE 2: Validate content relevance
                relevance = ContentValidator.calculate_content_relevance(
                    combined_text, concept_id, concept_content["title"]
                )
                
                concept_content["sections"][section_name] = {
                    "text": combined_text,
                    "pages": section_pages,
                    "relevance": relevance,  # Track validation
                }
            
            structured["concepts"][concept_id] = concept_content
        
        return structured
    
    def _validate_concept_content(self, structured_content: dict) -> dict:
        """
        PHASE 2: Validate all concept content and flag issues.
        Uses both rule-based (ContentValidator) and AI-assisted (Kimi) validation.
        """
        results = {"concepts": {}, "summary": {"total": 0, "relevant": 0, "irrelevant": 0}}
        
        for concept_id, concept_data in structured_content.get("concepts", {}).items():
            results["summary"]["total"] += 1
            
            # Get all section text
            all_text = ""
            for section in concept_data.get("sections", {}).values():
                if isinstance(section, dict):
                    all_text += section.get("text", "") + "\n\n"
            
            # Step 2a: Rule-based validation (ContentValidator)
            rule_relevance = ContentValidator.calculate_content_relevance(
                all_text, concept_id, concept_data.get("title", "")
            )
            
            # Step 2b: AI-assisted validation (Kimi Assistant)
            if self.use_kimi_assistant and self.kimi:
                ai_validation = self.kimi.validate_concept_content(
                    concept_id,
                    concept_data.get("title", ""),
                    all_text
                )
                
                # Combine scores (weighted average)
                combined_score = (
                    rule_relevance["score"] * 0.4 +  # Rule-based: 40%
                    ai_validation["relevance_score"] * 0.6  # AI: 60%
                )
                
                relevance = {
                    "score": round(combined_score, 2),
                    "is_relevant": combined_score >= self.min_content_relevance,
                    "rule_based": rule_relevance,
                    "ai_assisted": ai_validation,
                    "recommendation": ai_validation.get("recommendation", "")
                }
            else:
                relevance = rule_relevance
            
            results["concepts"][concept_id] = relevance
            
            if relevance["is_relevant"]:
                results["summary"]["relevant"] += 1
            else:
                results["summary"]["irrelevant"] += 1
        
        return results
    
    def _auto_detect_topics(self, pages: list[dict]) -> dict[str, Any]:
        """Automatically detect topics from page headers."""
        structured = {"concepts": {}}
        
        for page in pages:
            for section in page.get("sections", []):
                concept_id = self._slugify(section["title"])
                
                if concept_id not in structured["concepts"]:
                    structured["concepts"][concept_id] = {
                        "id": concept_id,
                        "title": section["title"],
                        "definition": "",
                        "difficulty": "intermediate",
                        "page_references": [page["page_number"]],
                        "sections": {
                            "content": {
                                "text": section["content"],
                                "pages": [page["page_number"]],
                            }
                        },
                    }
                else:
                    # Append to existing concept
                    existing = structured["concepts"][concept_id]
                    if page["page_number"] not in existing["page_references"]:
                        existing["page_references"].append(page["page_number"])
                    
                    existing["sections"]["content"]["text"] += "\n\n" + section["content"]
        
        return structured
    
    def _generate_educational_notes(
        self, 
        structured_content: dict,
        progress_callback: callable | None = None,
    ) -> dict[str, Any]:
        """Generate educational notes from structured content."""
        notes = {"concepts": {}}
        
        concepts = list(structured_content.get("concepts", {}).items())
        total = len(concepts)
        
        for idx, (concept_id, concept_data) in enumerate(concepts, 1):
            # Update progress
            percent = int((idx / total) * 100) if total > 0 else 100
            if progress_callback:
                progress_callback(
                    "enhance", 
                    percent, 
                    100, 
                    f"Processing concept {idx}/{total}: {concept_data.get('title', concept_id)}"
                )
            
            # Get raw text for this concept
            raw_text = concept_data.get("sections", {}).get("content", {}).get("text", "")
            if not raw_text:
                # Try other sections
                for section in concept_data.get("sections", {}).values():
                    if isinstance(section, dict) and "text" in section:
                        raw_text += section["text"] + "\n\n"
            
            # PHASE 2: Check content relevance before processing
            relevance = ContentValidator.calculate_content_relevance(
                raw_text, concept_id, concept_data.get("title", "")
            )
            
            # Skip LLM if content is not relevant and we have low threshold
            if not relevance["is_relevant"] and self.min_content_relevance > 0.3:
                if progress_callback:
                    progress_callback(
                        "enhance", 
                        percent, 
                        100, 
                        f"Skipping {concept_data.get('title', concept_id)[:30]}... (irrelevant content)"
                    )
                
                notes["concepts"][concept_id] = {
                    **concept_data,
                    **self._create_placeholder_notes(
                        concept_data["title"],
                        f"Content relevance too low ({relevance['score']}). Text may not match concept.",
                    ),
                    "content_relevance": relevance,
                }
                continue
            
            # Generate educational content
            if not self.skip_llm and self.llm_available and len(raw_text) > 100:
                if progress_callback:
                    progress_callback(
                        "enhance", 
                        percent, 
                        100, 
                        f"LLM enhancing: {concept_data.get('title', concept_id)[:30]}..."
                    )
                
                educational_content = self._llm_enhance_concept(
                    concept_data["title"],
                    concept_data.get("definition", ""),
                    raw_text,
                    concept_id,  # Pass concept_id for validation
                )
            else:
                # Fallback: create basic educational content without LLM
                if self.skip_llm:
                    reason = "LLM skipped by user"
                elif not self.llm_available:
                    reason = "LLM not available"
                else:
                    reason = "Text too short"
                    
                if progress_callback:
                    progress_callback(
                        "enhance", 
                        percent, 
                        100, 
                        f"Basic extraction ({reason})"
                    )
                
                educational_content = self._create_basic_notes(
                    concept_data["title"],
                    raw_text,
                )
            
            notes["concepts"][concept_id] = {
                **concept_data,
                **educational_content,
                "content_relevance": relevance,
            }
        
        return notes
    
    def _create_placeholder_notes(self, title: str, reason: str) -> dict[str, Any]:
        """Create placeholder notes when content is not available."""
        return {
            "educational_notes": {
                "definition": f"Content for {title} could not be extracted from the textbook.",
                "explanation": f"**Note:** {reason}\n\nPlease refer to the textbook directly for this concept.",
                "key_points": ["Content not available in extracted pages"],
                "examples": [],
                "common_mistakes": [],
                "practice": {
                    "question": "See textbook for practice questions",
                    "solution": "Refer to textbook examples",
                },
            },
            "llm_enhanced": False,
            "placeholder": True,
        }
    def _llm_enhance_concept(
        self,
        title: str,
        definition: str,
        raw_text: str,
        concept_id: str = "",
    ) -> dict[str, Any]:
        """
        PHASE 3: Use LLM to transform raw textbook content into high-quality educational notes.
        Includes validation and SQL verification.
        """
        try:
            # PHASE 1: Clean the text first
            cleaned_text = TextCleaner.clean_pdf_text(raw_text)
            
            # PHASE 2: Validate content matches concept
            relevance = ContentValidator.calculate_content_relevance(
                cleaned_text, concept_id or self._slugify(title), title
            )
            
            # PHASE 2: Remove non-SQL content
            cleaned_text = ContentValidator.clean_non_sql_content(cleaned_text)
            
            # Truncate if too long - but keep more context for better understanding
            max_chars = 8000
            text_to_process = cleaned_text[:max_chars]
            
            # Use Kimi Assistant to prepare optimized prompt if available
            if self.use_kimi_assistant and self.kimi:
                # Get validation result for context-aware prompt
                validation_context = {
                    'relevance_score': relevance.get('score', 0.5),
                    'factors': relevance.get('ai_assisted', {}).get('factors', {})
                }
                
                prompt = self.kimi.prepare_llm_prompt(
                    concept_title=title,
                    raw_text=text_to_process,
                    validation_result=validation_context
                )
            else:
                # Fallback to standard prompt
                prompt = f"""You are an expert computer science educator. Transform this textbook excerpt into well-structured, student-friendly educational notes.

CRITICAL INSTRUCTIONS:
1. DO NOT copy the raw text verbatim - synthesize and explain concepts clearly
2. Focus on WHAT the concept is, WHY it matters, and HOW to use it
3. Write for a student who is learning this for the first time
4. Use clear, concise language - avoid unnecessary jargon
5. Include practical SQL examples that illustrate the concept
6. Highlight common mistakes students make with this concept
7. VERIFY all SQL examples are syntactically valid and complete
8. DO NOT include narrative text in SQL code blocks - only valid SQL
9. DO NOT include Java, Perl, or other programming languages in SQL examples
10. If the provided text doesn't contain relevant SQL content, generate appropriate examples based on the concept

TOPIC: {title}

RAW TEXTBOOK CONTENT:
{text_to_process}

---

Create educational notes in this exact JSON format:

{{
  "definition": "A clear, concise definition in 2-3 sentences that explains what this concept is and why it matters. Write this as if explaining to a beginner.",
  
  "explanation": "A detailed explanation (3-5 paragraphs) that covers:
1. What problem this concept solves
2. How it works (step by step)
3. When to use it
4. Key things to remember

Use clear language, analogies if helpful, and avoid just copying the textbook. Make it engaging and educational.",
  
  "key_points": [
    "Key point 1: Most important thing to remember",
    "Key point 2: Critical detail about usage",
    "Key point 3: Common pitfall to avoid",
    "Key point 4: Best practice or tip",
    "Key point 5: How this connects to other concepts"
  ],
  
  "examples": [
    {{
      "title": "Basic Usage",
      "code": "-- Write clean, commented SQL here\\nSELECT example\\nFROM table\\nWHERE condition;",
      "explanation": "Explain what this example demonstrates and how it works"
    }},
    {{
      "title": "Practical Example",
      "code": "-- Real-world scenario\\nSELECT more_complex_example;",
      "explanation": "Explain the practical application"
    }}
  ],
  
  "common_mistakes": [
    {{
      "mistake": "Name of the mistake",
      "incorrect_code": "-- Show the WRONG way\\nSELECT wrong_example;",
      "correct_code": "-- Show the RIGHT way\\nSELECT correct_example;",
      "explanation": "Explain why the mistake happens and how to avoid it"
    }}
  ],
  
  "practice": {{
    "question": "Create a practical question that tests understanding of this concept",
    "solution": "Provide a clear solution with explanation"
  }}
}}

REMEMBER:
- The explanation should TEACH, not just repeat the textbook
- Use formatting (bolding, lists) to make it readable
- Examples should be realistic and educational
- Common mistakes should be actual errors students make
- Write as if you're a patient, expert tutor helping a student learn
- ALL SQL code must be valid and runnable
- NO narrative text inside SQL code blocks
- NO Java, Perl, or other languages in SQL examples

Respond ONLY with the JSON object, nothing else."""
            
            # Use active client (OpenAI, Kimi, or Ollama) with retry logic
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    if self.llm_provider == LLMProvider.OLLAMA:
                        content = self._ollama_chat(
                            messages=[
                                {"role": "system", "content": "You are an expert educator. Respond ONLY with valid JSON."},
                                {"role": "user", "content": prompt},
                            ],
                            temperature=0.3,
                        )
                    else:
                        response = self.active_client.chat.completions.create(
                            model=self.active_model,
                            messages=[
                                {"role": "system", "content": "You are an expert educator. Respond ONLY with valid JSON."},
                                {"role": "user", "content": prompt},
                            ],
                            temperature=0.3,
                            max_tokens=2500,
                        )
                        content = response.choices[0].message.content
                    
                    # PHASE 3: Extract and validate JSON
                    json_match = re.search(r'\{[\s\S]*\}', content)
                    if json_match:
                        parsed = json.loads(json_match.group())
                        
                        # PHASE 3: Validate required fields
                        required_fields = ["definition", "explanation", "key_points", "examples"]
                        for field in required_fields:
                            if field not in parsed:
                                parsed[field] = [] if field in ["key_points", "examples"] else "See textbook for details."
                        
                        # PHASE 3: Validate SQL examples
                        validated_examples = []
                        for ex in parsed.get("examples", []):
                            code = ex.get("code", "")
                            validation = SQLValidator.validate_sql(code)
                            
                            # Fix SQL if needed
                            if not validation["is_valid"] and code.strip():
                                fixed_code = SQLValidator.fix_sql(code)
                                ex["code"] = fixed_code
                                ex["validation_note"] = f"SQL auto-fixed: {', '.join(validation['issues'])}"
                            
                            validated_examples.append(ex)
                        
                        parsed["examples"] = validated_examples
                        
                        # PHASE 3: Validate common mistakes SQL
                        validated_mistakes = []
                        for mistake in parsed.get("common_mistakes", []):
                            # Validate incorrect code
                            incorrect = mistake.get("incorrect_code", "")
                            if incorrect.strip():
                                val = SQLValidator.validate_sql(incorrect)
                                if not val["is_valid"]:
                                    mistake["incorrect_code"] = SQLValidator.fix_sql(incorrect)
                            
                            # Validate correct code
                            correct = mistake.get("correct_code", "")
                            if correct.strip():
                                val = SQLValidator.validate_sql(correct)
                                if not val["is_valid"]:
                                    mistake["correct_code"] = SQLValidator.fix_sql(correct)
                            
                            validated_mistakes.append(mistake)
                        
                        parsed["common_mistakes"] = validated_mistakes
                        
                        # PHASE 3b: AI-assisted post-processing (Kimi Assistant)
                        if self.use_kimi_assistant and self.kimi:
                            # Convert parsed back to string for post-processing
                            content_json = json.dumps(parsed)
                            post_processed = self.kimi.post_process_llm_output(
                                llm_output=content_json,
                                concept_title=title
                            )
                            
                            if post_processed['success']:
                                parsed = post_processed['content']
                            else:
                                # Log issues but still use the content
                                if post_processed.get('issues'):
                                    print(f"   Kimi post-processing notes: {', '.join(post_processed['issues'])}")
                        
                        return {
                            "educational_notes": parsed,
                            "llm_enhanced": True,
                            "ai_assisted": self.use_kimi_assistant and self.kimi is not None,
                            "raw_text_preview": raw_text[:200],
                            "content_relevance": relevance,
                        }
                    else:
                        raise ValueError("No JSON found in LLM response")
                        
                except Exception as e:
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(1)  # Wait before retry
                        continue
                    raise  # Re-raise on final attempt
                
        except Exception as e:
            # Log the error for debugging
            print(f"\n⚠️  LLM enhancement failed for '{title}': {e}")
            print(f"   Error type: {type(e).__name__}")
            print(f"   Using basic extraction as fallback...")
            # Fallback to basic notes
            return self._create_basic_notes(title, cleaned_text, error=str(e))
    
    def _create_basic_notes(
        self,
        title: str,
        raw_text: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Create basic educational notes without LLM (fallback method)."""
        # PHASE 1: Clean up the raw text
        cleaned_text = TextCleaner.clean_pdf_text(raw_text)
        
        # PHASE 3: Extract clean SQL examples using TextCleaner
        code_examples = TextCleaner.extract_clean_sql_examples(cleaned_text)
        
        # If no valid examples found, create a placeholder
        if not code_examples:
            code_examples = [{
                "title": "Example",
                "code": "-- See textbook for complete examples",
                "explanation": "Code examples available in the source material",
            }]
        
        # Create a better summary - find sentences that define or explain the concept
        sentences = re.split(r'(?<=[.!?])\s+', cleaned_text)
        
        # Look for definition-like sentences
        definition = ""
        for sent in sentences[:10]:
            if len(sent) > 30 and len(sent) < 300:
                lower = sent.lower()
                if any(word in lower for word in ['is a', 'are a', 'refers to', 'means', 'definition']):
                    definition = sent.strip()
                    break
        
        if not definition and sentences:
            # Use first substantial sentence
            for sent in sentences:
                if len(sent) > 50 and len(sent) < 250:
                    definition = sent.strip()
                    break
        
        # Create key points from the text
        key_points = []
        for sent in sentences[1:6]:
            if len(sent) > 40 and len(sent) < 200:
                # Clean up the sentence
                point = sent.strip()
                if point and not point.startswith('Figure') and not point.startswith('Table'):
                    key_points.append(point)
        
        # Limit explanation length
        explanation_paragraphs = []
        current_para = ""
        for sent in sentences[:15]:
            if len(current_para) < 400:
                current_para += sent + " "
            else:
                if current_para.strip():
                    explanation_paragraphs.append(current_para.strip())
                current_para = sent + " "
        if current_para.strip():
            explanation_paragraphs.append(current_para.strip())
        
        explanation = "\n\n".join(explanation_paragraphs[:3])
        
        notes = {
            "educational_notes": {
                "definition": definition[:250] if definition else f"Learn about {title} - a key concept in SQL and database management.",
                "explanation": explanation,
                "key_points": key_points[:5] if key_points else [f"Understanding {title} is essential for working with databases"],
                "examples": code_examples,
                "common_mistakes": [{
                    "mistake": "Not understanding the concept fully",
                    "incorrect_code": "-- Incorrect usage",
                    "correct_code": "-- Correct usage (see textbook)",
                    "explanation": "Review the textbook explanation carefully",
                }],
                "practice": {
                    "question": f"Practice using {title} in your own SQL queries",
                    "solution": "Try writing queries and compare with textbook examples",
                },
            },
            "llm_enhanced": False,
            "raw_text_preview": raw_text[:500],
        }
        
        if error:
            notes["llm_error"] = str(error)[:200]
        
        return notes
    
    def _create_sqladapt_format(
        self,
        educational_notes: dict,
        pdf_path: Path,
    ) -> dict[str, Any]:
        """Create SQL-Adapt compatible output format."""
        doc_id = self._slugify(pdf_path.stem)
        
        sqladapt = {
            "schemaVersion": "educational-concept-v1",
            "sourceDocId": doc_id,
            "sourceFile": str(pdf_path),
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "concepts": {},
        }
        
        for concept_id, concept_data in educational_notes.get("concepts", {}).items():
            notes = concept_data.get("educational_notes", {})
            
            # Create chunk IDs for sections
            chunk_ids = {}
            for section_name, section_data in concept_data.get("sections", {}).items():
                if isinstance(section_data, dict):
                    chunk_ids[section_name] = [
                        f"{doc_id}:p{p}:c1" 
                        for p in section_data.get("pages", [])
                    ]
            
            sqladapt["concepts"][concept_id] = {
                "id": concept_id,
                "title": concept_data.get("title", concept_id),
                "definition": notes.get("definition", concept_data.get("definition", "")),
                "difficulty": concept_data.get("difficulty", "intermediate"),
                "estimatedReadTime": self._estimate_read_time(notes),
                "pageReferences": concept_data.get("page_references", []),
                "sections": {
                    "definition": {
                        "chunkIds": chunk_ids.get("definition", chunk_ids.get("content", [])),
                        "text": notes.get("definition", ""),
                    },
                    "explanation": {
                        "chunkIds": chunk_ids.get("explanation", chunk_ids.get("content", [])),
                        "text": notes.get("explanation", ""),
                    },
                    "examples": {
                        "chunkIds": chunk_ids.get("examples", []),
                        "items": notes.get("examples", []),
                    },
                    "commonMistakes": {
                        "chunkIds": chunk_ids.get("commonMistakes", []),
                        "items": notes.get("common_mistakes", []),
                    },
                    "practice": {
                        "chunkIds": chunk_ids.get("practice", []),
                        "questions": notes.get("practice", {}),
                    },
                },
                "relatedConcepts": concept_data.get("related_concepts", []),
                "tags": concept_data.get("tags", []),
            }
        
        return sqladapt
    
    def _save_outputs(
        self,
        output_dir: Path,
        extraction_result: dict,
        educational_notes: dict,
        sqladapt_output: dict,
    ) -> dict[str, str]:
        """Save all outputs to disk in SQL-Adapt standard format."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        doc_id = sqladapt_output.get("sourceDocId", "unknown")
        
        paths = {}
        
        # Create concepts directory with textbook subdirectory (standard SQL-Adapt structure)
        concepts_root = output_dir / "concepts"
        concepts_dir = concepts_root / doc_id
        concepts_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean up any old wrongly-placed files from previous runs (in root concepts/)
        # These would be .md files that should be in subdirectories
        if concepts_root.exists():
            for old_file in concepts_root.glob("*.md"):
                # Only remove if this exact file also exists in the correct subdirectory
                correct_location = concepts_dir / old_file.name
                if correct_location.exists() and old_file.stat().st_mtime < correct_location.stat().st_mtime:
                    old_file.unlink()
        
        # Generate concept manifest (internal format) - at root level
        concept_manifest = self._create_concept_manifest(educational_notes, doc_id)
        manifest_path = output_dir / "concept-manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(concept_manifest, f, indent=2, ensure_ascii=False)
        paths["concept_manifest"] = str(manifest_path)
        
        # Generate or update concept-map.json (SQL-Adapt format with namespaced IDs)
        concept_map = self._create_concept_map(educational_notes, doc_id, output_dir)
        
        # Generate individual concept markdown files in textbook subdirectory
        # Use namespaced IDs: {source}/{concept-id}.md
        for concept_id, concept_data in educational_notes.get("concepts", {}).items():
            concept_md = self._generate_concept_markdown(concept_id, concept_data)
            concept_path = concepts_dir / f"{concept_id}.md"
            with open(concept_path, "w", encoding="utf-8") as f:
                f.write(concept_md)
        
        # Generate concepts README in textbook subdirectory
        readme_path = concepts_dir / "README.md"
        self._generate_concepts_readme(readme_path, educational_notes, doc_id)
        paths["concepts_readme"] = str(readme_path)
        
        # Save extraction result (diagnostic)
        extract_path = output_dir / f"{doc_id}-extraction.json"
        with open(extract_path, "w", encoding="utf-8") as f:
            json.dump(extraction_result, f, indent=2, ensure_ascii=False)
        paths["extraction"] = str(extract_path)
        
        # Save educational notes (diagnostic)
        notes_path = output_dir / f"{doc_id}-educational-notes.json"
        with open(notes_path, "w", encoding="utf-8") as f:
            json.dump(educational_notes, f, indent=2, ensure_ascii=False)
        paths["educational_notes"] = str(notes_path)
        
        # Save SQL-Adapt format
        sqladapt_path = output_dir / f"{doc_id}-sqladapt.json"
        with open(sqladapt_path, "w", encoding="utf-8") as f:
            json.dump(sqladapt_output, f, indent=2, ensure_ascii=False)
        paths["sqladapt"] = str(sqladapt_path)
        
        # Generate study guide (legacy, for humans)
        md_path = output_dir / f"{doc_id}-study-guide.md"
        self._generate_study_guide(md_path, educational_notes)
        paths["study_guide"] = str(md_path)
        
        return paths
    
    def _create_concept_manifest(
        self,
        educational_notes: dict,
        doc_id: str,
    ) -> dict[str, Any]:
        """Create concept manifest in standard SQL-Adapt format."""
        concepts = {}
        
        for concept_id, concept_data in educational_notes.get("concepts", {}).items():
            notes = concept_data.get("educational_notes", {})
            
            # Build sections with chunkIds (simplified for educational pipeline)
            sections = {}
            for section_name in ["definition", "explanation", "examples", "commonMistakes", "practice"]:
                sections[section_name] = {
                    "chunkIds": [f"{doc_id}:p{page}:c1" for page in concept_data.get("page_references", [])],
                    "pageNumbers": concept_data.get("page_references", []),
                }
            
            concepts[concept_id] = {
                "id": concept_id,
                "title": concept_data.get("title", concept_id),
                "definition": notes.get("definition", ""),
                "difficulty": concept_data.get("difficulty", "intermediate"),
                "estimatedReadTime": concept_data.get("estimated_read_time", 10),
                "pageReferences": concept_data.get("page_references", []),
                "sections": sections,
                "relatedConcepts": concept_data.get("related_concepts", []),
                "tags": concept_data.get("tags", []),
            }
        
        return {
            "schemaVersion": "concept-manifest-v1",
            "sourceDocId": doc_id,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "conceptCount": len(concepts),
            "concepts": concepts,
        }
    
    def _create_concept_map(
        self,
        educational_notes: dict,
        doc_id: str,
        output_dir: Path,
    ) -> dict[str, Any]:
        """
        Create or update concept-map.json in SQL-Adapt format.
        
        This creates the proper concept-map.json with:
        - version: "1.0.0"
        - sourceDocIds: array of all textbook IDs
        - concepts: dict with namespaced keys like "{source}/{concept-id}"
        """
        concept_map_file = output_dir / "concept-map.json"
        
        # Load existing concept map if it exists
        if concept_map_file.exists():
            with open(concept_map_file, "r", encoding="utf-8") as f:
                concept_map = json.load(f)
        else:
            concept_map = {
                "version": "1.0.0",
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "sourceDocIds": [],
                "concepts": {},
            }
        
        # Update timestamp
        concept_map["generatedAt"] = datetime.now(timezone.utc).isoformat()
        
        # Add this doc_id to sourceDocIds if not present
        if doc_id not in concept_map.get("sourceDocIds", []):
            concept_map["sourceDocIds"] = concept_map.get("sourceDocIds", []) + [doc_id]
        
        # Add concepts with namespaced IDs
        for concept_id, concept_data in educational_notes.get("concepts", {}).items():
            notes = concept_data.get("educational_notes", {})
            page_refs = concept_data.get("page_references", [])
            
            # Build chunkIds for each section
            chunk_ids = {
                "definition": [f"{doc_id}:p{page}:c1" for page in page_refs[:3]],
                "explanation": [f"{doc_id}:p{page}:c1" for page in page_refs[3:6] if len(page_refs) > 3],
                "examples": [f"{doc_id}:p{page}:c1" for page in page_refs[6:9] if len(page_refs) > 6],
                "commonMistakes": [f"{doc_id}:p{page}:c1" for page in page_refs[9:12] if len(page_refs) > 9],
            }
            
            # Namespace the concept ID
            namespaced_id = f"{doc_id}/{concept_id}"
            
            # Namespace related concepts
            related = concept_data.get("related_concepts", [])
            namespaced_related = [f"{doc_id}/{rid}" for rid in related]
            
            concept_map["concepts"][namespaced_id] = {
                "title": concept_data.get("title", concept_id),
                "definition": notes.get("definition", ""),
                "difficulty": concept_data.get("difficulty", "intermediate"),
                "pageNumbers": page_refs,
                "chunkIds": chunk_ids,
                "relatedConcepts": namespaced_related,
                "practiceProblemIds": [],
                "sourceDocId": doc_id,
            }
        
        # Save updated concept map
        with open(concept_map_file, "w", encoding="utf-8") as f:
            json.dump(concept_map, f, indent=2, ensure_ascii=False)
        
        return concept_map
    
    def _generate_concept_markdown(
        self,
        concept_id: str,
        concept_data: dict,
    ) -> str:
        """Generate markdown for a single concept in SQL-Adapt standard format."""
        notes = concept_data.get("educational_notes", {})
        
        lines = []
        lines.append(f"# {concept_data.get('title', concept_id)}")
        lines.append("")
        
        # Definition (Required)
        if notes.get("definition"):
            lines.append("## Definition")
            lines.append("")
            lines.append(notes["definition"])
            lines.append("")
        
        # Explanation (Required)
        if notes.get("explanation"):
            lines.append("## Explanation")
            lines.append("")
            lines.append(notes["explanation"])
            lines.append("")
        
        # Examples (Required)
        if notes.get("examples"):
            lines.append("## Examples")
            lines.append("")
            for i, ex in enumerate(notes["examples"], 1):
                title = ex.get('title', f'Example {i}')
                lines.append(f"### {title}")
                lines.append("")
                if "code" in ex:
                    lines.append("```sql")
                    lines.append(ex["code"])
                    lines.append("```")
                    lines.append("")
                if "explanation" in ex:
                    lines.append(ex["explanation"])
                    lines.append("")
        
        # Common Mistakes (Recommended)
        if notes.get("common_mistakes"):
            lines.append("## Common Mistakes")
            lines.append("")
            for mistake in notes["common_mistakes"]:
                title = mistake.get("mistake", "Mistake")
                lines.append(f"### {title}")
                lines.append("")
                
                # Incorrect code
                lines.append("**Incorrect:**")
                lines.append("")
                lines.append("```sql")
                lines.append(mistake.get("incorrect_code", "-- Wrong approach"))
                lines.append("```")
                lines.append("")
                
                # Correct code
                lines.append("**Correct:**")
                lines.append("")
                lines.append("```sql")
                lines.append(mistake.get("correct_code", "-- Fixed approach"))
                lines.append("```")
                lines.append("")
                
                # Why it happens
                lines.append(f"**Why this happens:** {mistake.get('explanation', mistake.get('correction', ''))}")
                lines.append("")
        
        # Add separator at end
        lines.append("---")
        lines.append("")
        
        # Practice
        if notes.get("practice"):
            practice = notes["practice"]
            if practice.get("question"):
                lines.append("## Practice")
                lines.append("")
                lines.append(f"**Question:** {practice['question']}")
                lines.append("")
                if practice.get("solution"):
                    lines.append(f"**Solution:** {practice['solution']}")
                    lines.append("")
        
        # Related Concepts
        related = concept_data.get("related_concepts", [])
        if related:
            lines.append("## Related Concepts")
            lines.append("")
            for rel_id in related:
                lines.append(f"- [{rel_id}]({rel_id}.md)")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_concepts_readme(
        self,
        readme_path: Path,
        educational_notes: dict,
        doc_id: str,
    ) -> None:
        """Generate README for concepts directory."""
        lines = []
        lines.append(f"# {doc_id.replace('-', ' ').title()} - Concepts")
        lines.append("")
        lines.append("This directory contains all concepts extracted from the textbook.")
        lines.append("")
        lines.append(f"**Total Concepts:** {len(educational_notes.get('concepts', {}))}")
        lines.append("")
        lines.append("## Concept Index")
        lines.append("")
        
        # Sort by difficulty then title
        concepts = educational_notes.get("concepts", {})
        sorted_concepts = sorted(
            concepts.items(),
            key=lambda x: (
                {"beginner": 0, "intermediate": 1, "advanced": 2}.get(x[1].get("difficulty", "intermediate"), 1),
                x[1].get("title", x[0]),
            )
        )
        
        current_difficulty = None
        for concept_id, concept_data in sorted_concepts:
            difficulty = concept_data.get("difficulty", "intermediate")
            title = concept_data.get("title", concept_id)
            
            if difficulty != current_difficulty:
                current_difficulty = difficulty
                lines.append(f"### {difficulty.capitalize()}")
                lines.append("")
            
            definition = concept_data.get("educational_notes", {}).get("definition", "")
            if definition:
                # Truncate definition
                short_def = definition[:80] + "..." if len(definition) > 80 else definition
                lines.append(f"- [{title}]({concept_id}.md) - {short_def}")
            else:
                lines.append(f"- [{title}]({concept_id}.md)")
        
        lines.append("")
        
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    
    def _generate_study_guide(
        self,
        output_path: Path,
        educational_notes: dict,
    ) -> None:
        """Generate human-readable study guide."""
        lines = ["# Study Guide\n", f"Generated: {datetime.now().isoformat()}\n\n"]
        
        for concept_id, concept_data in educational_notes.get("concepts", {}).items():
            notes = concept_data.get("educational_notes", {})
            
            lines.append(f"## {concept_data.get('title', concept_id)}\n\n")
            
            if notes.get("definition"):
                lines.append(f"**Definition:** {notes['definition']}\n\n")
            
            if notes.get("explanation"):
                lines.append(f"### Explanation\n{notes['explanation']}\n\n")
            
            if notes.get("key_points"):
                lines.append("### Key Points\n")
                for point in notes["key_points"]:
                    lines.append(f"- {point}\n")
                lines.append("\n")
            
            if notes.get("examples"):
                lines.append("### Examples\n")
                for ex in notes["examples"]:
                    lines.append(f"**{ex.get('title', 'Example')}:**\n")
                    if "code" in ex:
                        lines.append(f"```sql\n{ex['code']}\n```\n")
                    if "explanation" in ex:
                        lines.append(f"{ex['explanation']}\n")
                    lines.append("\n")
            
            if notes.get("common_mistakes"):
                lines.append("### Common Mistakes\n")
                for mistake in notes["common_mistakes"]:
                    lines.append(f"**❌ {mistake.get('mistake', '')}**\n")
                    lines.append(f"**✅ {mistake.get('correction', '')}**\n\n")
            
            lines.append("---\n\n")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("".join(lines))
    
    def _estimate_read_time(self, notes: dict) -> int:
        """Estimate reading time in minutes."""
        total_words = 0
        
        if notes.get("definition"):
            total_words += len(notes["definition"].split())
        
        if notes.get("explanation"):
            total_words += len(notes["explanation"].split())
        
        if notes.get("examples"):
            for ex in notes["examples"]:
                total_words += len(ex.get("explanation", "").split())
        
        # Average reading speed: 200 words per minute
        return max(1, total_words // 200)
    
    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug."""
        import re
        text = text.lower()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)
        return text.strip('-')
