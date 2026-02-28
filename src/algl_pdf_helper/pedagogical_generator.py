"""
Pedagogical Content Generator for SQL-Adapt Learning Platform.

This module transforms raw PDF textbook content into pedagogically structured,
student-ready educational materials that use practice schemas instead of 
textbook-specific schemas.
"""

from __future__ import annotations

import re
from typing import Any


# =============================================================================
# PRACTICE SCHEMAS - Standardized schemas for all SQL examples
# =============================================================================

PRACTICE_SCHEMAS: dict[str, dict[str, Any]] = {
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


# =============================================================================
# TEXTBOOK TO PRACTICE SCHEMA MAPPING
# =============================================================================

TEXTBOOK_TO_PRACTICE_MAPPING: dict[str, str] = {
    # Table mappings (case-insensitive)
    "Sailors": "users",
    "sailors": "users",
    "SAILORS": "users",
    "Boats": "products",
    "boats": "products",
    "BOATS": "products",
    "Reserves": "orders",
    "reserves": "orders",
    "RESERVES": "orders",
    "Invoices": "orders",
    "invoices": "orders",
    "INVOICES": "orders",
    "Invoice": "orders",
    "invoice": "orders",
    "INVOICE": "orders",
    "vendors": "users",
    "Vendors": "users",
    "VENDORS": "users",
    "vendor": "users",
    "Vendor": "users",
    "VENDOR": "users",
    "customers": "users",
    "Customers": "users",
    "CUSTOMERS": "users",
    "customer": "users",
    "Customer": "users",
    "CUSTOMER": "users",
    "items": "products",
    "Items": "products",
    "ITEMS": "products",
    "item": "products",
    "Item": "products",
    "ITEM": "products",
    "Staff": "employees",
    "staff": "employees",
    "STAFF": "employees",
    "worker": "employees",
    "Worker": "employees",
    "WORKER": "employees",
    "workers": "employees",
    "Workers": "employees",
    "WORKERS": "employees",
    "Divisions": "departments",
    "divisions": "departments",
    "DIVISIONS": "departments",
    "Division": "departments",
    "division": "departments",
    "DIVISION": "departments",
    "Teams": "departments",
    "teams": "departments",
    "TEAMS": "departments",
    # Column mappings
    "vendor_id": "user_id",
    "vendor_name": "name",
    "vendor_email": "email",
    "customer_id": "user_id",
    "customer_name": "name",
    "customer_email": "email",
    "invoice_total": "amount",
    "payment_total": "amount",
    "credit_total": "amount",
    "invoice_amount": "amount",
    "item_id": "id",
    "item_name": "name",
    "item_price": "price",
    "unit_price": "price",
    "sailor_id": "id",
    "sailor_name": "name",
    "boat_id": "id",
    "boat_name": "name",
    "bid": "id",
    "sid": "id",
    "rating": "age",
    "reserve_date": "hire_date",
    "day": "hire_date",
    "staff_id": "emp_id",
    "staff_name": "emp_name",
    "worker_id": "emp_id",
    "worker_name": "emp_name",
    "division_id": "dept_id",
    "division_name": "dept_name",
    "team_id": "dept_id",
    "team_name": "dept_name",
    "department_id": "dept_id",
    "department_name": "dept_name",
}


# =============================================================================
# CONCEPT TO PRACTICE PROBLEM MAPPING
# =============================================================================

CONCEPT_TO_PROBLEMS: dict[str, list[str]] = {
    "select-basic": ["problem-1", "problem-2", "problem-5"],
    "where-clause": ["problem-2", "problem-6", "problem-7"],
    "joins": ["problem-3", "problem-8", "problem-9", "problem-10"],
    "inner-join": ["problem-3", "problem-8"],
    "outer-join": ["problem-9", "problem-10"],
    "aggregate-functions": ["problem-4", "problem-11", "problem-12"],
    "aggregation": ["problem-4", "problem-11", "problem-12"],
    "group-by": ["problem-4", "problem-13", "problem-14"],
    "having": ["problem-14", "problem-15"],
    "subqueries": ["problem-16", "problem-17", "problem-18"],
    "correlated-subquery": ["problem-18", "problem-19"],
    "insert": ["problem-20", "problem-21"],
    "update": ["problem-22", "problem-23"],
    "delete": ["problem-24", "problem-25"],
    "create-table": ["problem-26", "problem-27"],
    "constraints": ["problem-26", "problem-28"],
    "primary-key": ["problem-26"],
    "foreign-key": ["problem-27", "problem-28"],
    "data-types": ["problem-26"],
    "order-by": ["problem-5", "problem-6"],
    "limit": ["problem-29"],
    "distinct": ["problem-30"],
    "null-handling": ["problem-31", "problem-32"],
    "string-functions": ["problem-33", "problem-34"],
    "date-functions": ["problem-35", "problem-36"],
    "views": ["problem-37"],
    "indexes": ["problem-38"],
}


# =============================================================================
# COMMON MISTAKES TEMPLATES BY CONCEPT
# =============================================================================

COMMON_MISTAKES_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "select-basic": [
        {
            "title": "Forgetting the FROM clause",
            "error_sql": "SELECT * WHERE age > 25;",
            "error_message": "Error: near 'WHERE': syntax error",
            "why_it_happens": "The FROM clause is required to specify which table to query. Without it, SQL doesn't know where to look for the 'age' column.",
            "fix_sql": "SELECT * FROM users WHERE age > 25;",
            "key_takeaway": "Always include FROM table_name after SELECT",
        },
        {
            "title": "Selecting all columns unnecessarily",
            "error_sql": "SELECT * FROM users;",
            "error_message": "No error, but inefficient",
            "why_it_happens": "Using * retrieves all columns, which can be slow with large tables and unnecessary data transfer.",
            "fix_sql": "SELECT id, name, email FROM users;",
            "key_takeaway": "Specify only the columns you need",
        },
    ],
    "where-clause": [
        {
            "title": "Using = instead of IN for multiple values",
            "error_sql": "SELECT * FROM users WHERE city = 'Seattle', 'Portland';",
            "error_message": "Error: near ',': syntax error",
            "why_it_happens": "The = operator only compares to a single value. For multiple values, use IN.",
            "fix_sql": "SELECT * FROM users WHERE city IN ('Seattle', 'Portland');",
            "key_takeaway": "Use IN for multiple possible values",
        },
        {
            "title": "String comparison without quotes",
            "error_sql": "SELECT * FROM users WHERE city = Seattle;",
            "error_message": "Error: no such column: Seattle",
            "why_it_happens": "Without quotes, SQL treats Seattle as a column name instead of a string value.",
            "fix_sql": "SELECT * FROM users WHERE city = 'Seattle';",
            "key_takeaway": "Always use quotes around string literals",
        },
    ],
    "joins": [
        {
            "title": "Missing JOIN condition (Cartesian product)",
            "error_sql": "SELECT * FROM users, orders;",
            "error_message": "No error, but returns too many rows",
            "why_it_happens": "Without a JOIN condition, every row in the first table is matched with every row in the second table.",
            "fix_sql": "SELECT * FROM users JOIN orders ON users.id = orders.user_id;",
            "key_takeaway": "Always specify the JOIN condition with ON",
        },
        {
            "title": "Ambiguous column reference",
            "error_sql": "SELECT name, product FROM users JOIN orders ON id = user_id;",
            "error_message": "Error: ambiguous column name: id",
            "why_it_happens": "Both tables have an 'id' column. SQL doesn't know which one to use in the comparison.",
            "fix_sql": "SELECT users.name, orders.product FROM users JOIN orders ON users.id = orders.user_id;",
            "key_takeaway": "Use table aliases or full table names for clarity",
        },
    ],
    "aggregate-functions": [
        {
            "title": "Mixing aggregate and non-aggregate columns",
            "error_sql": "SELECT city, COUNT(*) FROM users;",
            "error_message": "Error: misuse of aggregate function COUNT()",
            "why_it_happens": "When using aggregates, non-aggregate columns must be in a GROUP BY clause.",
            "fix_sql": "SELECT city, COUNT(*) FROM users GROUP BY city;",
            "key_takeaway": "All non-aggregated columns must be in GROUP BY",
        },
        {
            "title": "Using WHERE with aggregate conditions",
            "error_sql": "SELECT city, COUNT(*) FROM users WHERE COUNT(*) > 2 GROUP BY city;",
            "error_message": "Error: misuse of aggregate: COUNT()",
            "why_it_happens": "WHERE filters rows before aggregation. Use HAVING to filter after aggregation.",
            "fix_sql": "SELECT city, COUNT(*) FROM users GROUP BY city HAVING COUNT(*) > 2;",
            "key_takeaway": "Use HAVING, not WHERE, for aggregate conditions",
        },
    ],
    "group-by": [
        {
            "title": "Missing column in GROUP BY",
            "error_sql": "SELECT city, age, COUNT(*) FROM users GROUP BY city;",
            "error_message": "Error: column 'age' must appear in GROUP BY clause",
            "why_it_happens": "When grouping, any non-aggregated column in SELECT must be in GROUP BY.",
            "fix_sql": "SELECT city, age, COUNT(*) FROM users GROUP BY city, age;",
            "key_takeaway": "Include all non-aggregated columns in GROUP BY",
        },
    ],
    "subqueries": [
        {
            "title": "Subquery returns multiple rows for single-row operator",
            "error_sql": "SELECT * FROM users WHERE id = (SELECT user_id FROM orders);",
            "error_message": "Error: subquery returns more than one row",
            "why_it_happens": "The = operator expects a single value, but the subquery returns multiple rows.",
            "fix_sql": "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders);",
            "key_takeaway": "Use IN when the subquery may return multiple rows",
        },
    ],
    "insert": [
        {
            "title": "Wrong number of values",
            "error_sql": "INSERT INTO users VALUES (1, 'Alice');",
            "error_message": "Error: table users has 5 columns but 2 values were supplied",
            "why_it_happens": "When not specifying columns, VALUES must include all columns in order.",
            "fix_sql": "INSERT INTO users (id, name) VALUES (1, 'Alice');",
            "key_takeaway": "Specify columns when inserting partial rows",
        },
    ],
    "update": [
        {
            "title": "Missing WHERE clause in UPDATE",
            "error_sql": "UPDATE users SET age = 30;",
            "error_message": "No error, but updates ALL rows!",
            "why_it_happens": "Without WHERE, the UPDATE applies to every row in the table.",
            "fix_sql": "UPDATE users SET age = 30 WHERE id = 1;",
            "key_takeaway": "Always include WHERE in UPDATE statements",
        },
    ],
    "delete": [
        {
            "title": "Missing WHERE clause in DELETE",
            "error_sql": "DELETE FROM users;",
            "error_message": "No error, but deletes ALL rows!",
            "why_it_happens": "Without WHERE, DELETE removes every row in the table.",
            "fix_sql": "DELETE FROM users WHERE id = 1;",
            "key_takeaway": "Always include WHERE in DELETE statements",
        },
    ],
}


# =============================================================================
# PRACTICE CHALLENGE TEMPLATES BY CONCEPT
# =============================================================================

PRACTICE_CHALLENGES: dict[str, dict[str, Any]] = {
    "select-basic": {
        "description": "Write a query to find all users from 'Seattle' who are older than 25.",
        "hint": "Use WHERE with AND to combine conditions.",
        "solution": "SELECT * FROM users WHERE city = 'Seattle' AND age > 25;",
        "explanation": "This query filters for users where both conditions are true: city is 'Seattle' AND age is greater than 25.",
    },
    "where-clause": {
        "description": "Find all users whose email ends with '@email.com' and are under 30.",
        "hint": "Use LIKE for pattern matching with the % wildcard.",
        "solution": "SELECT * FROM users WHERE email LIKE '%@email.com' AND age < 30;",
        "explanation": "LIKE '%@email.com' matches any string ending with '@email.com'. The AND operator ensures both conditions are met.",
    },
    "joins": {
        "description": "List all users who have placed orders, showing their name and the total amount they've spent.",
        "hint": "JOIN users with orders, then use SUM and GROUP BY.",
        "solution": """SELECT u.name, SUM(o.amount) as total_spent
FROM users u
JOIN orders o ON u.id = o.user_id
GROUP BY u.id, u.name;""",
        "explanation": "We JOIN to get related orders, then GROUP BY user to aggregate, and SUM the order amounts.",
    },
    "aggregate-functions": {
        "description": "Find the average age of users in each city.",
        "hint": "Use AVG with GROUP BY.",
        "solution": "SELECT city, AVG(age) as avg_age FROM users GROUP BY city;",
        "explanation": "AVG calculates the average age, and GROUP BY city computes it separately for each city.",
    },
    "group-by": {
        "description": "Find cities that have more than 2 users, ordered by user count.",
        "hint": "Use GROUP BY with HAVING and ORDER BY.",
        "solution": """SELECT city, COUNT(*) as user_count
FROM users
GROUP BY city
HAVING COUNT(*) > 2
ORDER BY user_count DESC;""",
        "explanation": "GROUP BY groups users by city, HAVING filters groups with more than 2 users, and ORDER BY sorts the results.",
    },
    "subqueries": {
        "description": "Find users who have not placed any orders.",
        "hint": "Use NOT EXISTS or NOT IN with a subquery.",
        "solution": """SELECT * FROM users u
WHERE NOT EXISTS (
    SELECT 1 FROM orders o WHERE o.user_id = u.id
);""",
        "explanation": "The subquery checks for orders for each user. NOT EXISTS returns users where no matching orders are found.",
    },
    "insert": {
        "description": "Add a new user with name 'Grace', email 'grace@email.com', age 27, city 'Austin'.",
        "hint": "Use INSERT INTO with column names and VALUES.",
        "solution": "INSERT INTO users (name, email, age, city) VALUES ('Grace', 'grace@email.com', 27, 'Austin');",
        "explanation": "We specify the columns and provide values in the same order. The id may auto-generate or we can include it.",
    },
    "update": {
        "description": "Increase the salary of all employees in the Engineering department by 10%.",
        "hint": "Use UPDATE with a subquery or JOIN to find Engineering dept_id.",
        "solution": """UPDATE employees
SET salary = salary * 1.10
WHERE dept_id = (SELECT dept_id FROM departments WHERE dept_name = 'Engineering');""",
        "explanation": "The subquery finds the Engineering department ID, and UPDATE modifies only matching employees' salaries.",
    },
    "delete": {
        "description": "Delete all orders with amount less than 50.",
        "hint": "Use DELETE FROM with a WHERE clause.",
        "solution": "DELETE FROM orders WHERE amount < 50;",
        "explanation": "The WHERE clause ensures only orders with amount less than 50 are deleted.",
    },
}


# =============================================================================
# LEARNING OBJECTIVES BY CONCEPT
# =============================================================================

LEARNING_OBJECTIVES: dict[str, list[str]] = {
    "select-basic": [
        "Understand the basic structure of a SELECT statement",
        "Retrieve specific columns vs all columns using *",
        "Use table aliases for cleaner queries",
    ],
    "where-clause": [
        "Filter rows using comparison operators (=, <, >, <=, >=, <>)",
        "Combine conditions with AND, OR, and NOT",
        "Use LIKE for pattern matching with wildcards",
        "Handle NULL values correctly with IS NULL / IS NOT NULL",
    ],
    "joins": [
        "Understand the difference between INNER and OUTER joins",
        "Write proper JOIN conditions with ON clause",
        "Know when to use each type of join",
        "Avoid common join pitfalls like Cartesian products",
    ],
    "aggregate-functions": [
        "Use COUNT, SUM, AVG, MAX, MIN for calculations",
        "Understand the difference between COUNT(*) and COUNT(column)",
        "Combine aggregates with other SQL features",
    ],
    "group-by": [
        "Group rows by one or more columns",
        "Apply aggregate functions to groups",
        "Use HAVING to filter groups based on aggregate values",
        "Understand the execution order of GROUP BY and HAVING",
    ],
    "subqueries": [
        "Write subqueries in SELECT, FROM, and WHERE clauses",
        "Understand correlated vs non-correlated subqueries",
        "Use EXISTS and IN operators with subqueries",
        "Know when to use subqueries vs joins",
    ],
    "insert": [
        "Insert single rows with specific column values",
        "Insert multiple rows in a single statement",
        "Insert data from one table into another",
    ],
    "update": [
        "Modify existing data with UPDATE statements",
        "Use subqueries in UPDATE statements",
        "Update multiple columns simultaneously",
    ],
    "delete": [
        "Remove rows safely with DELETE statements",
        "Use subqueries to determine which rows to delete",
        "Understand the difference between DELETE and TRUNCATE",
    ],
}


# =============================================================================
# PREREQUISITE CONCEPTS MAPPING
# =============================================================================

PREREQUISITE_CONCEPTS: dict[str, list[str]] = {
    "select-basic": [],
    "where-clause": ["select-basic"],
    "joins": ["select-basic", "where-clause"],
    "inner-join": ["select-basic", "joins"],
    "outer-join": ["select-basic", "joins", "inner-join"],
    "aggregate-functions": ["select-basic"],
    "group-by": ["select-basic", "aggregate-functions"],
    "having": ["select-basic", "aggregate-functions", "group-by"],
    "subqueries": ["select-basic", "where-clause"],
    "correlated-subquery": ["select-basic", "subqueries"],
    "insert": ["select-basic"],
    "update": ["select-basic", "where-clause"],
    "delete": ["select-basic", "where-clause"],
    "create-table": [],
    "constraints": ["create-table"],
    "primary-key": ["create-table", "constraints"],
    "foreign-key": ["create-table", "constraints", "primary-key"],
}


# =============================================================================
# PEDAGOGICAL CONTENT GENERATOR
# =============================================================================

class PedagogicalContentGenerator:
    """
    Generates pedagogically structured educational content from raw PDF textbook chunks.
    
    This class transforms textbook content that uses academic schemas (Sailors, Boats, etc.)
    into student-ready content using standardized practice schemas (users, orders, products, etc.)
    
    Features:
    - Schema transformation (textbook → practice schemas)
    - Pedagogical structure with learning objectives and prerequisites
    - Realistic common mistakes with error messages
    - Practice challenges using consistent schemas
    - Markdown generation with proper formatting
    """
    
    def __init__(
        self,
        practice_schemas: dict[str, dict] | None = None,
        schema_mapping: dict[str, str] | None = None,
    ):
        """
        Initialize the pedagogical content generator.
        
        Args:
            practice_schemas: Dictionary of practice schema definitions.
                Defaults to PRACTICE_SCHEMAS if not provided.
            schema_mapping: Dictionary mapping textbook terms to practice schemas.
                Defaults to TEXTBOOK_TO_PRACTICE_MAPPING if not provided.
        """
        self.practice_schemas = practice_schemas or PRACTICE_SCHEMAS
        self.schema_mapping = schema_mapping or TEXTBOOK_TO_PRACTICE_MAPPING
    
    def transform_textbook_example(self, raw_sql: str, concept_id: str) -> dict[str, Any]:
        """
        Convert textbook SQL example to practice-schema SQL.
        
        Args:
            raw_sql: SQL code from textbook using academic schemas
            concept_id: The concept ID for context
            
        Returns:
            Dictionary with transformed SQL and metadata
        """
        if not raw_sql or not raw_sql.strip():
            return {
                "original": raw_sql,
                "transformed": "",
                "schema_mappings_used": [],
                "error": "Empty SQL provided",
            }
        
        transformed_sql = raw_sql
        mappings_used: list[str] = []
        
        # Replace table names (whole word only, case-sensitive first)
        for old_term, new_term in self.schema_mapping.items():
            # Skip column mappings on first pass (handle tables only)
            if "_" in old_term and old_term.lower() == old_term:
                continue
                
            # Use word boundary matching for table names
            pattern = r'\b' + re.escape(old_term) + r'\b'
            if re.search(pattern, transformed_sql, re.IGNORECASE):
                transformed_sql = re.sub(pattern, new_term, transformed_sql, flags=re.IGNORECASE)
                mappings_used.append(f"{old_term} → {new_term}")
        
        # Replace column names (whole word only)
        for old_term, new_term in self.schema_mapping.items():
            # Skip table mappings (handle columns only)
            if "_" not in old_term:
                continue
                
            pattern = r'\b' + re.escape(old_term) + r'\b'
            if re.search(pattern, transformed_sql, re.IGNORECASE):
                transformed_sql = re.sub(pattern, new_term, transformed_sql, flags=re.IGNORECASE)
                mappings_used.append(f"{old_term} → {new_term}")
        
        # Clean up any artifacts
        transformed_sql = self._clean_sql_transform(transformed_sql)
        
        return {
            "original": raw_sql,
            "transformed": transformed_sql,
            "schema_mappings_used": mappings_used,
            "runnable": self._is_runnable(transformed_sql),
        }
    
    def _clean_sql_transform(self, sql: str) -> str:
        """Clean up any artifacts from SQL transformation."""
        # Fix double spaces
        sql = re.sub(r'\s+', ' ', sql)
        # Fix spacing around punctuation
        sql = re.sub(r'\s*;\s*$', ';', sql)
        sql = re.sub(r'\s*\(', ' (', sql)
        sql = re.sub(r'\(\s+', '(', sql)
        sql = re.sub(r'\s+\)', ')', sql)
        return sql.strip()
    
    def _is_runnable(self, sql: str) -> bool:
        """Check if SQL appears to be runnable (basic validation)."""
        sql_upper = sql.upper().strip()
        
        # Must start with a valid SQL keyword
        valid_starts = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'WITH']
        has_valid_start = any(sql_upper.startswith(kw) for kw in valid_starts)
        
        # Must end with semicolon
        ends_with_semicolon = sql.rstrip().endswith(';')
        
        # Must not contain obvious error patterns
        no_obvious_errors = not any(
            pattern in sql_upper for pattern in
            ['FROM FROM', 'WHERE WHERE', 'SELECT SELECT', ';;']
        )
        
        return has_valid_start and ends_with_semicolon and no_obvious_errors
    
    def generate_expected_output(self, sql: str, schema_name: str = "users") -> str:
        """
        Generate markdown table of expected output for a SELECT query.
        
        Args:
            sql: The SQL query
            schema_name: The primary schema being queried
            
        Returns:
            Markdown table as string, or empty string if not a SELECT
        """
        sql_upper = sql.upper().strip()
        
        if not sql_upper.startswith('SELECT'):
            return ""
        
        # Get schema info
        schema = self.practice_schemas.get(schema_name, self.practice_schemas["users"])
        columns = schema["columns"]
        sample_data = schema["sample_data"][:3]  # First 3 rows
        
        # Build markdown table
        header = " | ".join(columns)
        separator = " | ".join(["---"] * len(columns))
        
        rows = []
        for row_data in sample_data:
            row_str = " | ".join(str(val) if val is not None else "NULL" for val in row_data)
            rows.append(row_str)
        
        return f"""| {header} |
| {separator} |
| {' |\n| '.join(rows)} |"""
    
    def generate_pedagogical_concept(
        self,
        concept_id: str,
        concept_title: str,
        raw_chunks: list[dict],
        practice_problem_links: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Generate complete pedagogical concept from raw PDF chunks.
        
        Args:
            concept_id: Unique identifier for the concept
            concept_title: Human-readable title
            raw_chunks: List of raw text chunks from PDF extraction
            practice_problem_links: Optional list of problem IDs to link
            
        Returns:
            Complete pedagogical concept structure
        """
        # Combine raw chunks
        combined_text = "\n\n".join(
            chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
            for chunk in raw_chunks
        )
        
        # Extract SQL examples from raw text
        raw_examples = self._extract_sql_examples(combined_text)
        
        # Transform examples to use practice schemas
        transformed_examples = []
        for ex in raw_examples[:3]:  # Limit to 3 examples
            transformed = self.transform_textbook_example(ex["code"], concept_id)
            if transformed["runnable"]:
                transformed_examples.append({
                    "title": ex.get("title", "Example"),
                    "difficulty": self._estimate_difficulty(transformed["transformed"]),
                    "scenario": self._generate_scenario(transformed["transformed"]),
                    "sql": transformed["transformed"],
                    "explanation": ex.get("explanation", self._generate_explanation(transformed["transformed"])),
                    "expected_output": self.generate_expected_output(transformed["transformed"]),
                })
        
        # If no valid examples found, generate a default one
        if not transformed_examples:
            transformed_examples = self._generate_default_examples(concept_id)
        
        # Get learning objectives
        learning_objectives = LEARNING_OBJECTIVES.get(
            concept_id,
            [f"Understand the {concept_title} concept in SQL"]
        )
        
        # Get prerequisites
        prerequisites = PREREQUISITE_CONCEPTS.get(concept_id, [])
        
        # Get or generate practice problem links
        problem_links = practice_problem_links or CONCEPT_TO_PROBLEMS.get(concept_id, [])
        
        # Build the concept structure
        concept = {
            "concept_id": concept_id,
            "title": concept_title,
            "learning_objectives": learning_objectives,
            "prerequisite_concepts": prerequisites,
            "practice_problems": problem_links,
            "sections": {
                "definition": {
                    "concept_explanation": self._generate_definition(concept_id, concept_title, combined_text),
                    "visual_diagram": self._generate_diagram(concept_id),
                },
                "examples": transformed_examples,
                "common_mistakes": self.generate_common_mistakes(concept_id),
                "practice_challenge": self.generate_practice_challenge(concept_id),
            },
            "metadata": {
                "difficulty": self._estimate_overall_difficulty(concept_id),
                "estimated_time_minutes": self._estimate_time(concept_id),
                "source_chunks": len(raw_chunks),
            }
        }
        
        return concept
    
    def _extract_sql_examples(self, text: str) -> list[dict]:
        """Extract SQL examples from raw text."""
        examples = []
        
        # Pattern for SQL code blocks
        code_block_pattern = r'```sql\s*\n(.*?)\n```'
        for match in re.finditer(code_block_pattern, text, re.DOTALL | re.IGNORECASE):
            code = match.group(1).strip()
            if len(code) > 10:
                examples.append({
                    "title": "SQL Example",
                    "code": code,
                    "explanation": "Example from textbook",
                })
        
        # Pattern for inline SQL statements
        sql_pattern = r'(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP)\s+[^;]{10,500};'
        matches = list(re.finditer(sql_pattern, text, re.IGNORECASE | re.DOTALL))
        
        for i, match in enumerate(matches[:3], 1):
            code = match.group(0)
            # Clean up the code
            code = re.sub(r'\s+', ' ', code).strip()
            
            # Skip if already found in code blocks
            if not any(ex["code"] == code for ex in examples):
                examples.append({
                    "title": f"SQL Example {i}",
                    "code": code,
                    "explanation": "Example SQL statement",
                })
        
        return examples
    
    def _generate_default_examples(self, concept_id: str) -> list[dict]:
        """Generate default examples for a concept if none found in text."""
        defaults: dict[str, list[dict]] = {
            "select-basic": [
                {
                    "title": "Basic SELECT",
                    "difficulty": "beginner",
                    "scenario": "Retrieve all information about users",
                    "sql": "SELECT * FROM users;",
                    "explanation": "The * wildcard selects all columns from the table.",
                    "expected_output": self.generate_expected_output("SELECT * FROM users;"),
                },
                {
                    "title": "Select Specific Columns",
                    "difficulty": "beginner",
                    "scenario": "Get just the names and emails of all users",
                    "sql": "SELECT name, email FROM users;",
                    "explanation": "Specify column names to retrieve only the data you need.",
                    "expected_output": "| name | email |\n| --- | --- |\n| Alice | alice@email.com |\n| Bob | bob@email.com |",
                },
            ],
            "joins": [
                {
                    "title": "Inner Join",
                    "difficulty": "beginner",
                    "scenario": "Find users and their orders",
                    "sql": "SELECT u.name, o.product, o.amount FROM users u JOIN orders o ON u.id = o.user_id;",
                    "explanation": "JOIN combines rows from two tables based on a related column.",
                    "expected_output": "| name | product | amount |\n| --- | --- | --- |\n| Alice | Laptop | 999.99 |\n| Alice | Mouse | 29.99 |",
                },
            ],
        }
        
        return defaults.get(concept_id, [{
            "title": f"Example for {concept_id}",
            "difficulty": "beginner",
            "scenario": "Basic usage example",
            "sql": "SELECT * FROM users LIMIT 5;",
            "explanation": "See the practice problems for more examples.",
            "expected_output": self.generate_expected_output("SELECT * FROM users LIMIT 5;"),
        }])
    
    def _estimate_difficulty(self, sql: str) -> str:
        """Estimate difficulty of an SQL query."""
        sql_upper = sql.upper()
        score = 0
        
        # Complexity indicators
        if 'JOIN' in sql_upper:
            score += 1
        if 'GROUP BY' in sql_upper:
            score += 1
        if 'SUBQUERY' in sql_upper or 'SELECT' in sql_upper and sql_upper.count('SELECT') > 1:
            score += 2
        if 'EXISTS' in sql_upper or 'CORRELATED' in sql_upper:
            score += 2
        if sql_upper.count('(') > 2:
            score += 1
        
        if score >= 4:
            return "advanced"
        elif score >= 2:
            return "intermediate"
        return "beginner"
    
    def _estimate_overall_difficulty(self, concept_id: str) -> str:
        """Estimate overall difficulty for a concept."""
        difficulty_map = {
            "select-basic": "beginner",
            "where-clause": "beginner",
            "insert": "beginner",
            "update": "beginner",
            "delete": "beginner",
            "data-types": "beginner",
            "joins": "intermediate",
            "inner-join": "beginner",
            "outer-join": "intermediate",
            "aggregate-functions": "intermediate",
            "group-by": "intermediate",
            "having": "intermediate",
            "subqueries": "intermediate",
            "correlated-subquery": "advanced",
            "views": "intermediate",
            "indexes": "intermediate",
            "transactions": "advanced",
            "isolation-levels": "advanced",
        }
        return difficulty_map.get(concept_id, "intermediate")
    
    def _estimate_time(self, concept_id: str) -> int:
        """Estimate learning time in minutes."""
        time_map = {
            "select-basic": 10,
            "where-clause": 15,
            "joins": 20,
            "aggregate-functions": 15,
            "group-by": 20,
            "subqueries": 25,
            "correlated-subquery": 30,
        }
        return time_map.get(concept_id, 15)
    
    def _generate_scenario(self, sql: str) -> str:
        """Generate a real-world scenario description for SQL."""
        sql_lower = sql.lower()
        
        if "users" in sql_lower and "orders" in sql_lower:
            return "Finding customer purchase information"
        elif "employees" in sql_lower and "departments" in sql_lower:
            return "Analyzing employee and department data"
        elif "group by" in sql_lower:
            return "Aggregating data for reporting"
        elif "join" in sql_lower:
            return "Combining data from multiple tables"
        elif "where" in sql_lower:
            return "Filtering data based on conditions"
        else:
            return "Basic data retrieval"
    
    def _generate_explanation(self, sql: str) -> str:
        """Generate a basic explanation for SQL code."""
        sql_upper = sql.upper()
        
        if "SELECT" in sql_upper and "JOIN" in sql_upper:
            return "This query joins tables to combine related data."
        elif "GROUP BY" in sql_upper:
            return "This query groups data for aggregate calculations."
        elif "WHERE" in sql_upper:
            return "This query filters rows based on specified conditions."
        elif "INSERT" in sql_upper:
            return "This statement adds new data to the table."
        elif "UPDATE" in sql_upper:
            return "This statement modifies existing data."
        else:
            return "This SQL performs the specified operation."
    
    def _generate_definition(self, concept_id: str, title: str, raw_text: str) -> str:
        """Generate a clear definition from raw text."""
        # Try to extract a sentence that looks like a definition
        sentences = re.split(r'(?<=[.!?])\s+', raw_text)
        
        for sent in sentences[:5]:
            sent = sent.strip()
            if len(sent) > 50 and len(sent) < 300:
                # Look for definition-like patterns
                if any(word in sent.lower() for word in ['is a', 'is an', 'refers to', 'allows you', 'used to']):
                    return sent
        
        # Fallback to generated definition
        definitions = {
            "select-basic": "The SELECT statement is the foundation of SQL queries, allowing you to retrieve data from one or more tables.",
            "where-clause": "The WHERE clause filters query results by specifying conditions that rows must meet.",
            "joins": "JOIN operations combine rows from two or more tables based on related columns.",
            "aggregate-functions": "Aggregate functions perform calculations on sets of values and return a single result.",
            "group-by": "GROUP BY organizes rows with the same values into summary rows for aggregate calculations.",
        }
        return definitions.get(concept_id, f"{title} is an important SQL concept for working with databases.")
    
    def _generate_diagram(self, concept_id: str) -> str:
        """Generate an ASCII diagram if applicable."""
        diagrams = {
            "joins": """
    users                    orders
    +----+-------+           +----------+--------+--------+
    | id | name  |           | order_id |user_id |product |
    +----+-------+           +----------+--------+--------+
    |  1 | Alice |<--------->|   101    |   1    | Laptop |
    |  2 | Bob   |<--------->|   102    |   1    | Mouse  |
    +----+-------+           +----------+--------+--------+
            INNER JOIN matches rows where id = user_id
            """,
            "inner-join": """
    users (LEFT)    INNER JOIN    orders (RIGHT)
    +----+------+                  +----------+--------+
    |  1 |Alice |<---------------->| order_id |user_id |
    |  2 |Bob   |<---------------->|   101    |   1    |
    |  3 |Carol |   (no match)     |   102    |   1    |
    +----+------+                  +----------+--------+
    Result: Only rows with matches in BOTH tables
            """,
            "outer-join": """
    users (LEFT)    LEFT JOIN     orders (RIGHT)
    +----+------+                  +----------+--------+
    |  1 |Alice |<---------------->| order_id |user_id |
    |  2 |Bob   |<---------------->|   101    |   1    |
    |  3 |Carol |  (included with  |   102    |   1    |
    +----+------+       NULL)      +----------+--------+
    Result: ALL left rows, matched with right or NULL
            """,
        }
        return diagrams.get(concept_id, "")
    
    def generate_common_mistakes(self, concept_id: str) -> list[dict]:
        """
        Generate realistic common mistakes for this concept.
        
        Args:
            concept_id: The concept identifier
            
        Returns:
            List of common mistake structures
        """
        templates = COMMON_MISTAKES_TEMPLATES.get(concept_id, [])
        
        if templates:
            return templates
        
        # Generic fallback mistakes
        return [
            {
                "title": "Syntax error",
                "error_sql": "SELECT * FORM users;",
                "error_message": "Error: near 'FORM': syntax error",
                "why_it_happens": "Typo in SQL keyword. The correct keyword is FROM, not FORM.",
                "fix_sql": "SELECT * FROM users;",
                "key_takeaway": "Double-check SQL keyword spelling",
            },
            {
                "title": "Missing semicolon",
                "error_sql": "SELECT * FROM users",
                "error_message": "Some databases require semicolons to end statements",
                "why_it_happens": "While some SQL implementations are lenient, it's best practice to end statements with semicolons.",
                "fix_sql": "SELECT * FROM users;",
                "key_takeaway": "Always end SQL statements with a semicolon",
            },
        ]
    
    def generate_practice_challenge(self, concept_id: str) -> dict[str, Any]:
        """
        Generate mini-exercise using practice schemas.
        
        Args:
            concept_id: The concept identifier
            
        Returns:
            Practice challenge structure
        """
        challenge = PRACTICE_CHALLENGES.get(concept_id)
        
        if challenge:
            return challenge
        
        # Default challenge
        return {
            "description": f"Practice using {concept_id} with the practice schemas.",
            "hint": "Review the examples above and try writing your own query.",
            "solution": "SELECT * FROM users LIMIT 5;",
            "explanation": "This is a basic query to get you started. See the linked practice problems for more challenges.",
        }
    
    def generate_markdown(self, concept: dict[str, Any]) -> str:
        """
        Generate final markdown with proper formatting.
        
        Args:
            concept: The pedagogical concept structure
            
        Returns:
            Formatted markdown string
        """
        lines: list[str] = []
        
        # Title and metadata
        lines.append(f"# {concept['title']}")
        lines.append("")
        
        difficulty = concept.get("metadata", {}).get("difficulty", "intermediate")
        time_estimate = concept.get("metadata", {}).get("estimated_time_minutes", 15)
        
        emoji = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}.get(difficulty, "⚪")
        lines.append(f"{emoji} **Difficulty:** {difficulty.title()}")
        lines.append(f"⏱️ **Estimated Time:** {time_estimate} minutes")
        lines.append("")
        
        # Learning Objectives
        lines.append("## Learning Objectives")
        lines.append("")
        for obj in concept.get("learning_objectives", []):
            lines.append(f"- {obj}")
        lines.append("")
        
        # Prerequisites
        prereqs = concept.get("prerequisite_concepts", [])
        if prereqs:
            lines.append("## Prerequisites")
            lines.append("")
            lines.append("Before learning this concept, you should understand:")
            lines.append("")
            for prereq in prereqs:
                lines.append(f"- [{prereq}](./{prereq}.md)")
            lines.append("")
        
        # Definition
        definition_section = concept.get("sections", {}).get("definition", {})
        lines.append("## What is This?")
        lines.append("")
        lines.append(definition_section.get("concept_explanation", ""))
        lines.append("")
        
        # Visual diagram if available
        diagram = definition_section.get("visual_diagram", "").strip()
        if diagram:
            lines.append("### Visual Diagram")
            lines.append("")
            lines.append("```")
            lines.append(diagram)
            lines.append("```")
            lines.append("")
        
        # Examples
        lines.append("## Examples")
        lines.append("")
        
        examples = concept.get("sections", {}).get("examples", [])
        if examples:
            for i, ex in enumerate(examples, 1):
                lines.append(f"### Example {i}: {ex.get('title', 'SQL Example')}")
                lines.append("")
                lines.append(f"**Difficulty:** {ex.get('difficulty', 'beginner').title()}")
                lines.append("")
                lines.append(f"**Scenario:** {ex.get('scenario', 'Data retrieval')}")
                lines.append("")
                lines.append("```sql")
                lines.append(ex.get("sql", ""))
                lines.append("```")
                lines.append("")
                lines.append(f"**Explanation:** {ex.get('explanation', '')}")
                lines.append("")
                
                # Expected output
                expected = ex.get("expected_output", "")
                if expected:
                    lines.append("**Expected Output:**")
                    lines.append("")
                    lines.append(expected)
                    lines.append("")
        else:
            lines.append("*No examples available for this concept.*")
            lines.append("")
        
        # Common Mistakes
        lines.append("## Common Mistakes")
        lines.append("")
        
        mistakes = concept.get("sections", {}).get("common_mistakes", [])
        if mistakes:
            for i, m in enumerate(mistakes, 1):
                lines.append(f"### Mistake {i}: {m.get('title', 'Error')}")
                lines.append("")
                lines.append("**Incorrect SQL:**")
                lines.append("```sql")
                lines.append(m.get("error_sql", ""))
                lines.append("```")
                lines.append("")
                lines.append(f"**Error Message:** `{m.get('error_message', 'Error')}`")
                lines.append("")
                lines.append(f"**Why it happens:** {m.get('why_it_happens', '')}")
                lines.append("")
                lines.append("**Corrected SQL:**")
                lines.append("```sql")
                lines.append(m.get("fix_sql", ""))
                lines.append("```")
                lines.append("")
                lines.append(f"💡 **Key Takeaway:** {m.get('key_takeaway', '')}")
                lines.append("")
        else:
            lines.append("*No common mistakes documented.*")
            lines.append("")
        
        # Practice Challenge
        lines.append("## Practice Challenge")
        lines.append("")
        
        challenge = concept.get("sections", {}).get("practice_challenge", {})
        lines.append(f"**{challenge.get('description', 'Practice this concept')}**")
        lines.append("")
        lines.append(f"💡 **Hint:** {challenge.get('hint', 'Try it yourself!')}")
        lines.append("")
        lines.append("<details>")
        lines.append("<summary>Click to see solution</summary>")
        lines.append("")
        lines.append("```sql")
        lines.append(challenge.get("solution", ""))
        lines.append("```")
        lines.append("")
        lines.append(f"**Explanation:** {challenge.get('explanation', '')}")
        lines.append("</details>")
        lines.append("")
        
        # Practice Problems
        problems = concept.get("practice_problems", [])
        if problems:
            lines.append("## Related Practice Problems")
            lines.append("")
            for prob_id in problems:
                lines.append(f"- [{prob_id}](/practice/{prob_id})")
            lines.append("")
        
        # Footer
        lines.append("---")
        lines.append("")
        lines.append("*Content generated for SQL-Adapt Learning Platform*")
        lines.append("")
        
        return "\n".join(lines)
    
    def generate_schema_reference(self) -> str:
        """
        Generate a markdown reference for all practice schemas.
        
        Returns:
            Markdown documentation of practice schemas
        """
        lines: list[str] = [
            "# Practice Schema Reference",
            "",
            "This document describes the standardized schemas used throughout the SQL-Adapt learning platform.",
            "",
        ]
        
        for table_name, schema in self.practice_schemas.items():
            lines.append(f"## {table_name.upper()}")
            lines.append("")
            lines.append(f"**Description:** {schema.get('description', '')}")
            lines.append("")
            
            # Columns
            lines.append("### Columns")
            lines.append("")
            lines.append("| Column | Type | Description |")
            lines.append("|--------|------|-------------|")
            
            for col in schema["columns"]:
                col_type = "INTEGER" if col.endswith("_id") or col in ["id", "age"] else "TEXT"
                if col in ["amount", "price", "salary"]:
                    col_type = "REAL"
                lines.append(f"| {col} | {col_type} | |")
            lines.append("")
            
            # Sample Data
            lines.append("### Sample Data")
            lines.append("")
            header = " | ".join(schema["columns"])
            separator = " | ".join(["---"] * len(schema["columns"]))
            lines.append(f"| {header} |")
            lines.append(f"| {separator} |")
            
            for row in schema["sample_data"]:
                row_str = " | ".join(str(val) if val is not None else "NULL" for val in row)
                lines.append(f"| {row_str} |")
            lines.append("")
            
            # Keys
            lines.append("### Keys")
            lines.append("")
            lines.append(f"- **Primary Key:** {schema.get('primary_key', 'id')}")
            
            foreign_keys = schema.get("foreign_keys", {})
            if foreign_keys:
                for col, ref in foreign_keys.items():
                    lines.append(f"- **Foreign Key:** {col} → {ref}")
            lines.append("")
        
        return "\n".join(lines)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def transform_sql_file(
    input_path: str,
    output_path: str,
    generator: PedagogicalContentGenerator | None = None,
) -> dict[str, Any]:
    """
    Transform an entire SQL file from textbook schemas to practice schemas.
    
    Args:
        input_path: Path to input SQL file
        output_path: Path to output SQL file
        generator: Optional PedagogicalContentGenerator instance
        
    Returns:
        Summary of transformations performed
    """
    if generator is None:
        generator = PedagogicalContentGenerator()
    
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split into statements (basic split by semicolon)
    statements = content.split(';')
    
    transformed_statements = []
    all_mappings: set[str] = set()
    
    for stmt in statements:
        stmt = stmt.strip()
        if not stmt:
            continue
            
        result = generator.transform_textbook_example(stmt + ';', 'batch-transform')
        transformed_statements.append(result['transformed'])
        all_mappings.update(result['schema_mappings_used'])
    
    # Write output
    output_sql = '\n\n'.join(transformed_statements)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output_sql)
    
    return {
        "input_path": input_path,
        "output_path": output_path,
        "statements_processed": len(transformed_statements),
        "unique_mappings": sorted(list(all_mappings)),
    }


def generate_concept_markdown_file(
    concept_id: str,
    concept_title: str,
    raw_chunks: list[dict],
    output_path: str,
    generator: PedagogicalContentGenerator | None = None,
) -> str:
    """
    Generate and save pedagogical concept markdown to a file.
    
    Args:
        concept_id: Unique identifier for the concept
        concept_title: Human-readable title
        raw_chunks: List of raw text chunks from PDF extraction
        output_path: Path to save the markdown file
        generator: Optional PedagogicalContentGenerator instance
        
    Returns:
        Path to the generated file
    """
    if generator is None:
        generator = PedagogicalContentGenerator()
    
    concept = generator.generate_pedagogical_concept(
        concept_id=concept_id,
        concept_title=concept_title,
        raw_chunks=raw_chunks,
    )
    
    markdown = generator.generate_markdown(concept)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    return output_path
