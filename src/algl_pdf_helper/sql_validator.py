"""
SQL Semantic Validation System for Adaptive Textbook Helper.

This module provides comprehensive SQL validation with three layers:
1. Parse validation - Syntax checking using sqlparse
2. Execution validation - Running against SQLite in-memory database
3. Semantic validation - Checking logical correctness and best practices

Usage:
    from sql_validator import SQLValidator, ValidationLevel
    
    validator = SQLValidator()
    result = validator.validate(
        sql="SELECT * FROM users u JOIN orders o ON u.id = o.user_id;",
        expected_concept="joins",
        schema=PRACTICE_SCHEMAS
    )
    
    if result.is_valid:
        print(f"Semantic score: {result.semantic_score}")
    else:
        for error in result.errors:
            print(f"Error: {error.message}")
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import sqlparse
from sqlparse.sql import Statement, Token, Comparison, Identifier, IdentifierList
from sqlparse.tokens import Keyword, DML, DDL


# =============================================================================
# VALIDATION LEVEL ENUM
# =============================================================================

class ValidationLevel(Enum):
    """Validation levels indicating depth of validation performed."""
    PARSE = "parse"
    EXECUTION = "execution"
    SEMANTIC = "semantic"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ValidationError:
    """Detailed error information for SQL validation failures."""
    error_type: str
    message: str
    line_number: int | None = None
    column: int | None = None
    suggestion: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary representation."""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "line_number": self.line_number,
            "column": self.column,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationResult:
    """Complete result of SQL validation across all layers."""
    is_valid: bool
    validation_level: ValidationLevel
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    execution_result: dict[str, Any] | None = None
    semantic_score: float = 0.0  # 0.0 to 1.0
    
    def add_error(
        self,
        error_type: str,
        message: str,
        line_number: int | None = None,
        column: int | None = None,
        suggestion: str | None = None,
    ) -> None:
        """Add an error and mark result as invalid."""
        self.errors.append(ValidationError(
            error_type=error_type,
            message=message,
            line_number=line_number,
            column=column,
            suggestion=suggestion,
        ))
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a warning without affecting validity."""
        self.warnings.append(warning)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary representation."""
        return {
            "is_valid": self.is_valid,
            "validation_level": self.validation_level.value,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": self.warnings,
            "execution_result": self.execution_result,
            "semantic_score": self.semantic_score,
        }


# =============================================================================
# PRACTICE SCHEMA MANAGER
# =============================================================================

class PracticeSchemaManager:
    """Manages practice schemas for SQL validation.
    
    Handles creation of in-memory SQLite databases with practice schema tables
    and sample data. Also builds foreign key relationship graphs for semantic
    validation.
    """
    
    # Default PRACTICE_SCHEMAS from pedagogical_generator
    DEFAULT_SCHEMAS: dict[str, dict[str, Any]] = {
        "users": {
            "columns": ["id", "name", "email", "age", "city"],
            "sample_data": [
                (1, "Alice", "alice@email.com", 25, "Seattle"),
                (2, "Bob", "bob@email.com", 30, "Portland"),
                (3, "Charlie", "charlie@email.com", 22, "Seattle"),
                (4, "Diana", "diana@email.com", 28, "San Jose"),
                (5, "Evan", "evan@email.com", 35, "Portland"),
            ],
            "primary_key": "id",
            "description": "Stores user information including name, email, age, and city",
        },
        "orders": {
            "columns": ["order_id", "user_id", "product", "amount"],
            "sample_data": [
                (101, 1, "Laptop", 999.99),
                (102, 1, "Mouse", 29.99),
                (103, 2, "Keyboard", 79.99),
                (104, 2, "Monitor", 219.99),
                (105, 4, "Laptop", 1099.00),
                (106, 4, "Mouse", 24.99),
            ],
            "primary_key": "order_id",
            "foreign_keys": {"user_id": "users.id"},
            "description": "Stores order information linked to users",
        },
        "products": {
            "columns": ["id", "name", "category", "price"],
            "sample_data": [
                (1, "Laptop", "Electronics", 999.99),
                (2, "Mouse", "Electronics", 29.99),
                (3, "Keyboard", "Electronics", 79.99),
                (4, "Desk", "Furniture", 299.99),
                (5, "Chair", "Furniture", 199.99),
                (6, "Lamp", "Home", 49.99),
            ],
            "primary_key": "id",
            "description": "Stores product information with category and price",
        },
        "employees": {
            "columns": ["emp_id", "emp_name", "salary", "dept_id", "manager_id", "hire_date"],
            "sample_data": [
                (1, "Alice", 90000, 1, None, "2020-01-15"),
                (2, "Bob", 75000, 1, 1, "2021-03-20"),
                (3, "Carol", 80000, 2, None, "2019-06-10"),
                (4, "David", 65000, 2, 3, "2022-01-05"),
                (5, "Eve", 70000, 3, None, "2021-09-15"),
                (6, "Frank", 55000, 4, None, "2023-02-28"),
            ],
            "primary_key": "emp_id",
            "foreign_keys": {"dept_id": "departments.dept_id", "manager_id": "employees.emp_id"},
            "description": "Stores employee information including salary and department",
        },
        "departments": {
            "columns": ["dept_id", "dept_name"],
            "sample_data": [
                (1, "Engineering"),
                (2, "Sales"),
                (3, "Marketing"),
                (4, "HR"),
            ],
            "primary_key": "dept_id",
            "description": "Stores department information",
        },
    }
    
    # Foreign key relationship mappings
    FOREIGN_KEY_MAPPINGS: dict[str, dict[str, dict[str, str]]] = {
        "users": {
            "orders": {"from": "users.id", "to": "orders.user_id"},
            "employees": {"from": "users.id", "to": "employees.manager_id"},
        },
        "orders": {
            "users": {"from": "orders.user_id", "to": "users.id"},
            "products": {"from": "orders.product", "to": "products.name"},
        },
        "products": {
            "orders": {"from": "products.name", "to": "orders.product"},
        },
        "departments": {
            "employees": {"from": "departments.dept_id", "to": "employees.dept_id"},
        },
        "employees": {
            "departments": {"from": "employees.dept_id", "to": "departments.dept_id"},
            "employees_self": {"from": "employees.manager_id", "to": "employees.emp_id"},
        },
    }
    
    def __init__(self, schemas: dict[str, dict] | None = None):
        """Initialize with optional custom schemas.
        
        Args:
            schemas: Dictionary of schema definitions. Uses DEFAULT_SCHEMAS if None.
        """
        self.schemas = schemas or self.DEFAULT_SCHEMAS
    
    def setup_database(self, schema: dict[str, Any] | None = None) -> sqlite3.Connection:
        """Create and populate an in-memory SQLite database.
        
        Args:
            schema: Schema dictionary. Uses self.schemas if None.
            
        Returns:
            SQLite connection to in-memory database with tables and data.
        """
        schemas_to_use = schema or self.schemas
        
        # Create in-memory database
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Enable foreign key support
        cursor.execute("PRAGMA foreign_keys = OFF;")
        
        # Create tables in order: first tables without foreign keys, then those with FKs
        # This avoids dependency issues
        tables_without_fk = []
        tables_with_fk = []
        
        for table_name, table_schema in schemas_to_use.items():
            if table_schema.get("foreign_keys"):
                tables_with_fk.append((table_name, table_schema))
            else:
                tables_without_fk.append((table_name, table_schema))
        
        # Create tables without FKs first
        for table_name, table_schema in tables_without_fk:
            self._create_table(cursor, table_name, table_schema)
        
        # Then create tables with FKs
        for table_name, table_schema in tables_with_fk:
            self._create_table(cursor, table_name, table_schema)
        
        # Insert data after all tables are created
        for table_name, table_schema in tables_without_fk + tables_with_fk:
            self._insert_sample_data(cursor, table_name, table_schema)
        
        # Re-enable foreign key support
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        conn.commit()
        return conn
    
    def _create_table(
        self,
        cursor: sqlite3.Cursor,
        table_name: str,
        table_schema: dict[str, Any],
    ) -> None:
        """Create a single table from schema definition."""
        columns = table_schema.get("columns", [])
        primary_key = table_schema.get("primary_key", "id")
        foreign_keys = table_schema.get("foreign_keys", {})
        
        # Infer column types from sample data
        column_defs = []
        sample_data = table_schema.get("sample_data", [])
        
        for i, col in enumerate(columns):
            col_type = self._infer_column_type(col, sample_data, i)
            
            # Add PRIMARY KEY constraint
            if col == primary_key:
                col_type += " PRIMARY KEY"
            
            column_defs.append(f"{col} {col_type}")
        
        # Add foreign key constraints
        fk_constraints = []
        for col, ref in foreign_keys.items():
            ref_table, ref_col = ref.split(".")
            fk_constraints.append(f"FOREIGN KEY ({col}) REFERENCES {ref_table}({ref_col})")
        
        all_defs = column_defs + fk_constraints
        create_sql = f"CREATE TABLE {table_name} ({', '.join(all_defs)});"
        cursor.execute(create_sql)
    
    def _infer_column_type(
        self,
        column_name: str,
        sample_data: list[tuple],
        col_index: int,
    ) -> str:
        """Infer SQLite column type from column name and sample data."""
        # Type inference from column name
        if column_name.endswith("_id") or column_name in ["id", "age"]:
            return "INTEGER"
        if column_name in ["amount", "price", "salary"]:
            return "REAL"
        
        # Type inference from sample data
        if sample_data and col_index < len(sample_data[0]):
            value = sample_data[0][col_index]
            if value is None:
                return "TEXT"  # Default for unknown
            elif isinstance(value, int):
                return "INTEGER"
            elif isinstance(value, float):
                return "REAL"
        
        return "TEXT"
    
    def _insert_sample_data(
        self,
        cursor: sqlite3.Cursor,
        table_name: str,
        table_schema: dict[str, Any],
    ) -> None:
        """Insert sample data into a table."""
        columns = table_schema.get("columns", [])
        sample_data = table_schema.get("sample_data", [])
        
        if not sample_data:
            return
        
        placeholders = ", ".join(["?"] * len(columns))
        column_names = ", ".join(columns)
        insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders});"
        
        for row in sample_data:
            cursor.execute(insert_sql, row)
    
    def get_schema_graph(self, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build a graph representation of schema relationships.
        
        Returns a dictionary with:
        - tables: Dict of table names to column lists
        - relationships: List of foreign key relationships
        - join_paths: Valid join paths between tables
        
        Args:
            schema: Schema dictionary. Uses self.schemas if None.
            
        Returns:
            Schema graph dictionary.
        """
        schemas_to_use = schema or self.schemas
        
        graph = {
            "tables": {},
            "relationships": [],
            "join_paths": {},
        }
        
        # Build table info
        for table_name, table_schema in schemas_to_use.items():
            graph["tables"][table_name] = {
                "columns": table_schema.get("columns", []),
                "primary_key": table_schema.get("primary_key", "id"),
                "foreign_keys": table_schema.get("foreign_keys", {}),
            }
        
        # Build relationships from foreign keys
        for table_name, table_schema in schemas_to_use.items():
            foreign_keys = table_schema.get("foreign_keys", {})
            for col, ref in foreign_keys.items():
                ref_table, ref_col = ref.split(".")
                relationship = {
                    "from_table": table_name,
                    "from_column": col,
                    "to_table": ref_table,
                    "to_column": ref_col,
                    "type": "many_to_one",
                }
                graph["relationships"].append(relationship)
        
        # Build valid join paths using FOREIGN_KEY_MAPPINGS
        for table1, mappings in self.FOREIGN_KEY_MAPPINGS.items():
            for table2, mapping in mappings.items():
                key = tuple(sorted([table1, table2]))
                if key not in graph["join_paths"]:
                    graph["join_paths"][key] = []
                graph["join_paths"][key].append(mapping)
        
        return graph


# =============================================================================
# SEMANTIC CHECKER
# =============================================================================

class SemanticChecker:
    """Performs semantic analysis on SQL queries.
    
    Checks for logical correctness, best practices, and meaningful query
    structure beyond just syntax validity.
    """
    
    def __init__(self, schema_manager: PracticeSchemaManager | None = None):
        """Initialize with optional schema manager.
        
        Args:
            schema_manager: PracticeSchemaManager instance for schema info.
        """
        self.schema_manager = schema_manager or PracticeSchemaManager()
    
    def check_join_semantics(self, sql: str, schema: dict[str, Any] | None = None) -> list[str]:
        """Check JOIN conditions for semantic correctness.
        
        Verifies:
        - Join conditions use proper foreign key relationships
        - No suspicious cross-joins without conditions
        - Join predicates make sense semantically
        
        Args:
            sql: SQL query to check
            schema: Schema dictionary for context
            
        Returns:
            List of warning messages about join semantics.
        """
        warnings = []
        sql_upper = sql.upper()
        
        # Check for JOIN without ON (Cartesian product)
        if re.search(r'\bJOIN\s+\w+\s+(?!ON|USING)', sql_upper, re.IGNORECASE):
            warnings.append(
                "JOIN without ON clause detected - this creates a Cartesian product. "
                "Always specify join conditions with ON."
            )
        
        # Check for suspicious join conditions
        # Pattern: ON table1.column = table2.column
        join_pattern = r'ON\s+(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)'
        matches = list(re.finditer(join_pattern, sql, re.IGNORECASE))
        
        if matches:
            schema_graph = self.schema_manager.get_schema_graph(schema)
            valid_relationships = schema_graph.get("relationships", [])
            
            for match in matches:
                table1, col1, table2, col2 = match.groups()
                table1_lower = table1.lower()
                table2_lower = table2.lower()
                col1_lower = col1.lower()
                col2_lower = col2.lower()
                
                # Check if this is a valid FK relationship
                is_valid_fk = False
                for rel in valid_relationships:
                    # Check both directions
                    if (rel["from_table"] == table1_lower and 
                        rel["from_column"] == col1_lower and
                        rel["to_table"] == table2_lower and 
                        rel["to_column"] == col2_lower):
                        is_valid_fk = True
                        break
                    if (rel["from_table"] == table2_lower and 
                        rel["from_column"] == col2_lower and
                        rel["to_table"] == table1_lower and 
                        rel["to_column"] == col1_lower):
                        is_valid_fk = True
                        break
                
                # Also check FOREIGN_KEY_MAPPINGS
                fk_mappings = self.schema_manager.FOREIGN_KEY_MAPPINGS
                if (table1_lower in fk_mappings and 
                    table2_lower in fk_mappings[table1_lower]):
                    mapping = fk_mappings[table1_lower][table2_lower]
                    from_parts = mapping["from"].split(".")
                    to_parts = mapping["to"].split(".")
                    if ((from_parts[0] == table1_lower and from_parts[1] == col1_lower and
                         to_parts[0] == table2_lower and to_parts[1] == col2_lower) or
                        (from_parts[0] == table2_lower and from_parts[1] == col2_lower and
                         to_parts[0] == table1_lower and to_parts[1] == col1_lower)):
                        is_valid_fk = True
                
                if not is_valid_fk:
                    # Check for obviously wrong conditions (like joining id to id from different tables)
                    if col1_lower == col2_lower == "id" and table1_lower != table2_lower:
                        warnings.append(
                            f"Suspicious join condition: {table1}.{col1} = {table2}.{col2}. "
                            f"Joining primary keys from different tables may not be semantically meaningful. "
                            f"Did you mean to join using a foreign key relationship?"
                        )
                    else:
                        warnings.append(
                            f"Join condition {table1}.{col1} = {table2}.{col2} does not match "
                            f"a known foreign key relationship. Verify this is intentional."
                        )
        
        return warnings
    
    def check_group_by_semantics(self, sql: str) -> list[str]:
        """Check GROUP BY clause for semantic correctness.
        
        Verifies:
        - GROUP BY has appropriate aggregates
        - Non-grouped columns are properly aggregated
        
        Args:
            sql: SQL query to check
            
        Returns:
            List of warning messages about GROUP BY semantics.
        """
        warnings = []
        sql_upper = sql.upper()
        sql_parsed = sqlparse.parse(sql)[0] if sqlparse.parse(sql) else None
        
        # Check for GROUP BY
        if "GROUP BY" not in sql_upper:
            # Check if aggregates are used without GROUP BY
            aggregate_functions = ["COUNT(", "SUM(", "AVG(", "MAX(", "MIN("]
            has_aggregates = any(func in sql_upper for func in aggregate_functions)
            has_non_agg_columns = False
            
            if has_aggregates and sql_parsed:
                # Parse SELECT clause to check for non-aggregated columns
                select_seen = False
                for token in sql_parsed.tokens:
                    if token.ttype is DML and token.value.upper() == "SELECT":
                        select_seen = True
                        continue
                    if select_seen and not token.is_whitespace:
                        if hasattr(token, 'value'):
                            # Check for non-aggregate column references
                            if re.search(r'\b\w+\b', str(token)):
                                if not any(func in str(token).upper() for func in aggregate_functions):
                                    has_non_agg_columns = True
                        break
            
            if has_aggregates and has_non_agg_columns:
                warnings.append(
                    "Query uses aggregate functions with non-aggregated columns but lacks GROUP BY. "
                    "Consider adding GROUP BY for the non-aggregated columns."
                )
            
            return warnings
        
        # Has GROUP BY - check for aggregates
        aggregate_functions = ["COUNT(", "SUM(", "AVG(", "MAX(", "MIN("]
        has_aggregates = any(func in sql_upper for func in aggregate_functions)
        
        if not has_aggregates:
            warnings.append(
                "GROUP BY without aggregate functions may return arbitrary values. "
                "Consider using COUNT, SUM, AVG, etc. with GROUP BY."
            )
        
        # Check for HAVING without GROUP BY (already checked GROUP BY exists above)
        if "HAVING" in sql_upper and "GROUP BY" in sql_upper:
            # Verify HAVING uses aggregates
            having_match = re.search(r'HAVING\s+(.+?)(?:ORDER|LIMIT|$)', sql_upper, re.IGNORECASE)
            if having_match:
                having_clause = having_match.group(1)
                if not any(func in having_clause for func in aggregate_functions):
                    warnings.append(
                        "HAVING clause typically filters on aggregate results. "
                        "Consider if WHERE would be more appropriate for row-level filtering."
                    )
        
        return warnings
    
    def check_null_handling(self, sql: str) -> list[str]:
        """Check for common NULL handling mistakes.
        
        Verifies:
        - Uses IS NULL instead of = NULL
        - Uses IS NOT NULL instead of != NULL
        
        Args:
            sql: SQL query to check
            
        Returns:
            List of warning messages about NULL handling.
        """
        warnings = []
        
        # Check for = NULL (should be IS NULL)
        if re.search(r'=\s*NULL\b', sql, re.IGNORECASE):
            warnings.append(
                "Found '= NULL' - this is always false. Use 'IS NULL' instead."
            )
        
        # Check for != NULL or <> NULL (should be IS NOT NULL)
        if re.search(r'(!=|<>)\s*NULL\b', sql, re.IGNORECASE):
            warnings.append(
                "Found '!= NULL' or '<> NULL' - this is always true. Use 'IS NOT NULL' instead."
            )
        
        return warnings
    
    def check_output_consistency(
        self,
        sql: str,
        results: list[dict[str, Any]],
    ) -> list[str]:
        """Check query output for consistency issues.
        
        Verifies:
        - Column count matches SELECT clause
        - No unexpected NULLs in results
        - Row count seems reasonable
        
        Args:
            sql: SQL query that was executed
            results: Query results as list of dictionaries
            
        Returns:
            List of warning messages about output consistency.
        """
        warnings = []
        sql_upper = sql.upper()
        
        if not results:
            # Empty result might be valid, but worth noting
            if "WHERE" in sql_upper:
                warnings.append("Query returned no rows. Verify your WHERE conditions.")
            return warnings
        
        # Check column count matches SELECT
        first_row = results[0]
        actual_columns = len(first_row)
        
        # Count columns in SELECT clause (approximate)
        select_match = re.search(r'SELECT\s+(.+?)\s+FROM', sql_upper, re.DOTALL)
        if select_match:
            select_clause = select_match.group(1)
            if select_clause.strip() == "*":
                # Can't verify column count with *
                pass
            else:
                # Count comma-separated columns
                expected_columns = select_clause.count(",") + 1
                if actual_columns != expected_columns:
                    warnings.append(
                        f"Column count mismatch: SELECT has ~{expected_columns} columns "
                        f"but result has {actual_columns} columns."
                    )
        
        # Check for unexpected NULLs
        null_columns: dict[str, int] = {}
        for row in results:
            for col, val in row.items():
                if val is None:
                    null_columns[col] = null_columns.get(col, 0) + 1
        
        # Report columns with many NULLs
        for col, count in null_columns.items():
            if count > len(results) * 0.5:  # More than 50% NULL
                warnings.append(
                    f"Column '{col}' has {count}/{len(results)} NULL values (>{50}%). "
                    "Verify if this is expected."
                )
        
        # Check for suspicious result size
        if len(results) > 1000:
            warnings.append(
                f"Query returned {len(results)} rows. Consider adding LIMIT for large result sets."
            )
        
        return warnings
    
    def check_concept_alignment(
        self,
        sql: str,
        expected_concept: str,
    ) -> tuple[bool, list[str], float]:
        """Check if query aligns with expected concept.
        
        Args:
            sql: SQL query to check
            expected_concept: Expected concept ID (e.g., 'joins', 'group-by')
            
        Returns:
            Tuple of (is_aligned, warnings, score)
        """
        warnings = []
        score = 1.0
        sql_upper = sql.upper()
        
        concept_indicators: dict[str, list[str]] = {
            "joins": ["JOIN"],
            "inner-join": ["JOIN", "INNER"],
            "outer-join": ["LEFT JOIN", "RIGHT JOIN", "FULL JOIN", "OUTER JOIN"],
            "group-by": ["GROUP BY"],
            "aggregate-functions": ["COUNT(", "SUM(", "AVG(", "MAX(", "MIN("],
            "subqueries": ["SELECT", "EXISTS", "IN ("],
            "where-clause": ["WHERE"],
            "order-by": ["ORDER BY"],
            "having": ["HAVING"],
            "insert": ["INSERT"],
            "update": ["UPDATE"],
            "delete": ["DELETE"],
        }
        
        indicators = concept_indicators.get(expected_concept.lower(), [])
        
        if not indicators:
            # Unknown concept, can't validate
            return True, [], score
        
        has_indicator = any(ind in sql_upper for ind in indicators)
        
        if expected_concept.lower() in ["joins", "inner-join", "outer-join"]:
            if "JOIN" not in sql_upper:
                warnings.append(f"Expected concept '{expected_concept}' requires JOIN clause.")
                score -= 0.5
        elif expected_concept.lower() == "group-by":
            if "GROUP BY" not in sql_upper:
                warnings.append(f"Expected concept '{expected_concept}' requires GROUP BY clause.")
                score -= 0.5
        elif expected_concept.lower() == "aggregate-functions":
            agg_funcs = ["COUNT(", "SUM(", "AVG(", "MAX(", "MIN("]
            if not any(func in sql_upper for func in agg_funcs):
                warnings.append(f"Expected concept '{expected_concept}' requires aggregate functions.")
                score -= 0.5
        elif not has_indicator:
            warnings.append(
                f"Query may not demonstrate '{expected_concept}' concept as expected."
            )
            score -= 0.3
        
        return score > 0.5, warnings, max(0.0, score)


# =============================================================================
# SQL VALIDATOR
# =============================================================================

class SQLValidator:
    """Main SQL validation class with three-layer validation.
    
    Provides:
    - Parse validation using sqlparse
    - Execution validation using SQLite in-memory database
    - Semantic validation using semantic analysis
    """
    
    def __init__(
        self,
        schema_manager: PracticeSchemaManager | None = None,
        semantic_checker: SemanticChecker | None = None,
    ):
        """Initialize the validator.
        
        Args:
            schema_manager: PracticeSchemaManager for database operations
            semantic_checker: SemanticChecker for semantic analysis
        """
        self.schema_manager = schema_manager or PracticeSchemaManager()
        self.semantic_checker = semantic_checker or SemanticChecker(self.schema_manager)
    
    def validate(
        self,
        sql: str,
        expected_concept: str | None = None,
        schema: dict[str, Any] | None = None,
    ) -> ValidationResult:
        """Run complete validation pipeline on SQL query.
        
        Performs three-layer validation:
        1. Parse validation - syntax checking
        2. Execution validation - running against test database
        3. Semantic validation - logical correctness
        
        Args:
            sql: SQL query to validate
            expected_concept: Optional concept ID for concept alignment check
            schema: Optional schema dictionary (uses default if None)
            
        Returns:
            ValidationResult with complete validation information
        """
        result = ValidationResult(
            is_valid=True,
            validation_level=ValidationLevel.PARSE,
        )
        
        schemas_to_use = schema or self.schema_manager.schemas
        
        # Layer 1: Parse validation
        is_parse_valid, parse_errors = self._validate_parse(sql)
        if not is_parse_valid:
            for error in parse_errors:
                result.add_error(
                    error_type=error.error_type,
                    message=error.message,
                    line_number=error.line_number,
                    column=error.column,
                    suggestion=error.suggestion,
                )
            return result
        
        # Layer 2: Execution validation
        result.validation_level = ValidationLevel.EXECUTION
        is_exec_valid, exec_errors, exec_data = self._validate_execution(sql, schemas_to_use)
        
        for error in exec_errors:
            result.add_error(
                error_type=error.error_type,
                message=error.message,
                line_number=error.line_number,
                suggestion=error.suggestion,
            )
        
        if not is_exec_valid:
            return result
        
        result.execution_result = exec_data
        
        # Layer 3: Semantic validation
        result.validation_level = ValidationLevel.SEMANTIC
        
        # Get execution results for semantic checks
        results_list = exec_data.get("results", [])
        
        is_sem_valid, sem_warnings, sem_score = self._validate_semantic(
            sql, results_list, expected_concept, schemas_to_use
        )
        
        for warning in sem_warnings:
            result.add_warning(warning)
        
        result.semantic_score = sem_score
        
        # If semantic score is very low, mark as invalid
        if sem_score < 0.3:
            result.is_valid = False
        
        return result
    
    def _validate_parse(self, sql: str) -> tuple[bool, list[ValidationError]]:
        """Validate SQL syntax using sqlparse.
        
        Args:
            sql: SQL query to parse
            
        Returns:
            Tuple of (is_valid, list of errors)
        """
        errors: list[ValidationError] = []
        
        if not sql or not sql.strip():
            errors.append(ValidationError(
                error_type="parse",
                message="SQL query is empty",
                suggestion="Provide a valid SQL query",
            ))
            return False, errors
        
        sql_clean = sql.strip()
        
        # Check for basic SQL injection patterns
        dangerous_patterns = [
            (r";\s*DROP\s+TABLE", "Potentially dangerous DROP TABLE pattern"),
            (r";\s*DELETE\s+FROM\s+\w+\s*;?\s*$", "Dangerous DELETE without WHERE"),
        ]
        for pattern, msg in dangerous_patterns:
            if re.search(pattern, sql_clean, re.IGNORECASE):
                errors.append(ValidationError(
                    error_type="security",
                    message=msg,
                    suggestion="Review query for security issues",
                ))
        
        # Parse with sqlparse
        try:
            parsed = sqlparse.parse(sql_clean)
            if not parsed or not parsed[0].tokens:
                errors.append(ValidationError(
                    error_type="parse",
                    message="Failed to parse SQL query",
                    suggestion="Check SQL syntax",
                ))
                return False, errors
        except Exception as e:
            errors.append(ValidationError(
                error_type="parse",
                message=f"Parse error: {str(e)}",
                suggestion="Check SQL syntax",
            ))
            return False, errors
        
        statement = parsed[0]
        
        # Identify statement type
        first_token = None
        for token in statement.tokens:
            if not token.is_whitespace:
                first_token = token
                break
        
        if not first_token:
            errors.append(ValidationError(
                error_type="parse",
                message="Empty SQL statement",
            ))
            return False, errors
        
        # Validate based on statement type
        token_value = str(first_token).upper()
        
        valid_starts = [
            "SELECT", "INSERT", "UPDATE", "DELETE", "CREATE",
            "ALTER", "DROP", "WITH",
        ]
        
        if token_value not in valid_starts:
            errors.append(ValidationError(
                error_type="parse",
                message=f"Unknown SQL statement type: {token_value}",
                suggestion=f"Statement must start with one of: {', '.join(valid_starts)}",
            ))
            return False, errors
        
        # Check for common syntax errors
        syntax_checks = [
            (r"\bFROM\s+FROM\b", "Duplicate FROM clause"),
            (r"\bWHERE\s+WHERE\b", "Duplicate WHERE clause"),
            (r"\bSELECT\s+SELECT\b", "Duplicate SELECT clause"),
            (r"\*\*", "Invalid ** operator"),
            (r"==", "Use single = for equality, not =="),
        ]
        
        for pattern, message in syntax_checks:
            if re.search(pattern, sql_clean, re.IGNORECASE):
                errors.append(ValidationError(
                    error_type="syntax",
                    message=message,
                    suggestion="Fix the syntax error",
                ))
        
        # Check balanced parentheses
        open_parens = sql_clean.count("(")
        close_parens = sql_clean.count(")")
        if open_parens != close_parens:
            errors.append(ValidationError(
                error_type="syntax",
                message=f"Unbalanced parentheses: {open_parens} open, {close_parens} close",
                suggestion="Ensure all parentheses are properly closed",
            ))
        
        # Statement type-specific validation
        if token_value == "SELECT":
            self._validate_select_parse(sql_clean, errors)
        elif token_value == "INSERT":
            self._validate_insert_parse(sql_clean, errors)
        elif token_value == "UPDATE":
            self._validate_update_parse(sql_clean, errors)
        elif token_value == "DELETE":
            self._validate_delete_parse(sql_clean, errors)
        
        return len(errors) == 0, errors
    
    def _validate_select_parse(self, sql: str, errors: list[ValidationError]) -> None:
        """Parse validation specific to SELECT statements."""
        sql_upper = sql.upper()
        
        if "FROM" not in sql_upper:
            errors.append(ValidationError(
                error_type="syntax",
                message="SELECT statement missing FROM clause",
                suggestion="Add FROM table_name to specify the table",
            ))
    
    def _validate_insert_parse(self, sql: str, errors: list[ValidationError]) -> None:
        """Parse validation specific to INSERT statements."""
        sql_upper = sql.upper()
        
        if "INTO" not in sql_upper:
            errors.append(ValidationError(
                error_type="syntax",
                message="INSERT statement missing INTO clause",
                suggestion="Use INSERT INTO table_name ...",
            ))
        
        if "VALUES" not in sql_upper and "SELECT" not in sql_upper:
            errors.append(ValidationError(
                error_type="syntax",
                message="INSERT statement missing VALUES or SELECT clause",
                suggestion="Add VALUES (...) or use INSERT ... SELECT",
            ))
    
    def _validate_update_parse(self, sql: str, errors: list[ValidationError]) -> None:
        """Parse validation specific to UPDATE statements."""
        sql_upper = sql.upper()
        
        if "SET" not in sql_upper:
            errors.append(ValidationError(
                error_type="syntax",
                message="UPDATE statement missing SET clause",
                suggestion="Use UPDATE table SET column = value ...",
            ))
    
    def _validate_delete_parse(self, sql: str, errors: list[ValidationError]) -> None:
        """Parse validation specific to DELETE statements."""
        sql_upper = sql.upper()
        
        if "FROM" not in sql_upper:
            errors.append(ValidationError(
                error_type="syntax",
                message="DELETE statement missing FROM clause",
                suggestion="Use DELETE FROM table_name ...",
            ))
    
    def _validate_execution(
        self,
        sql: str,
        schema: dict[str, Any],
    ) -> tuple[bool, list[ValidationError], dict[str, Any]]:
        """Execute SQL against in-memory database for validation.
        
        Args:
            sql: SQL query to execute
            schema: Schema dictionary for table creation
            
        Returns:
            Tuple of (is_valid, errors, execution_data)
        """
        errors: list[ValidationError] = []
        exec_data: dict[str, Any] = {
            "results": [],
            "row_count": 0,
            "columns": [],
        }
        
        # Setup database
        try:
            conn = self.schema_manager.setup_database(schema)
        except Exception as e:
            errors.append(ValidationError(
                error_type="setup",
                message=f"Failed to setup test database: {str(e)}",
            ))
            return False, errors, exec_data
        
        # Execute SQL
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            
            # Check if this is a SELECT that returns results
            if sql.strip().upper().startswith("SELECT"):
                rows = cursor.fetchall()
                exec_data["row_count"] = len(rows)
                
                if rows:
                    # Get column names from cursor description
                    if cursor.description:
                        columns = [desc[0] for desc in cursor.description]
                        exec_data["columns"] = columns
                        
                        # Convert rows to dictionaries
                        results = []
                        for row in rows:
                            row_dict = dict(zip(columns, row))
                            results.append(row_dict)
                        exec_data["results"] = results
            else:
                # For INSERT/UPDATE/DELETE, get row count
                exec_data["row_count"] = cursor.rowcount
                conn.commit()
            
            conn.close()
            return True, errors, exec_data
            
        except sqlite3.OperationalError as e:
            conn.close()
            error_msg = str(e)
            suggestion = None
            
            # Provide helpful suggestions for common errors
            if "no such column" in error_msg.lower():
                suggestion = "Check column name spelling and verify it exists in the table"
            elif "no such table" in error_msg.lower():
                suggestion = "Check table name spelling - must be one of: users, orders, products, employees, departments"
            elif "ambiguous column" in error_msg.lower():
                suggestion = "Use table alias (e.g., u.id) to specify which table the column belongs to"
            elif "syntax error" in error_msg.lower():
                suggestion = "Review SQL syntax near the reported location"
            elif "misuse of aggregate" in error_msg.lower():
                suggestion = "When using aggregate functions, non-aggregated columns must be in GROUP BY"
            
            errors.append(ValidationError(
                error_type="execution",
                message=f"Execution error: {error_msg}",
                suggestion=suggestion,
            ))
            return False, errors, exec_data
            
        except Exception as e:
            conn.close()
            errors.append(ValidationError(
                error_type="execution",
                message=f"Unexpected execution error: {str(e)}",
            ))
            return False, errors, exec_data
    
    def _validate_semantic(
        self,
        sql: str,
        results: list[dict[str, Any]],
        expected_concept: str | None,
        schema: dict[str, Any],
    ) -> tuple[bool, list[str], float]:
        """Perform semantic validation on SQL and results.
        
        Args:
            sql: SQL query
            results: Execution results
            expected_concept: Expected concept ID
            schema: Schema dictionary
            
        Returns:
            Tuple of (is_valid, warnings, score)
        """
        warnings: list[str] = []
        
        # Run semantic checks
        warnings.extend(self.semantic_checker.check_join_semantics(sql, schema))
        warnings.extend(self.semantic_checker.check_group_by_semantics(sql))
        warnings.extend(self.semantic_checker.check_null_handling(sql))
        warnings.extend(self.semantic_checker.check_output_consistency(sql, results))
        
        # Check concept alignment if expected concept provided
        if expected_concept:
            _, concept_warnings, concept_score = self.semantic_checker.check_concept_alignment(
                sql, expected_concept
            )
            warnings.extend(concept_warnings)
        else:
            concept_score = 1.0
        
        # Calculate overall semantic score
        # Start with concept alignment score
        score = concept_score
        
        # Deduct for each semantic warning
        warning_penalty = min(len(warnings) * 0.1, 0.5)  # Max 0.5 penalty
        score -= warning_penalty
        
        # Bonus for returning results (query actually does something)
        if results:
            score += 0.1
        
        # Ensure score is between 0 and 1
        score = max(0.0, min(1.0, score))
        
        is_valid = score >= 0.3
        
        return is_valid, warnings, score


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def validate_sql(
    sql: str,
    expected_concept: str | None = None,
    schema: dict[str, Any] | None = None,
) -> ValidationResult:
    """Convenience function for one-off SQL validation.
    
    Args:
        sql: SQL query to validate
        expected_concept: Optional concept ID for alignment check
        schema: Optional custom schema dictionary
        
    Returns:
        ValidationResult with complete validation information
    """
    validator = SQLValidator()
    return validator.validate(sql, expected_concept, schema)


def quick_validate(sql: str) -> bool:
    """Quick validation - returns True if SQL is valid, False otherwise.
    
    Args:
        sql: SQL query to validate
        
    Returns:
        True if valid, False otherwise
    """
    result = validate_sql(sql)
    return result.is_valid


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example 1: Valid join
    valid_sql = """
        SELECT u.name, o.product, o.amount 
        FROM users u 
        JOIN orders o ON u.id = o.user_id;
    """
    
    print("=" * 60)
    print("Example 1: Valid JOIN")
    print("=" * 60)
    result = validate_sql(valid_sql, expected_concept="joins")
    print(f"Valid: {result.is_valid}")
    print(f"Level: {result.validation_level.value}")
    print(f"Semantic Score: {result.semantic_score:.2f}")
    print(f"Errors: {len(result.errors)}")
    print(f"Warnings: {len(result.warnings)}")
    if result.execution_result:
        print(f"Results: {result.execution_result['row_count']} rows")
    for warning in result.warnings:
        print(f"  Warning: {warning}")
    
    # Example 2: Semantically wrong join (users.id = products.id)
    wrong_sql = """
        SELECT * FROM users s JOIN products b ON s.id = b.id;
    """
    
    print("\n" + "=" * 60)
    print("Example 2: Semantically Wrong JOIN")
    print("=" * 60)
    result = validate_sql(wrong_sql, expected_concept="joins")
    print(f"Valid: {result.is_valid}")
    print(f"Semantic Score: {result.semantic_score:.2f}")
    print(f"Errors: {len(result.errors)}")
    for error in result.errors:
        print(f"  Error ({error.error_type}): {error.message}")
    print(f"Warnings: {len(result.warnings)}")
    for warning in result.warnings:
        print(f"  Warning: {warning}")
    
    # Example 3: NULL handling mistake
    null_sql = """
        SELECT * FROM users WHERE city = NULL;
    """
    
    print("\n" + "=" * 60)
    print("Example 3: NULL Handling Mistake")
    print("=" * 60)
    result = validate_sql(null_sql, expected_concept="where-clause")
    print(f"Valid: {result.is_valid}")
    print(f"Semantic Score: {result.semantic_score:.2f}")
    print(f"Warnings: {len(result.warnings)}")
    for warning in result.warnings:
        print(f"  Warning: {warning}")
