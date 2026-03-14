"""
Central Schema Definitions for ALGL PDF Helper.

This module provides centralized schema definitions used across the codebase,
including practice schemas for SQL validation and foreign key mappings.

Usage:
    from algl_pdf_helper.schemas import PRACTICE_SCHEMAS, FOREIGN_KEY_MAPPINGS
    
    # Access schema definitions
    users_schema = PRACTICE_SCHEMAS["users"]
    
    # Access FK relationships
    fk_mapping = FOREIGN_KEY_MAPPINGS["users"]["orders"]
"""

from __future__ import annotations

from typing import Any


# =============================================================================
# FOREIGN KEY MAPPINGS - For proper join condition transformation
# =============================================================================

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
}


# =============================================================================
# CONCEPT TO PROBLEMS MAPPING
# =============================================================================

CONCEPT_TO_PROBLEMS: dict[str, list[str]] = {
    "select-basic": ["sql-select-basics-001", "sql-select-columns-002"],
    "where-clause": ["sql-where-basics-001", "sql-where-operators-002"],
    "joins": ["sql-join-intro-001", "sql-join-types-002"],
    "inner-join": ["sql-inner-join-001"],
    "outer-join": ["sql-outer-join-001", "sql-left-join-002"],
    "aggregate-functions": ["sql-aggregate-intro-001", "sql-count-002"],
    "group-by": ["sql-group-by-001", "sql-group-filter-002"],
    "subqueries": ["sql-subquery-intro-001"],
    "order-by": ["sql-order-by-001"],
}


# =============================================================================
# PRACTICE SCHEMAS FOR SPECIFIC PROBLEMS
# =============================================================================

PRACTICE_SCHEMAS_BY_PROBLEM: dict[str, dict[str, Any]] = {
    "default": PRACTICE_SCHEMAS,
}


def get_schema_for_concept(concept_id: str) -> dict[str, Any]:
    """
    Get the appropriate practice schema for a concept.
    
    Args:
        concept_id: The concept ID to get schema for
        
    Returns:
        Schema dictionary for the concept (defaults to standard schemas)
    """
    # Currently returns default schemas for all concepts
    # Can be extended to return specialized schemas for specific concepts
    return PRACTICE_SCHEMAS


def get_schema_graph() -> dict[str, Any]:
    """
    Build a graph representation of schema relationships.
    
    Returns:
        Dictionary with tables, relationships, and join paths
    """
    graph = {
        "tables": {},
        "relationships": [],
        "join_paths": {},
    }
    
    # Build table info
    for table_name, table_schema in PRACTICE_SCHEMAS.items():
        graph["tables"][table_name] = {
            "columns": table_schema.get("columns", []),
            "primary_key": table_schema.get("primary_key", "id"),
            "foreign_keys": table_schema.get("foreign_keys", {}),
        }
    
    # Build relationships from foreign keys
    for table_name, table_schema in PRACTICE_SCHEMAS.items():
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
    for table1, mappings in FOREIGN_KEY_MAPPINGS.items():
        for table2, mapping in mappings.items():
            key = tuple(sorted([table1, table2]))
            if key not in graph["join_paths"]:
                graph["join_paths"][key] = []
            graph["join_paths"][key].append(mapping)
    
    return graph


def transform_textbook_to_practice(
    sql: str,
    source_tables: list[str],
    custom_mappings: dict[str, str] | None = None,
) -> str:
    """
    Transform SQL using textbook-specific schemas to practice schemas.
    
    Args:
        sql: Original SQL using textbook schemas
        source_tables: Tables used in the original SQL
        custom_mappings: Optional custom table/column mappings
        
    Returns:
        Transformed SQL using practice schemas
        
    Example:
        >>> sql = "SELECT * FROM Sailors WHERE rating > 5;"
        >>> transform_textbook_to_practice(sql, ["Sailors"])
        'SELECT * FROM users WHERE age > 5;'
    """
    import re
    
    if not sql or not sql.strip():
        return ""
    
    mappings = custom_mappings or TEXTBOOK_TO_PRACTICE_MAPPING
    transformed = sql
    
    # Build mapping from source tables to target tables
    table_mapping: dict[str, str] = {}
    for source_table in source_tables:
        source_lower = source_table.lower()
        # Find matching practice schema
        for key, value in mappings.items():
            if key.lower() == source_lower:
                table_mapping[source_table] = value
                break
    
    # Replace table names (whole word, case-insensitive)
    for old_table, new_table in table_mapping.items():
        pattern = r'\b' + re.escape(old_table) + r'\b'
        transformed = re.sub(pattern, new_table, transformed, flags=re.IGNORECASE)
    
    # Replace column names
    for old_col, new_col in mappings.items():
        if "_" in old_col:  # Column names have underscores
            pattern = r'\b' + re.escape(old_col) + r'\b'
            transformed = re.sub(pattern, new_col, transformed, flags=re.IGNORECASE)
    
    # Clean up
    transformed = re.sub(r'\s+', ' ', transformed)
    transformed = transformed.strip()
    if not transformed.endswith(';'):
        transformed += ';'
    
    return transformed
