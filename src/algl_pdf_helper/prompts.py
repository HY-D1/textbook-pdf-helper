"""
Specialized LLM Prompts for Educational Content Generation

This module provides production-ready prompts for transforming raw PDF textbook
ccontent into high-quality, pedagogically sound educational materials for the
SQL-Adapt learning platform.

Supported LLM Providers:
- OpenAI GPT-4 / GPT-4o / GPT-4o-mini
- Moonshot AI (Kimi) - kimi-k2-5, moonshot-v1 series
- Ollama (local) - llama3.x, qwen2.5, phi4, mistral, gemma2

Usage:
    from algl_pdf_helper.prompts import (
        CONCEPT_EXPLANATION_PROMPT,
        SQL_EXAMPLE_PROMPT,
        COMMON_MISTAKES_PROMPT,
        build_concept_prompt,
        format_schema_for_prompt,
    )
    
    prompt = build_concept_prompt(
        concept_id="joins-intro",
        raw_text=extracted_text,
        context={
            "concept_title": "Introduction to JOINs",
            "difficulty": "intermediate",
            "prerequisites": ["select-basic", "where-clause"]
        }
    )
"""

from __future__ import annotations

from typing import Any


# =============================================================================
# ERROR PATTERNS LIBRARY
# =============================================================================

# Common error patterns organized by SQL concept for mistake generation
# These patterns inform the LLM about realistic mistakes students make
ERROR_PATTERNS: dict[str, list[str]] = {
    "joins": [
        "Missing ON clause in JOIN statement",
        "Ambiguous column names without table aliases",
        "Using wrong join type (INNER vs LEFT vs RIGHT)",
        "Incorrect join condition logic",
        "Forgetting that INNER JOIN excludes non-matching rows",
        "Cartesian product from missing join condition",
        "Using WHERE to filter joined results instead of ON",
    ],
    "aggregation": [
        "Forgetting GROUP BY clause with aggregate functions",
        "Mixing aggregated and non-aggregated columns",
        "Using WHERE instead of HAVING to filter aggregated results",
        "NULL handling confusion in COUNT(*) vs COUNT(column)",
        "Not understanding that aggregates collapse rows",
        "Wrong order of WHERE, GROUP BY, HAVING clauses",
    ],
    "subqueries": [
        "Using = with subqueries that return multiple rows",
        "Correlated subquery without proper correlation",
        "Confusion between IN, EXISTS, ANY, ALL operators",
        "Forgetting subquery needs parentheses",
        "Performance issues with subqueries vs JOINs",
        "Subquery in SELECT clause returning multiple rows",
    ],
    "select": [
        "Forgetting FROM clause",
        "Using column aliases in WHERE clause",
        "Confusion between * and specific columns",
        "Case sensitivity in string comparisons",
        "Not understanding execution order",
    ],
    "where": [
        "Confusion between AND and OR precedence",
        "String comparisons without quotes",
        "Using = instead of IN for multiple values",
        "Date format mismatches",
        "NULL comparisons using = instead of IS NULL",
    ],
    "insert": [
        "Column count mismatch between columns and values",
        "Data type mismatches in VALUES",
        "Forgetting required columns (NOT NULL)",
        "Identity/primary key conflicts",
    ],
    "update": [
        "Missing WHERE clause (updates all rows!)",
        "Wrong order in SET clause",
        "Subquery in SET returning multiple rows",
        "Not understanding UPDATE is a row operation",
    ],
    "delete": [
        "Missing WHERE clause (deletes everything!)",
        "Foreign key constraint violations",
        "Using DELETE instead of TRUNCATE for all rows",
    ],
    "group_by": [
        "Including non-aggregated columns not in GROUP BY",
        "Using column position numbers instead of names",
        "Confusion about GROUP BY execution order",
    ],
    "having": [
        "Using HAVING without GROUP BY",
        "Using WHERE for aggregate conditions",
        "Column references not in GROUP BY or aggregate",
    ],
    "order_by": [
        "Column position references in ORDER BY",
        "ASC/DESC confusion",
        "Ordering by column not in SELECT (in some DBs)",
    ],
    "indexes": [
        "Creating indexes on every column",
        "Not understanding B-tree vs hash indexes",
        "Forgetting index maintenance overhead",
        "Index on low-cardinality columns",
    ],
    "constraints": [
        "Primary key vs UNIQUE confusion",
        "Foreign key without referenced index",
        "CHECK constraints with complex logic",
        "Constraint naming and management",
    ],
    "transactions": [
        "Forgetting COMMIT or ROLLBACK",
        "Long-running transactions blocking others",
        "Not understanding isolation levels",
        "Deadlocks from inconsistent access order",
    ],
    "cte": [
        "Recursive CTE without termination",
        "Multiple CTEs referencing wrong order",
        "Overusing CTEs for simple queries",
    ],
    "window_functions": [
        "Confusion between ROW_NUMBER, RANK, DENSE_RANK",
        "Forgetting PARTITION BY when needed",
        "Wrong ORDER BY in OVER clause",
        "Using window functions in WHERE",
    ],
}


# =============================================================================
# DIFFICULTY GUIDELINES
# =============================================================================

# Difficulty guidelines for content generation
# Used to constrain LLM output complexity
DIFFICULTY_GUIDELINES: dict[str, dict[str, Any]] = {
    "beginner": {
        "max_joins": 1,
        "max_aggregations": 0,
        "max_subqueries": 0,
        "max_tables": 1,
        "allowed_clauses": ["SELECT", "FROM", "WHERE", "ORDER BY", "LIMIT"],
        "description": "Single table queries with basic filtering and sorting",
        "example_complexity": "Simple SELECT with WHERE, no joins or aggregates",
        "student_level": "Just starting SQL, familiar with basic SELECT syntax",
    },
    "intermediate": {
        "max_joins": 2,
        "max_aggregations": 2,
        "max_subqueries": 1,
        "max_tables": 3,
        "allowed_clauses": [
            "SELECT", "FROM", "WHERE", "ORDER BY", "LIMIT",
            "JOIN", "INNER JOIN", "LEFT JOIN", "GROUP BY", "HAVING"
        ],
        "description": "JOINs, GROUP BY, simple subqueries",
        "example_complexity": "2-table JOINs, GROUP BY with aggregates, simple subqueries",
        "student_level": "Comfortable with basics, ready for multi-table queries",
    },
    "advanced": {
        "max_joins": 3,
        "max_aggregations": 3,
        "max_subqueries": 2,
        "max_tables": 5,
        "allowed_clauses": [
            "SELECT", "FROM", "WHERE", "ORDER BY", "LIMIT",
            "JOIN", "INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN",
            "GROUP BY", "HAVING", "UNION", "INTERSECT", "EXCEPT",
            "WITH"  # CTEs
        ],
        "description": "Complex multi-table queries, correlated subqueries, CTEs",
        "example_complexity": "Multiple JOINs, correlated subqueries, recursive CTEs",
        "student_level": "Experienced with SQL, ready for optimization and complex patterns",
    },
}


# =============================================================================
# PRACTICE SCHEMA DEFINITIONS
# =============================================================================

# Standard practice schemas used across all examples
# These schemas are designed to be relatable and cover common use cases
PRACTICE_SCHEMAS: dict[str, dict[str, Any]] = {
    "users": {
        "description": "User accounts",
        "columns": [
            ("user_id", "INTEGER PRIMARY KEY", "Unique user identifier"),
            ("username", "VARCHAR(50)", "User login name"),
            ("email", "VARCHAR(100)", "Email address"),
            ("age", "INTEGER", "User age"),
            ("city", "VARCHAR(50)", "User's city"),
            ("signup_date", "DATE", "Account creation date"),
        ],
        "sample_data": [
            (1, "alice_w", "alice@example.com", 28, "Seattle", "2023-01-15"),
            (2, "bob_m", "bob@test.com", 35, "Portland", "2023-02-20"),
            (3, "carol_d", "carol@demo.com", 24, "Seattle", "2023-03-10"),
        ],
    },
    "orders": {
        "description": "Purchase orders",
        "columns": [
            ("order_id", "INTEGER PRIMARY KEY", "Unique order identifier"),
            ("user_id", "INTEGER", "Reference to users table"),
            ("product", "VARCHAR(100)", "Product name"),
            ("quantity", "INTEGER", "Number of items"),
            ("price", "DECIMAL(10,2)", "Price per item"),
            ("order_date", "DATE", "When order was placed"),
        ],
        "sample_data": [
            (101, 1, "Laptop", 1, 999.99, "2023-06-01"),
            (102, 1, "Mouse", 2, 29.99, "2023-06-01"),
            (103, 2, "Keyboard", 1, 79.99, "2023-06-15"),
            (104, 3, "Monitor", 1, 299.99, "2023-07-01"),
        ],
    },
    "products": {
        "description": "Product catalog",
        "columns": [
            ("product_id", "INTEGER PRIMARY KEY", "Unique product identifier"),
            ("name", "VARCHAR(100)", "Product name"),
            ("category", "VARCHAR(50)", "Product category"),
            ("price", "DECIMAL(10,2)", "Base price"),
            ("stock", "INTEGER", "Items in stock"),
        ],
        "sample_data": [
            (1, "Laptop", "Electronics", 999.99, 15),
            (2, "Mouse", "Electronics", 29.99, 50),
            (3, "Coffee Mug", "Kitchen", 12.99, 100),
            (4, "Notebook", "Office", 5.99, 200),
        ],
    },
    "categories": {
        "description": "Product categories",
        "columns": [
            ("category_id", "INTEGER PRIMARY KEY", "Category identifier"),
            ("name", "VARCHAR(50)", "Category name"),
            ("description", "VARCHAR(255)", "Category description"),
        ],
        "sample_data": [
            (1, "Electronics", "Gadgets and electronic devices"),
            (2, "Kitchen", "Cookware and dining items"),
            (3, "Office", "Office supplies and furniture"),
        ],
    },
}

# Schema mapping from common textbook schemas to practice schemas
# Used by SCHEMA_TRANSFORMATION_PROMPT
SCHEMA_MAPPING: dict[str, str] = {
    # Sailors database (Ramakrishnan/Gehrke textbook)
    "Sailors": "users",
    "sailors": "users",
    "Sailors.sid": "users.user_id",
    "Sailors.sname": "users.username",
    "Sailors.rating": "users.age",  # Analogy: rating ≈ age group
    "Sailors.age": "users.age",
    
    # Boats/Reserves
    "Boats": "products",
    "boats": "products",
    "Boats.bid": "products.product_id",
    "Boats.bname": "products.name",
    "Boats.color": "products.category",
    
    "Reserves": "orders",
    "reserves": "orders",
    "Reserves.sid": "orders.user_id",
    "Reserves.bid": "orders.product_id",
    "Reserves.day": "orders.order_date",
    
    # Employees/Departments (common schema)
    "Employees": "users",
    "employees": "users",
    "Employee": "users",
    "Emp": "users",
    "Emp.empno": "users.user_id",
    "Emp.ename": "users.username",
    "Emp.deptno": "users.city",  # Analogy: dept ≈ city grouping
    "Emp.sal": "users.age",  # Analogy
    
    "Departments": "categories",
    "departments": "categories",
    "Dept": "categories",
    "Dept.deptno": "categories.category_id",
    "Dept.dname": "categories.name",
    
    # Suppliers/Parts (classic database examples)
    "Suppliers": "users",
    "Parts": "products",
    "Catalog": "orders",
}


# =============================================================================
# PROMPT TEMPLATES
# =============================================================================

CONCEPT_EXPLANATION_PROMPT = """
You are an expert SQL educator creating content for beginner to intermediate students.

RAW TEXT FROM TEXTBOOK:
{raw_text}

CONCEPT TO TEACH: {concept_title}
CONCEPT ID: {concept_id}
TARGET DIFFICULTY: {difficulty}

TASK:
Transform the raw textbook text into a clear, engaging explanation (150-250 words).

REQUIREMENTS:
1. Start with WHY this concept matters (real-world relevance)
2. Explain the core idea in plain English (avoid jargon, or explain it)
3. Use an analogy if helpful
4. Connect to prerequisite concepts: {prerequisites}
5. End with what they'll be able to do after learning this

CONSTRAINTS:
- Do NOT use textbook-specific examples (Sailors, Boats, etc.)
- Use "you" to address the student directly
- Keep sentences short and digestible
- Include one concrete real-world example (e.g., "When analyzing sales data...")

OUTPUT FORMAT:
Return ONLY the explanation text, no markdown headers, no extra commentary.
"""


SQL_EXAMPLE_PROMPT = """
You are creating SQL examples for students learning {concept_title}.

CONCEPT: {concept_title}
DIFFICULTY LEVEL: {difficulty}

AVAILABLE PRACTICE TABLES:
{practice_schemas}

EXAMPLE REQUIREMENTS:
1. Title: {example_title}
2. Scenario: {scenario_description}
3. Must demonstrate: {concept_id}
4. Difficulty: {difficulty}

RULES:
- Use ONLY the table names provided above
- SQL must be syntactically correct SQLite
- Include comments explaining each clause
- Show realistic data that makes sense
- For JOINs, use users + orders tables
- For aggregation, use meaningful groupings

OUTPUT FORMAT (JSON):
{{
    "sql": "SELECT ...",
    "explanation": "This query...",
    "scenario": "When you want to...",
    "key_points": ["point 1", "point 2"],
    "expected_output": "name|product\\nAlice|Laptop\\n..."
}}
"""


COMMON_MISTAKES_PROMPT = """
You are documenting common mistakes students make when learning {concept_title}.

CONCEPT: {concept_title}
COMMON ERROR PATTERNS FOR THIS TOPIC:
{error_patterns}

TASK:
Generate 3 realistic mistakes students commonly make.

FOR EACH MISTAKE:
1. Give it a descriptive title (e.g., "Forgetting to qualify column names")
2. Show the INCORRECT SQL code
3. Show the EXACT error message they'd see in SQLite
4. Explain WHY it happens (conceptual misunderstanding)
5. Show the CORRECTED SQL
6. Provide a memorable tip to avoid this

CONSTRAINTS:
- Mistakes must be realistic for {difficulty} level students
- Use practice schema tables (users, orders, products)
- Error messages should match actual SQLite errors
- Explanations should teach the underlying concept

OUTPUT FORMAT (JSON):
[
    {{
        "title": "Mistake title",
        "error_sql": "SELECT ...",
        "error_message": "ambiguous column name: id",
        "why_it_happens": "Explanation...",
        "fix_sql": "SELECT ...",
        "key_takeaway": "Remember to..."
    }},
    ...
]
"""


PRACTICE_CHALLENGE_PROMPT = """
Create a mini coding challenge for students learning {concept_title}.

CONCEPT: {concept_title}
DIFFICULTY: {difficulty}
AVAILABLE TABLES: {tables}

REQUIREMENTS:
1. Description: A realistic scenario requiring this concept
2. Must use: {required_sql_elements}
3. Difficulty: Appropriate for {difficulty} level

CHALLENGE DESIGN:
- Start with a clear, realistic scenario
- Provide the table schema they can use
- Give a hint that's helpful but not the answer
- Provide complete solution with explanation

EXAMPLE SCENARIOS BY CONCEPT:
- JOINs: "Find users who haven't placed orders"
- Aggregation: "Calculate average order value by city"
- Subqueries: "Find products more expensive than average"

OUTPUT FORMAT (JSON):
{{
    "description": "Challenge text...",
    "hint": "Hint text...",
    "solution": "SELECT ...",
    "explanation": "This works because..."
}}
"""


SCHEMA_TRANSFORMATION_PROMPT = """
Transform this SQL example from textbook schemas to practice schemas.

ORIGINAL SQL:
{original_sql}

SCHEMA MAPPING:
{schema_mapping}

PRACTICE SCHEMAS AVAILABLE:
{practice_schemas}

TASK:
1. Replace all table names using the mapping
2. Replace column names appropriately
3. Adjust the query logic if needed for new schema
4. Ensure the transformed SQL is still pedagogically valid
5. Keep the same concept being demonstrated

RULES:
- Maintain the same SQL structure and clauses
- Use realistic data values (real names, products, etc.)
- Ensure foreign key relationships are correct in new schema
- If no direct mapping exists, create appropriate alternative

OUTPUT FORMAT (JSON):
{{
    "transformed_sql": "SELECT ...",
    "original_concept": "What this demonstrates",
    "changes_made": ["Sailors -> users", "rating -> age"],
    "notes": "Any important adjustments"
}}
"""


CONCEPT_LINKING_PROMPT = """
Given a concept and available practice problems, identify the best matches.

CONCEPT: {concept_title} ({concept_id})
CONCEPT DESCRIPTION: {description}

AVAILABLE PRACTICE PROBLEMS:
{practice_problems}

TASK:
Identify which practice problems are best for this concept.

CRITERIA:
1. Problem MUST require this concept to solve
2. Problem difficulty should match concept difficulty
3. Prefer problems that build on each other

OUTPUT FORMAT (JSON):
{{
    "primary_problems": ["problem-3", "problem-4"],
    "secondary_problems": ["problem-10"],
    "prerequisites": ["concept-id-1", "concept-id-2"],
    "next_concepts": ["concept-id-3"],
    "reasoning": "These problems require JOINs because..."
}}
"""


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def format_schema_for_prompt(schema: dict[str, Any]) -> str:
    """
    Format practice schema for inclusion in prompts.
    
    Args:
        schema: Dictionary of table schemas from PRACTICE_SCHEMAS
        
    Returns:
        Formatted string representation suitable for LLM prompts
        
    Example:
        >>> from algl_pdf_helper.prompts import PRACTICE_SCHEMAS
        >>> formatted = format_schema_for_prompt(PRACTICE_SCHEMAS)
        >>> print(formatted[:100])
        Table: users
        Columns:
          - user_id (INTEGER PRIMARY KEY): Unique user identifier
        ...
    """
    lines = []
    
    for table_name, table_info in schema.items():
        lines.append(f"Table: {table_name}")
        lines.append(f"  Description: {table_info.get('description', 'N/A')}")
        lines.append("  Columns:")
        
        for col in table_info.get('columns', []):
            if len(col) >= 3:
                col_name, col_type, col_desc = col[0], col[1], col[2]
                lines.append(f"    - {col_name} ({col_type}): {col_desc}")
            else:
                lines.append(f"    - {col[0]} ({col[1]})")
        
        # Add sample data if available
        sample_data = table_info.get('sample_data', [])
        if sample_data:
            lines.append("  Sample Data:")
            for row in sample_data[:3]:  # Limit to 3 rows
                lines.append(f"    {row}")
        
        lines.append("")
    
    return "\n".join(lines)


def format_examples_for_few_shot(examples: list[dict[str, str]]) -> str:
    """
    Format examples for few-shot prompting.
    
    Args:
        examples: List of example dictionaries with 'input' and 'output' keys
        
    Returns:
        Formatted few-shot examples string
        
    Example:
        >>> examples = [
        ...     {"input": "What is a JOIN?", "output": "A JOIN combines..."},
        ...     {"input": "Explain INNER JOIN", "output": "INNER JOIN returns..."}
        ... ]
        >>> print(format_examples_for_few_shot(examples))
    """
    lines = []
    
    for i, example in enumerate(examples, 1):
        lines.append(f"EXAMPLE {i}:")
        lines.append(f"Input: {example.get('input', '')}")
        lines.append(f"Output: {example.get('output', '')}")
        lines.append("")
    
    return "\n".join(lines)


def get_error_patterns_for_concept(concept_id: str) -> list[str]:
    """
    Get relevant error patterns for a concept.
    
    Args:
        concept_id: Concept identifier (e.g., "joins-intro", "aggregation")
        
    Returns:
        List of error pattern strings relevant to this concept
        
    Example:
        >>> patterns = get_error_patterns_for_concept("joins-intro")
        >>> print(patterns[0])
        Missing ON clause in JOIN statement
    """
    concept_id_lower = concept_id.lower()
    
    # Map concept IDs to error pattern keys
    for key in ERROR_PATTERNS:
        if key in concept_id_lower:
            return ERROR_PATTERNS[key]
    
    # Check for partial matches
    for key in ERROR_PATTERNS:
        if any(part in concept_id_lower for part in key.split('_')):
            return ERROR_PATTERNS[key]
    
    # Return generic patterns as fallback
    return ERROR_PATTERNS.get("select", ["Syntax errors", "Logic errors"])


def build_concept_prompt(
    concept_id: str,
    raw_text: str,
    context: dict[str, Any],
) -> str:
    """
    Build complete concept explanation prompt with all context.
    
    This is the main entry point for generating concept explanations.
    It assembles all necessary context into the final prompt.
    
    Args:
        concept_id: Unique concept identifier
        raw_text: Raw extracted text from PDF
        context: Dictionary containing:
            - concept_title: Human-readable title
            - difficulty: "beginner" | "intermediate" | "advanced"
            - prerequisites: List of prerequisite concept IDs
            
    Returns:
        Formatted prompt string ready for LLM
        
    Example:
        >>> prompt = build_concept_prompt(
        ...     concept_id="joins-intro",
        ...     raw_text="JOIN combines rows from two tables...",
        ...     context={
        ...         "concept_title": "Introduction to JOINs",
        ...         "difficulty": "intermediate",
        ...         "prerequisites": ["select-basic", "where-clause"]
        ...     }
        ... )
    """
    # Format prerequisites
    prerequisites = context.get("prerequisites", [])
    prereq_str = ", ".join(prerequisites) if prerequisites else "None (foundational concept)"
    
    # Build the prompt
    prompt = CONCEPT_EXPLANATION_PROMPT.format(
        raw_text=raw_text[:4000],  # Limit to prevent token overflow
        concept_title=context.get("concept_title", concept_id),
        concept_id=concept_id,
        difficulty=context.get("difficulty", "intermediate"),
        prerequisites=prereq_str,
    )
    
    return prompt


def build_sql_example_prompt(
    concept_id: str,
    concept_title: str,
    difficulty: str,
    example_title: str,
    scenario_description: str,
    custom_schemas: dict[str, Any] | None = None,
) -> str:
    """
    Build SQL example generation prompt.
    
    Args:
        concept_id: Concept identifier
        concept_title: Human-readable concept title
        difficulty: Difficulty level
        example_title: Title for this specific example
        scenario_description: Description of the scenario
        custom_schemas: Optional custom schemas (uses PRACTICE_SCHEMAS if None)
        
    Returns:
        Formatted prompt string
    """
    schemas = custom_schemas or PRACTICE_SCHEMAS
    schema_text = format_schema_for_prompt(schemas)
    
    return SQL_EXAMPLE_PROMPT.format(
        concept_title=concept_title,
        concept_id=concept_id,
        difficulty=difficulty,
        practice_schemas=schema_text,
        example_title=example_title,
        scenario_description=scenario_description,
    )


def build_mistakes_prompt(
    concept_id: str,
    concept_title: str,
    difficulty: str,
) -> str:
    """
    Build common mistakes generation prompt.
    
    Args:
        concept_id: Concept identifier
        concept_title: Human-readable concept title
        difficulty: Difficulty level
        
    Returns:
        Formatted prompt string
    """
    error_patterns = get_error_patterns_for_concept(concept_id)
    patterns_text = "\n".join(f"- {p}" for p in error_patterns)
    
    return COMMON_MISTAKES_PROMPT.format(
        concept_title=concept_title,
        error_patterns=patterns_text,
        difficulty=difficulty,
    )


def build_practice_prompt(
    concept_id: str,
    concept_title: str,
    difficulty: str,
    required_elements: list[str] | None = None,
    tables: list[str] | None = None,
) -> str:
    """
    Build practice challenge generation prompt.
    
    Args:
        concept_id: Concept identifier
        concept_title: Human-readable concept title
        difficulty: Difficulty level
        required_elements: SQL elements that must be used
        tables: Tables available for the challenge
        
    Returns:
        Formatted prompt string
    """
    required_str = ", ".join(required_elements) if required_elements else concept_id
    tables_str = ", ".join(tables) if tables else "users, orders, products"
    
    return PRACTICE_CHALLENGE_PROMPT.format(
        concept_title=concept_title,
        difficulty=difficulty,
        tables=tables_str,
        required_sql_elements=required_str,
    )


def build_transformation_prompt(
    original_sql: str,
    custom_mapping: dict[str, str] | None = None,
) -> str:
    """
    Build schema transformation prompt.
    
    Args:
        original_sql: SQL using textbook schemas
        custom_mapping: Optional custom schema mapping
        
    Returns:
        Formatted prompt string
    """
    mapping = custom_mapping or SCHEMA_MAPPING
    mapping_text = "\n".join(f"{k} -> {v}" for k, v in list(mapping.items())[:20])
    schema_text = format_schema_for_prompt(PRACTICE_SCHEMAS)
    
    return SCHEMA_TRANSFORMATION_PROMPT.format(
        original_sql=original_sql,
        schema_mapping=mapping_text,
        practice_schemas=schema_text,
    )


def build_linking_prompt(
    concept_id: str,
    concept_title: str,
    description: str,
    practice_problems: list[dict[str, Any]],
) -> str:
    """
    Build concept linking prompt.
    
    Args:
        concept_id: Concept identifier
        concept_title: Human-readable concept title
        description: Concept description
        practice_problems: List of available practice problems
        
    Returns:
        Formatted prompt string
    """
    problems_text = "\n".join(
        f"- {p.get('id', 'unknown')}: {p.get('title', 'Untitled')} ({p.get('difficulty', 'unknown')})"
        for p in practice_problems
    )
    
    return CONCEPT_LINKING_PROMPT.format(
        concept_id=concept_id,
        concept_title=concept_title,
        description=description,
        practice_problems=problems_text,
    )


# =============================================================================
# BATCH GENERATION HELPERS
# =============================================================================

def build_batch_prompts(
    concept_manifest: dict[str, Any],
    raw_texts: dict[str, str],
) -> dict[str, dict[str, str]]:
    """
    Build all prompts for a batch of concepts.
    
    This is useful for generating complete educational content for
    multiple concepts at once.
    
    Args:
        concept_manifest: Dictionary mapping concept IDs to metadata
        raw_texts: Dictionary mapping concept IDs to extracted text
        
    Returns:
        Dictionary mapping concept IDs to their prompt sets
        
    Example:
        >>> prompts = build_batch_prompts(
        ...     concept_manifest={
        ...         "joins-intro": {"title": "JOINs", "difficulty": "intermediate"}
        ...     },
        ...     raw_texts={"joins-intro": "JOIN combines tables..."}
        ... )
    """
    prompts = {}
    
    for concept_id, metadata in concept_manifest.items():
        raw_text = raw_texts.get(concept_id, "")
        difficulty = metadata.get("difficulty", "intermediate")
        title = metadata.get("title", concept_id)
        prerequisites = metadata.get("prerequisites", [])
        
        prompts[concept_id] = {
            "explanation": build_concept_prompt(
                concept_id=concept_id,
                raw_text=raw_text,
                context={
                    "concept_title": title,
                    "difficulty": difficulty,
                    "prerequisites": prerequisites,
                }
            ),
            "mistakes": build_mistakes_prompt(
                concept_id=concept_id,
                concept_title=title,
                difficulty=difficulty,
            ),
            "example": build_sql_example_prompt(
                concept_id=concept_id,
                concept_title=title,
                difficulty=difficulty,
                example_title=f"Basic {title} Example",
                scenario_description=f"Demonstrates {title} usage",
            ),
            "practice": build_practice_prompt(
                concept_id=concept_id,
                concept_title=title,
                difficulty=difficulty,
            ),
        }
    
    return prompts


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def validate_difficulty_params(difficulty: str, sql_features: dict[str, int]) -> list[str]:
    """
    Validate that SQL features match difficulty guidelines.
    
    Args:
        difficulty: Difficulty level
        sql_features: Dictionary of feature counts (joins, aggregations, etc.)
        
    Returns:
        List of validation warnings (empty if valid)
        
    Example:
        >>> warnings = validate_difficulty_params("beginner", {"joins": 2, "aggregations": 1})
        >>> print(warnings)
        ['Too many JOINs for beginner level (max 1, got 2)', ...]
    """
    guidelines = DIFFICULTY_GUIDELINES.get(difficulty)
    if not guidelines:
        return [f"Unknown difficulty level: {difficulty}"]
    
    warnings = []
    
    # Check joins
    joins = sql_features.get("joins", 0)
    max_joins = guidelines.get("max_joins", 0)
    if joins > max_joins:
        warnings.append(f"Too many JOINs for {difficulty} level (max {max_joins}, got {joins})")
    
    # Check aggregations
    aggs = sql_features.get("aggregations", 0)
    max_aggs = guidelines.get("max_aggregations", 0)
    if aggs > max_aggs:
        warnings.append(f"Too many aggregations for {difficulty} level (max {max_aggs}, got {aggs})")
    
    # Check subqueries
    subs = sql_features.get("subqueries", 0)
    max_subs = guidelines.get("max_subqueries", 0)
    if subs > max_subs:
        warnings.append(f"Too many subqueries for {difficulty} level (max {max_subs}, got {subs})")
    
    return warnings


# =============================================================================
# EXAMPLE USAGE (for documentation)
# =============================================================================

EXAMPLE_USAGE = '''
# Example: Generating educational content for "JOINs"

from algl_pdf_helper.prompts import (
    build_concept_prompt,
    build_sql_example_prompt,
    build_mistakes_prompt,
    format_schema_for_prompt,
    PRACTICE_SCHEMAS,
)

# 1. Generate concept explanation
explanation_prompt = build_concept_prompt(
    concept_id="joins-intro",
    raw_text="The JOIN operation combines rows from two or more tables based on 
        a related column between them. Different types of JOINs exist: 
        INNER JOIN returns matching rows, LEFT JOIN returns all from left table...",
    context={
        "concept_title": "Introduction to JOINs",
        "difficulty": "intermediate",
        "prerequisites": ["select-basic", "where-clause"]
    }
)

# 2. Generate SQL example
example_prompt = build_sql_example_prompt(
    concept_id="joins-intro",
    concept_title="Introduction to JOINs",
    difficulty="intermediate",
    example_title="Finding User Orders",
    scenario_description="Show all users and their orders, including users with no orders"
)

# 3. Generate common mistakes
mistakes_prompt = build_mistakes_prompt(
    concept_id="joins-intro",
    concept_title="Introduction to JOINs",
    difficulty="intermediate"
)

# 4. Send prompts to your LLM
# (Using OpenAI, Kimi, or Ollama)
import openai

client = openai.OpenAI()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": explanation_prompt}],
    temperature=0.7
)

explanation_text = response.choices[0].message.content
'''


if __name__ == "__main__":
    # Demo: Show formatted output
    print("=" * 60)
    print("PROMPTS MODULE DEMO")
    print("=" * 60)
    
    print("\n1. Formatted Practice Schemas:")
    print("-" * 40)
    print(format_schema_for_prompt(PRACTICE_SCHEMAS))
    
    print("\n2. Error Patterns for 'joins':")
    print("-" * 40)
    for pattern in get_error_patterns_for_concept("joins-intro"):
        print(f"  - {pattern}")
    
    print("\n3. Difficulty Guidelines:")
    print("-" * 40)
    for level, guidelines in DIFFICULTY_GUIDELINES.items():
        print(f"\n  {level.upper()}:")
        print(f"    Description: {guidelines['description']}")
        print(f"    Max JOINs: {guidelines['max_joins']}")
        print(f"    Max Aggregations: {guidelines['max_aggregations']}")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)
