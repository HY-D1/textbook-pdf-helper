"""
Canonical SQL Concept Ontology for SQL-Engage Integration.

This module defines the stable learning graph aligned to SQL-Engage.
It provides:
1. SQL_CONCEPTS - Canonical concept definitions
2. PREREQUISITE_DAG - Learning path prerequisite edges
3. ERROR_SUBTYPE_TO_CONCEPT_MAPPING - Error to concept alignment
4. ConceptOntology class - Query and navigation methods

Usage:
    from sql_ontology import ConceptOntology
    
    ontology = ConceptOntology()
    concept = ontology.get_concept("select-basic")
    prereqs = ontology.get_prerequisites("where-clause")
    error_concepts = ontology.get_concepts_for_error("missing_comma_in_select")
"""

from __future__ import annotations

from typing import Any


# =============================================================================
# SQL_CONCEPTS - Canonical Concept Definitions
# =============================================================================

SQL_CONCEPTS: dict[str, dict[str, Any]] = {
    # =========================================================================
    # DQL (Data Query Language) - Core Query Concepts
    # =========================================================================
    
    "select-basic": {
        "id": "select-basic",
        "canonical_name": "sql.dql.select.basic",
        "title": "SELECT Statement Basics",
        "category": "dql",
        "difficulty": "beginner",
        "learning_objectives": [
            "Retrieve all columns using SELECT *",
            "Retrieve specific columns by name",
            "Understand the basic structure of a SELECT statement",
            "Use DISTINCT to eliminate duplicates"
        ],
        "description": "Fundamentals of retrieving data from database tables using the SELECT statement, including column selection and eliminating duplicates.",
        "is_core_learning_node": True,
    },
    
    "where-clause": {
        "id": "where-clause",
        "canonical_name": "sql.dql.where.basic",
        "title": "WHERE Clause and Filtering",
        "category": "dql",
        "difficulty": "beginner",
        "learning_objectives": [
            "Filter rows using the WHERE clause",
            "Use comparison operators (=, <>, <, >, <=, >=)",
            "Combine conditions with AND and OR",
            "Use BETWEEN, IN, and LIKE operators"
        ],
        "description": "Filtering query results using conditions with WHERE clause, comparison operators, and logical operators.",
        "is_core_learning_node": True,
    },
    
    "null-handling": {
        "id": "null-handling",
        "canonical_name": "sql.dql.null.handling",
        "title": "NULL Value Handling",
        "category": "dql",
        "difficulty": "beginner",
        "learning_objectives": [
            "Understand what NULL represents",
            "Use IS NULL and IS NOT NULL operators",
            "Avoid common NULL comparison mistakes",
            "Understand NULL behavior in aggregate functions"
        ],
        "description": "Working with NULL values in SQL, including proper comparison syntax and behavior in operations.",
        "is_core_learning_node": True,
    },
    
    "pattern-matching": {
        "id": "pattern-matching",
        "canonical_name": "sql.dql.like.patterns",
        "title": "Pattern Matching with LIKE",
        "category": "dql",
        "difficulty": "beginner",
        "learning_objectives": [
            "Use LIKE for text pattern matching",
            "Understand wildcards % and _",
            "Combine patterns with AND/OR",
            "Use ILIKE for case-insensitive matching"
        ],
        "description": "Searching for text patterns using LIKE operator with wildcards.",
        "is_core_learning_node": True,
    },
    
    "order-by": {
        "id": "order-by",
        "canonical_name": "sql.dql.orderby.sorting",
        "title": "ORDER BY Clause",
        "category": "dql",
        "difficulty": "beginner",
        "learning_objectives": [
            "Sort results by one or more columns",
            "Use ASC and DESC for sort direction",
            "Sort by column position",
            "Handle NULLs in sorting"
        ],
        "description": "Sorting query results using ORDER BY clause with ascending and descending order.",
        "is_core_learning_node": True,
    },
    
    "limit-offset": {
        "id": "limit-offset",
        "canonical_name": "sql.dql.pagination.basic",
        "title": "LIMIT and OFFSET",
        "category": "dql",
        "difficulty": "beginner",
        "learning_objectives": [
            "Limit the number of returned rows",
            "Skip rows using OFFSET",
            "Implement basic pagination",
            "Understand database-specific syntax variations"
        ],
        "description": "Controlling result set size and implementing pagination with LIMIT and OFFSET.",
        "is_core_learning_node": True,
    },
    
    "alias": {
        "id": "alias",
        "canonical_name": "sql.dql.alias.basic",
        "title": "Column and Table Aliases",
        "category": "dql",
        "difficulty": "beginner",
        "learning_objectives": [
            "Create column aliases with AS",
            "Create table aliases for brevity",
            "Resolve ambiguous column references",
            "Understand alias scope"
        ],
        "description": "Using aliases to rename columns and tables for readability and disambiguation.",
        "is_core_learning_node": True,
    },
    
    "distinct": {
        "id": "distinct",
        "canonical_name": "sql.dql.select.distinct",
        "title": "DISTINCT Keyword",
        "category": "dql",
        "difficulty": "beginner",
        "learning_objectives": [
            "Eliminate duplicate rows from results",
            "Use DISTINCT with multiple columns",
            "Understand performance implications"
        ],
        "description": "Removing duplicate values from query results using DISTINCT.",
        "is_core_learning_node": True,
    },
    
    # =========================================================================
    # JOIN Concepts
    # =========================================================================
    
    "joins-intro": {
        "id": "joins-intro",
        "canonical_name": "sql.dql.joins.intro",
        "title": "Introduction to JOINs",
        "category": "dql",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Understand why joins are needed",
            "Identify relationships between tables",
            "Understand primary and foreign keys",
            "Visualize join operations with Venn diagrams"
        ],
        "description": "Fundamentals of combining data from multiple tables using JOIN operations.",
        "is_core_learning_node": True,
    },
    
    "inner-join": {
        "id": "inner-join",
        "canonical_name": "sql.dql.joins.inner",
        "title": "INNER JOIN",
        "category": "dql",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Write INNER JOIN syntax",
            "Specify join conditions with ON",
            "Join multiple tables",
            "Understand matching row behavior"
        ],
        "description": "Retrieving only matching rows from two or more tables using INNER JOIN.",
        "is_core_learning_node": True,
    },
    
    "outer-join": {
        "id": "outer-join",
        "canonical_name": "sql.dql.joins.outer",
        "title": "OUTER JOIN",
        "category": "dql",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Use LEFT JOIN to preserve left table rows",
            "Use RIGHT JOIN to preserve right table rows",
            "Use FULL OUTER JOIN when available",
            "Handle NULLs from unmatched rows"
        ],
        "description": "Retrieving all rows from one table and matching rows from another using OUTER JOINs.",
        "is_core_learning_node": True,
    },
    
    "self-join": {
        "id": "self-join",
        "canonical_name": "sql.dql.joins.self",
        "title": "Self JOIN",
        "category": "dql",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Join a table to itself",
            "Use table aliases for self-joins",
            "Query hierarchical data",
            "Find related rows within the same table"
        ],
        "description": "Joining a table to itself to query hierarchical or related data within the same table.",
        "is_core_learning_node": True,
    },
    
    "cross-join": {
        "id": "cross-join",
        "canonical_name": "sql.dql.joins.cross",
        "title": "CROSS JOIN",
        "category": "dql",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Create Cartesian products",
            "Understand when to use CROSS JOIN",
            "Recognize performance implications",
            "Generate combinations of rows"
        ],
        "description": "Creating Cartesian products of rows from two or more tables using CROSS JOIN.",
        "is_core_learning_node": False,
    },
    
    # =========================================================================
    # Aggregation Concepts
    # =========================================================================
    
    "aggregate-functions": {
        "id": "aggregate-functions",
        "canonical_name": "sql.dql.aggregate.basic",
        "title": "Aggregate Functions",
        "category": "dql",
        "difficulty": "beginner",
        "learning_objectives": [
            "Use COUNT to count rows",
            "Use SUM to total numeric values",
            "Calculate averages with AVG",
            "Find MIN and MAX values",
            "Understand NULL handling in aggregates"
        ],
        "description": "Computing summary values from groups of rows using COUNT, SUM, AVG, MIN, and MAX.",
        "is_core_learning_node": True,
    },
    
    "group-by": {
        "id": "group-by",
        "canonical_name": "sql.dql.groupby.basic",
        "title": "GROUP BY Clause",
        "category": "dql",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Group rows by common values",
            "Apply aggregate functions to groups",
            "Group by multiple columns",
            "Understand column requirements in SELECT"
        ],
        "description": "Grouping rows with common values for aggregate calculations using GROUP BY.",
        "is_core_learning_node": True,
    },
    
    "having-clause": {
        "id": "having-clause",
        "canonical_name": "sql.dql.having.basic",
        "title": "HAVING Clause",
        "category": "dql",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Filter groups with HAVING",
            "Distinguish WHERE from HAVING",
            "Use aggregate conditions in HAVING",
            "Combine WHERE and HAVING"
        ],
        "description": "Filtering grouped results based on aggregate conditions using HAVING clause.",
        "is_core_learning_node": True,
    },
    
    # =========================================================================
    # Subquery Concepts
    # =========================================================================
    
    "subqueries-intro": {
        "id": "subqueries-intro",
        "canonical_name": "sql.dql.subqueries.intro",
        "title": "Introduction to Subqueries",
        "category": "dql",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Write basic subqueries",
            "Use subqueries in WHERE clause",
            "Understand subquery scope",
            "Distinguish scalar vs row vs table subqueries"
        ],
        "description": "Using nested SELECT statements (subqueries) within other SQL statements.",
        "is_core_learning_node": True,
    },
    
    "correlated-subquery": {
        "id": "correlated-subquery",
        "canonical_name": "sql.dql.subqueries.correlated",
        "title": "Correlated Subqueries",
        "category": "dql",
        "difficulty": "advanced",
        "learning_objectives": [
            "Reference outer query columns in subqueries",
            "Understand correlated vs non-correlated",
            "Use EXISTS with correlated subqueries",
            "Optimize correlated subquery performance"
        ],
        "description": "Subqueries that reference columns from the outer query, executing once per outer row.",
        "is_core_learning_node": True,
    },
    
    "subquery-in-where": {
        "id": "subquery-in-where",
        "canonical_name": "sql.dql.subqueries.where",
        "title": "Subqueries in WHERE Clause",
        "category": "dql",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Use IN with subqueries",
            "Use comparison operators with subqueries",
            "Use ALL and ANY quantifiers",
            "Handle single vs multiple row results"
        ],
        "description": "Filtering rows using subqueries in the WHERE clause with IN, EXISTS, and comparison operators.",
        "is_core_learning_node": True,
    },
    
    "subquery-in-select": {
        "id": "subquery-in-select",
        "canonical_name": "sql.dql.subqueries.scalar",
        "title": "Scalar Subqueries in SELECT",
        "category": "dql",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Use subqueries as computed columns",
            "Ensure subqueries return single values",
            "Combine with joins for complex reports",
            "Understand performance considerations"
        ],
        "description": "Using scalar subqueries in the SELECT list to compute column values.",
        "is_core_learning_node": True,
    },
    
    "exists-operator": {
        "id": "exists-operator",
        "canonical_name": "sql.dql.subqueries.exists",
        "title": "EXISTS Operator",
        "category": "dql",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Test for existence of rows with EXISTS",
            "Use NOT EXISTS for negation",
            "Optimize with EXISTS vs IN",
            "Write efficient semi-joins"
        ],
        "description": "Testing for existence of rows using EXISTS and NOT EXISTS operators.",
        "is_core_learning_node": True,
    },
    
    # =========================================================================
    # Set Operations
    # =========================================================================
    
    "union": {
        "id": "union",
        "canonical_name": "sql.dql.setops.union",
        "title": "UNION and UNION ALL",
        "category": "dql",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Combine results with UNION",
            "Preserve duplicates with UNION ALL",
            "Ensure column compatibility",
            "Order combined results"
        ],
        "description": "Combining result sets from multiple queries using UNION and UNION ALL.",
        "is_core_learning_node": True,
    },
    
    "intersect-except": {
        "id": "intersect-except",
        "canonical_name": "sql.dql.setops.intersect",
        "title": "INTERSECT and EXCEPT",
        "category": "dql",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Find common rows with INTERSECT",
            "Find differences with EXCEPT/MINUS",
            "Understand database support variations",
            "Rewrite using joins when needed"
        ],
        "description": "Finding common and different rows between result sets using INTERSECT and EXCEPT.",
        "is_core_learning_node": False,
    },
    
    # =========================================================================
    # DML (Data Manipulation Language)
    # =========================================================================
    
    "insert-statement": {
        "id": "insert-statement",
        "canonical_name": "sql.dml.insert.basic",
        "title": "INSERT Statement",
        "category": "dml",
        "difficulty": "beginner",
        "learning_objectives": [
            "Insert single rows",
            "Insert multiple rows",
            "Insert from SELECT (INSERT INTO SELECT)",
            "Handle default values and NULLs"
        ],
        "description": "Adding new rows to database tables using INSERT statement.",
        "is_core_learning_node": True,
    },
    
    "update-statement": {
        "id": "update-statement",
        "canonical_name": "sql.dml.update.basic",
        "title": "UPDATE Statement",
        "category": "dml",
        "difficulty": "beginner",
        "learning_objectives": [
            "Update existing rows",
            "Use WHERE to limit updates",
            "Update multiple columns",
            "Update from joined tables"
        ],
        "description": "Modifying existing data in tables using UPDATE statement.",
        "is_core_learning_node": True,
    },
    
    "delete-statement": {
        "id": "delete-statement",
        "canonical_name": "sql.dml.delete.basic",
        "title": "DELETE Statement",
        "category": "dml",
        "difficulty": "beginner",
        "learning_objectives": [
            "Delete specific rows with WHERE",
            "Delete all rows from a table",
            "Use subqueries in DELETE",
            "Understand TRUNCATE vs DELETE"
        ],
        "description": "Removing rows from database tables using DELETE statement.",
        "is_core_learning_node": True,
    },
    
    "merge-upsert": {
        "id": "merge-upsert",
        "canonical_name": "sql.dml.merge.basic",
        "title": "MERGE (UPSERT) Statement",
        "category": "dml",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Insert or update in single statement",
            "Use ON CONFLICT/ON DUPLICATE KEY",
            "Understand database-specific syntax",
            "Handle conditional logic"
        ],
        "description": "Conditionally inserting or updating rows using MERGE or UPSERT operations.",
        "is_core_learning_node": False,
    },
    
    # =========================================================================
    # DDL (Data Definition Language)
    # =========================================================================
    
    "create-table": {
        "id": "create-table",
        "canonical_name": "sql.ddl.create.table",
        "title": "CREATE TABLE",
        "category": "ddl",
        "difficulty": "beginner",
        "learning_objectives": [
            "Create new tables",
            "Define column names and data types",
            "Add column constraints",
            "Create tables from SELECT"
        ],
        "description": "Creating database tables with column definitions using CREATE TABLE.",
        "is_core_learning_node": True,
    },
    
    "alter-table": {
        "id": "alter-table",
        "canonical_name": "sql.ddl.alter.table",
        "title": "ALTER TABLE",
        "category": "ddl",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Add new columns",
            "Modify column definitions",
            "Drop columns",
            "Add and drop constraints"
        ],
        "description": "Modifying existing table structure using ALTER TABLE statement.",
        "is_core_learning_node": True,
    },
    
    "drop-table": {
        "id": "drop-table",
        "canonical_name": "sql.ddl.drop.table",
        "title": "DROP TABLE",
        "category": "ddl",
        "difficulty": "beginner",
        "learning_objectives": [
            "Delete tables permanently",
            "Use IF EXISTS for safety",
            "Understand CASCADE behavior",
            "Handle foreign key constraints"
        ],
        "description": "Removing database tables using DROP TABLE statement.",
        "is_core_learning_node": True,
    },
    
    "data-types": {
        "id": "data-types",
        "canonical_name": "sql.ddl.datatypes.basic",
        "title": "SQL Data Types",
        "category": "ddl",
        "difficulty": "beginner",
        "learning_objectives": [
            "Choose numeric types (INT, DECIMAL, FLOAT)",
            "Use character types (CHAR, VARCHAR, TEXT)",
            "Work with date/time types",
            "Understand type conversion"
        ],
        "description": "Understanding and selecting appropriate data types for columns.",
        "is_core_learning_node": True,
    },
    
    "constraints": {
        "id": "constraints",
        "canonical_name": "sql.ddl.constraints.basic",
        "title": "Integrity Constraints",
        "category": "ddl",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Define PRIMARY KEY constraints",
            "Create FOREIGN KEY relationships",
            "Use UNIQUE and CHECK constraints",
            "Add NOT NULL constraints"
        ],
        "description": "Ensuring data integrity with PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK, and NOT NULL constraints.",
        "is_core_learning_node": True,
    },
    
    "primary-key": {
        "id": "primary-key",
        "canonical_name": "sql.ddl.constraints.primarykey",
        "title": "Primary Key Constraint",
        "category": "ddl",
        "difficulty": "beginner",
        "learning_objectives": [
            "Define single-column primary keys",
            "Create composite primary keys",
            "Understand auto-increment behavior",
            "Choose appropriate key columns"
        ],
        "description": "Uniquely identifying rows with PRIMARY KEY constraints.",
        "is_core_learning_node": True,
    },
    
    "foreign-key": {
        "id": "foreign-key",
        "canonical_name": "sql.ddl.constraints.foreignkey",
        "title": "Foreign Key Constraint",
        "category": "ddl",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Create relationships between tables",
            "Define referential actions (CASCADE, SET NULL)",
            "Understand referential integrity",
            "Handle self-referencing keys"
        ],
        "description": "Maintaining referential integrity between tables with FOREIGN KEY constraints.",
        "is_core_learning_node": True,
    },
    
    # =========================================================================
    # Advanced Topics
    # =========================================================================
    
    "indexes": {
        "id": "indexes",
        "canonical_name": "sql.advanced.indexes.basic",
        "title": "Database Indexes",
        "category": "advanced",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Create B-tree indexes",
            "Understand when to use indexes",
            "Analyze query execution plans",
            "Maintain and rebuild indexes"
        ],
        "description": "Improving query performance using database indexes.",
        "is_core_learning_node": True,
    },
    
    "views": {
        "id": "views",
        "canonical_name": "sql.advanced.views.basic",
        "title": "SQL Views",
        "category": "advanced",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Create views from queries",
            "Use views for security",
            "Understand view updatability",
            "Create materialized views"
        ],
        "description": "Creating virtual tables based on stored queries using VIEWs.",
        "is_core_learning_node": True,
    },
    
    "transactions": {
        "id": "transactions",
        "canonical_name": "sql.advanced.transactions.basic",
        "title": "Database Transactions",
        "category": "advanced",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Understand ACID properties",
            "Use COMMIT and ROLLBACK",
            "Implement transaction blocks",
            "Handle transaction errors"
        ],
        "description": "Ensuring data consistency with ACID-compliant transaction processing.",
        "is_core_learning_node": True,
    },
    
    "isolation-levels": {
        "id": "isolation-levels",
        "canonical_name": "sql.advanced.transactions.isolation",
        "title": "Transaction Isolation Levels",
        "category": "advanced",
        "difficulty": "advanced",
        "learning_objectives": [
            "Understand dirty reads, non-repeatable reads, phantom reads",
            "Use READ UNCOMMITTED",
            "Use READ COMMITTED",
            "Use REPEATABLE READ and SERIALIZABLE"
        ],
        "description": "Controlling transaction behavior and concurrency with isolation levels.",
        "is_core_learning_node": False,
    },
    
    "stored-procedures": {
        "id": "stored-procedures",
        "canonical_name": "sql.advanced.procedures.basic",
        "title": "Stored Procedures",
        "category": "advanced",
        "difficulty": "advanced",
        "learning_objectives": [
            "Create reusable SQL routines",
            "Use input and output parameters",
            "Handle errors in procedures",
            "Call procedures from applications"
        ],
        "description": "Creating and using stored procedures for reusable database logic.",
        "is_core_learning_node": False,
    },
    
    "triggers": {
        "id": "triggers",
        "canonical_name": "sql.advanced.triggers.basic",
        "title": "Database Triggers",
        "category": "advanced",
        "difficulty": "advanced",
        "learning_objectives": [
            "Create BEFORE and AFTER triggers",
            "Use triggers for auditing",
            "Implement complex constraints",
            "Avoid trigger pitfalls"
        ],
        "description": "Automatically executing SQL code in response to data changes using triggers.",
        "is_core_learning_node": False,
    },
    
    "window-functions": {
        "id": "window-functions",
        "canonical_name": "sql.advanced.windows.basic",
        "title": "Window Functions",
        "category": "advanced",
        "difficulty": "advanced",
        "learning_objectives": [
            "Use ROW_NUMBER, RANK, DENSE_RANK",
            "Calculate running totals",
            "Use LAG and LEAD",
            "Define window frames with OVER"
        ],
        "description": "Performing calculations across sets of rows related to the current row using window functions.",
        "is_core_learning_node": False,
    },
    
    "cte": {
        "id": "cte",
        "canonical_name": "sql.advanced.cte.basic",
        "title": "Common Table Expressions (CTEs)",
        "category": "advanced",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Write simple CTEs with WITH",
            "Create recursive CTEs",
            "Improve query readability",
            "Use multiple CTEs in one query"
        ],
        "description": "Creating named temporary result sets using Common Table Expressions.",
        "is_core_learning_node": True,
    },
    
    # =========================================================================
    # Database Design
    # =========================================================================
    
    "normalization": {
        "id": "normalization",
        "canonical_name": "sql.design.normalization.basic",
        "title": "Database Normalization",
        "category": "design",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Understand normalization purpose",
            "Identify functional dependencies",
            "Apply 1NF, 2NF, 3NF",
            "Recognize denormalization needs"
        ],
        "description": "Organizing data to minimize redundancy and ensure integrity through normalization.",
        "is_core_learning_node": True,
    },
    
    "first-normal-form": {
        "id": "first-normal-form",
        "canonical_name": "sql.design.normalization.1nf",
        "title": "First Normal Form (1NF)",
        "category": "design",
        "difficulty": "beginner",
        "learning_objectives": [
            "Eliminate repeating groups",
            "Ensure atomic values",
            "Create primary keys",
            "Remove duplicate columns"
        ],
        "description": "Achieving First Normal Form by eliminating repeating groups and ensuring atomic values.",
        "is_core_learning_node": True,
    },
    
    "second-normal-form": {
        "id": "second-normal-form",
        "canonical_name": "sql.design.normalization.2nf",
        "title": "Second Normal Form (2NF)",
        "category": "design",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Meet 1NF requirements",
            "Eliminate partial dependencies",
            "Handle composite keys",
            "Decompose tables properly"
        ],
        "description": "Achieving Second Normal Form by eliminating partial dependencies on composite keys.",
        "is_core_learning_node": True,
    },
    
    "third-normal-form": {
        "id": "third-normal-form",
        "canonical_name": "sql.design.normalization.3nf",
        "title": "Third Normal Form (3NF)",
        "category": "design",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Meet 2NF requirements",
            "Eliminate transitive dependencies",
            "Identify and separate dependent attributes",
            "Validate 3NF compliance"
        ],
        "description": "Achieving Third Normal Form by eliminating transitive dependencies.",
        "is_core_learning_node": True,
    },
    
    "erd-basics": {
        "id": "erd-basics",
        "canonical_name": "sql.design.erd.basic",
        "title": "Entity-Relationship Diagrams",
        "category": "design",
        "difficulty": "beginner",
        "learning_objectives": [
            "Identify entities and attributes",
            "Define relationships",
            "Understand cardinality notation",
            "Read and create ERDs"
        ],
        "description": "Visual database design using Entity-Relationship Diagrams.",
        "is_core_learning_node": True,
    },
    
    "database-design": {
        "id": "database-design",
        "canonical_name": "sql.design.process.basic",
        "title": "Database Design Process",
        "category": "design",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Gather requirements",
            "Create conceptual models",
            "Convert to logical models",
            "Implement physical design"
        ],
        "description": "End-to-end database design from requirements gathering to physical implementation.",
        "is_core_learning_node": True,
    },
    
    # =========================================================================
    # String Functions (Helper concepts)
    # =========================================================================
    
    "string-functions": {
        "id": "string-functions",
        "canonical_name": "sql.functions.string.basic",
        "title": "String Functions",
        "category": "dql",
        "difficulty": "beginner",
        "learning_objectives": [
            "Use CONCAT for string concatenation",
            "Extract substrings with SUBSTRING",
            "Change case with UPPER/LOWER",
            "Trim whitespace with TRIM"
        ],
        "description": "Manipulating text data using SQL string functions.",
        "is_core_learning_node": False,
    },
    
    "date-functions": {
        "id": "date-functions",
        "canonical_name": "sql.functions.date.basic",
        "title": "Date and Time Functions",
        "category": "dql",
        "difficulty": "intermediate",
        "learning_objectives": [
            "Get current date/time",
            "Extract parts of dates",
            "Add and subtract intervals",
            "Format dates for display"
        ],
        "description": "Working with date and time values using SQL date functions.",
        "is_core_learning_node": False,
    },
}


# =============================================================================
# PREREQUISITE_DAG - Learning Path Edges
# =============================================================================

PREREQUISITE_DAG: list[dict[str, str]] = [
    # DQL Foundation - Select Basics
    ("select-basic", "where-clause", "hard_prereq"),
    ("select-basic", "alias", "hard_prereq"),
    ("select-basic", "distinct", "soft_prereq"),
    
    # Filtering and Sorting
    ("where-clause", "null-handling", "hard_prereq"),
    ("where-clause", "pattern-matching", "soft_prereq"),
    ("where-clause", "order-by", "soft_prereq"),
    ("select-basic", "limit-offset", "soft_prereq"),
    
    # Joins Foundation
    ("select-basic", "joins-intro", "hard_prereq"),
    ("joins-intro", "inner-join", "hard_prereq"),
    ("inner-join", "outer-join", "hard_prereq"),
    ("inner-join", "self-join", "soft_prereq"),
    ("inner-join", "cross-join", "soft_prereq"),
    ("alias", "inner-join", "soft_prereq"),  # Table aliases important for joins
    
    # Aggregation
    ("select-basic", "aggregate-functions", "hard_prereq"),
    ("aggregate-functions", "group-by", "hard_prereq"),
    ("group-by", "having-clause", "hard_prereq"),
    ("where-clause", "having-clause", "soft_prereq"),  # Similar filtering concept
    ("null-handling", "aggregate-functions", "soft_prereq"),  # NULLs in aggregates
    
    # Subqueries
    ("where-clause", "subqueries-intro", "hard_prereq"),
    ("subqueries-intro", "subquery-in-where", "hard_prereq"),
    ("subqueries-intro", "subquery-in-select", "hard_prereq"),
    ("subqueries-intro", "exists-operator", "soft_prereq"),
    ("inner-join", "correlated-subquery", "soft_prereq"),
    ("subqueries-intro", "correlated-subquery", "hard_prereq"),
    
    # Set Operations
    ("select-basic", "union", "hard_prereq"),
    ("union", "intersect-except", "soft_prereq"),
    
    # DML
    ("select-basic", "insert-statement", "soft_prereq"),
    ("select-basic", "update-statement", "hard_prereq"),
    ("select-basic", "delete-statement", "hard_prereq"),
    ("where-clause", "update-statement", "hard_prereq"),  # WHERE important for updates
    ("where-clause", "delete-statement", "hard_prereq"),
    ("subqueries-intro", "merge-upsert", "soft_prereq"),
    
    # DDL
    ("data-types", "create-table", "hard_prereq"),
    ("create-table", "alter-table", "hard_prereq"),
    ("create-table", "drop-table", "soft_prereq"),
    ("primary-key", "foreign-key", "hard_prereq"),
    ("constraints", "primary-key", "soft_prereq"),
    ("constraints", "foreign-key", "soft_prereq"),
    ("create-table", "constraints", "soft_prereq"),
    
    # Advanced Topics
    ("select-basic", "indexes", "soft_prereq"),
    ("create-table", "indexes", "hard_prereq"),
    ("select-basic", "views", "hard_prereq"),
    ("joins-intro", "views", "soft_prereq"),
    ("dml-insert", "transactions", "soft_prereq"),  # Typo fix below
    ("insert-statement", "transactions", "soft_prereq"),
    ("update-statement", "transactions", "soft_prereq"),
    ("delete-statement", "transactions", "soft_prereq"),
    ("transactions", "isolation-levels", "hard_prereq"),
    ("subqueries-intro", "cte", "soft_prereq"),
    ("aggregate-functions", "window-functions", "soft_prereq"),
    ("window-functions", "stored-procedures", "soft_prereq"),  # Advanced progression
    
    # Database Design
    ("create-table", "normalization", "soft_prereq"),
    ("primary-key", "normalization", "hard_prereq"),
    ("foreign-key", "normalization", "hard_prereq"),
    ("erd-basics", "first-normal-form", "soft_prereq"),
    ("first-normal-form", "second-normal-form", "hard_prereq"),
    ("second-normal-form", "third-normal-form", "hard_prereq"),
    ("erd-basics", "database-design", "soft_prereq"),
    ("normalization", "database-design", "soft_prereq"),
]

# Convert tuples to dict format
PREREQUISITE_DAG = [
    {"from": f, "to": t, "type": typ} for f, t, typ in PREREQUISITE_DAG
]


# =============================================================================
# ERROR_SUBTYPE_TO_CONCEPT_MAPPING
# Maps SQL-Engage error subtypes to relevant concept IDs
# =============================================================================

ERROR_SUBTYPE_TO_CONCEPT_MAPPING: dict[str, list[str]] = {
    # Query Completeness Errors
    "incomplete_query": ["select-basic", "syntax-error"],
    "incorrect_select_usage": ["select-basic", "distinct"],
    "incorrect_wildcard_usage": ["select-basic"],
    "missing_comma_in_select": ["select-basic", "syntax-error"],
    "extra_comma_in_select": ["select-basic", "syntax-error"],
    
    # WHERE Clause Errors
    "missing_where_clause": ["where-clause"],
    "incorrect_operator_usage": ["where-clause", "null-handling"],
    "incorrect_function_usage": ["string-functions", "date-functions", "aggregate-functions"],
    "incorrect_parentheses": ["where-clause", "logical-operators"],
    "incorrect_null_comparison": ["null-handling"],
    
    # JOIN Errors
    "incorrect_join_type": ["joins-intro", "inner-join", "outer-join"],
    "missing_join_condition": ["joins-intro", "inner-join", "outer-join"],
    "incorrect_join_table_order": ["joins-intro"],
    
    # Aggregation Errors
    "missing_group_by": ["group-by", "aggregate-functions"],
    "incorrect_group_by_columns": ["group-by"],
    "having_without_group_by": ["having-clause", "group-by"],
    "incorrect_aggregate_function": ["aggregate-functions"],
    
    # Set Operation Errors
    "incorrect_union_usage": ["union"],
    "incompatible_columns_in_union": ["union", "data-types"],
    
    # Subquery Errors
    "incorrect_subquery_usage": ["subqueries-intro", "subquery-in-where", "exists-operator"],
    "correlated_subquery_error": ["correlated-subquery", "subqueries-intro"],
    
    # Alias and Reference Errors
    "ambiguous_column_reference": ["alias"],
    "undefined_alias": ["alias"],
    "alias_reference_in_where": ["alias"],
    "alias_syntax_error": ["alias"],
    
    # Pattern Matching Errors
    "like_pattern_syntax": ["pattern-matching"],
    "like_wildcard_misuse": ["pattern-matching"],
    
    # NULL Handling Errors
    "null_arithmetic_error": ["null-handling"],
    "null_aggregate_ignored": ["null-handling"],
}


# =============================================================================
# ConceptOntology Class
# =============================================================================

class ConceptOntology:
    """
    Canonical SQL Concept Ontology for SQL-Engage.
    
    Provides methods to query concepts, prerequisites, and error mappings
    for building adaptive learning paths.
    
    Example:
        >>> ontology = ConceptOntology()
        >>> concept = ontology.get_concept("select-basic")
        >>> prereqs = ontology.get_prerequisites("where-clause")
        >>> error_concepts = ontology.get_concepts_for_error("missing_comma_in_select")
    """
    
    def __init__(self):
        """Initialize the ontology with concept data."""
        self._concepts = SQL_CONCEPTS
        self._prereqs = PREREQUISITE_DAG
        self._error_map = ERROR_SUBTYPE_TO_CONCEPT_MAPPING
        
        # Build reverse lookup for downstream concepts
        self._downstream: dict[str, list[str]] = {}
        for edge in self._prereqs:
            from_id = edge["from"]
            to_id = edge["to"]
            if from_id not in self._downstream:
                self._downstream[from_id] = []
            self._downstream[from_id].append(to_id)
    
    def get_concept(self, concept_id: str) -> dict[str, Any] | None:
        """
        Get a concept by its ID.
        
        Args:
            concept_id: The canonical concept ID (e.g., "select-basic")
            
        Returns:
            Concept definition dict or None if not found
        """
        return self._concepts.get(concept_id)
    
    def get_prerequisites(self, concept_id: str) -> list[str]:
        """
        Get all prerequisite concept IDs for a given concept.
        
        Args:
            concept_id: The concept ID to find prerequisites for
            
        Returns:
            List of prerequisite concept IDs (both hard and soft)
        """
        prereqs = []
        for edge in self._prereqs:
            if edge["to"] == concept_id:
                prereqs.append(edge["from"])
        return prereqs
    
    def get_hard_prerequisites(self, concept_id: str) -> list[str]:
        """
        Get only hard prerequisite concept IDs for a given concept.
        
        Args:
            concept_id: The concept ID to find hard prerequisites for
            
        Returns:
            List of hard prerequisite concept IDs
        """
        prereqs = []
        for edge in self._prereqs:
            if edge["to"] == concept_id and edge["type"] == "hard_prereq":
                prereqs.append(edge["from"])
        return prereqs
    
    def get_downstream(self, concept_id: str) -> list[str]:
        """
        Get all concepts that have this concept as a prerequisite.
        
        Args:
            concept_id: The concept ID to find downstream concepts for
            
        Returns:
            List of downstream concept IDs
        """
        return self._downstream.get(concept_id, [])
    
    def get_concepts_for_error(self, error_subtype: str) -> list[str]:
        """
        Get relevant concept IDs for a given error subtype.
        
        Args:
            error_subtype: The SQL-Engage error subtype (e.g., "missing_comma_in_select")
            
        Returns:
            List of concept IDs relevant to the error
        """
        # Filter out non-existent concepts (like "syntax-error" placeholder)
        concepts = self._error_map.get(error_subtype, [])
        return [c for c in concepts if c in self._concepts]
    
    def validate_concept_id(self, concept_id: str) -> bool:
        """
        Check if a concept ID exists in the ontology.
        
        Args:
            concept_id: The concept ID to validate
            
        Returns:
            True if the concept exists, False otherwise
        """
        return concept_id in self._concepts
    
    def get_core_learning_nodes(self) -> list[str]:
        """
        Get all core learning node concept IDs.
        
        Returns:
            List of concept IDs marked as core learning nodes
        """
        return [
            cid for cid, concept in self._concepts.items()
            if concept.get("is_core_learning_node", False)
        ]
    
    def get_concepts_by_category(self, category: str) -> list[dict[str, Any]]:
        """
        Get all concepts in a given category.
        
        Args:
            category: The category name (dql, dml, ddl, design, advanced)
            
        Returns:
            List of concept definitions in the category
        """
        return [
            concept for concept in self._concepts.values()
            if concept.get("category") == category
        ]
    
    def get_concepts_by_difficulty(self, difficulty: str) -> list[dict[str, Any]]:
        """
        Get all concepts with a given difficulty level.
        
        Args:
            difficulty: The difficulty level (beginner, intermediate, advanced)
            
        Returns:
            List of concept definitions with the difficulty
        """
        return [
            concept for concept in self._concepts.values()
            if concept.get("difficulty") == difficulty
        ]
    
    def get_learning_path(self, start_concept: str, end_concept: str) -> list[str]:
        """
        Find a learning path from start to end concept using BFS.
        
        Args:
            start_concept: The starting concept ID
            end_concept: The target concept ID
            
        Returns:
            List of concept IDs forming a path, or empty list if no path
        """
        if start_concept not in self._concepts or end_concept not in self._concepts:
            return []
        
        if start_concept == end_concept:
            return [start_concept]
        
        # BFS to find shortest path
        from collections import deque
        
        queue = deque([(start_concept, [start_concept])])
        visited = {start_concept}
        
        while queue:
            current, path = queue.popleft()
            
            # Get concepts that can be learned after current
            for edge in self._prereqs:
                if edge["from"] == current:
                    next_concept = edge["to"]
                    if next_concept == end_concept:
                        return path + [next_concept]
                    if next_concept not in visited:
                        visited.add(next_concept)
                        queue.append((next_concept, path + [next_concept]))
        
        return []
    
    def get_recommended_learning_order(self, target_concepts: list[str]) -> list[str]:
        """
        Get a recommended learning order for a set of target concepts.
        Uses topological sort to respect prerequisite relationships.
        
        Args:
            target_concepts: List of concept IDs to learn
            
        Returns:
            Ordered list of concept IDs to learn (including prerequisites)
        """
        # Collect all required concepts (targets + prerequisites)
        required = set(target_concepts)
        for target in target_concepts:
            self._collect_prerequisites(target, required)
        
        # Simple topological sort based on prerequisites
        result = []
        visited = set()
        
        def visit(concept_id: str):
            if concept_id in visited:
                return
            visited.add(concept_id)
            
            # Visit hard prerequisites first
            for prereq in self.get_hard_prerequisites(concept_id):
                if prereq in required:
                    visit(prereq)
            
            # Visit soft prerequisites
            for prereq in self.get_prerequisites(concept_id):
                if prereq in required and prereq not in visited:
                    visit(prereq)
            
            result.append(concept_id)
        
        for target in target_concepts:
            visit(target)
        
        return result
    
    def _collect_prerequisites(self, concept_id: str, collected: set[str]) -> None:
        """Recursively collect all prerequisites for a concept."""
        for prereq in self.get_prerequisites(concept_id):
            if prereq not in collected and prereq in self._concepts:
                collected.add(prereq)
                self._collect_prerequisites(prereq, collected)
    
    def list_all_concepts(self) -> list[str]:
        """
        Get a list of all concept IDs in the ontology.
        
        Returns:
            List of all concept IDs
        """
        return list(self._concepts.keys())
    
    def list_all_error_subtypes(self) -> list[str]:
        """
        Get a list of all error subtypes in the mapping.
        
        Returns:
            List of all error subtype IDs
        """
        return list(self._error_map.keys())
    
    def search_concepts(self, query: str) -> list[dict[str, Any]]:
        """
        Search concepts by keyword in title, description, or objectives.
        
        Args:
            query: The search query string
            
        Returns:
            List of matching concept definitions
        """
        query_lower = query.lower()
        results = []
        
        for concept in self._concepts.values():
            # Search in title and description
            if (query_lower in concept.get("title", "").lower() or
                query_lower in concept.get("description", "").lower()):
                results.append(concept)
                continue
            
            # Search in learning objectives
            objectives = concept.get("learning_objectives", [])
            if any(query_lower in obj.lower() for obj in objectives):
                results.append(concept)
        
        return results
    
    def get_statistics(self) -> dict[str, Any]:
        """
        Get statistics about the ontology.
        
        Returns:
            Dict with counts and distribution statistics
        """
        categories = {}
        difficulties = {}
        
        for concept in self._concepts.values():
            cat = concept.get("category", "unknown")
            diff = concept.get("difficulty", "unknown")
            
            categories[cat] = categories.get(cat, 0) + 1
            difficulties[diff] = difficulties.get(diff, 0) + 1
        
        return {
            "total_concepts": len(self._concepts),
            "total_prerequisite_edges": len(self._prereqs),
            "total_error_mappings": len(self._error_map),
            "core_learning_nodes": len(self.get_core_learning_nodes()),
            "by_category": categories,
            "by_difficulty": difficulties,
        }


# =============================================================================
# Module-level convenience functions
# =============================================================================

# Create singleton instance for module-level access
_ontology = ConceptOntology()


def get_concept(concept_id: str) -> dict[str, Any] | None:
    """Module-level function to get a concept."""
    return _ontology.get_concept(concept_id)


def get_prerequisites(concept_id: str) -> list[str]:
    """Module-level function to get prerequisites."""
    return _ontology.get_prerequisites(concept_id)


def get_downstream(concept_id: str) -> list[str]:
    """Module-level function to get downstream concepts."""
    return _ontology.get_downstream(concept_id)


def get_concepts_for_error(error_subtype: str) -> list[str]:
    """Module-level function to get concepts for an error."""
    return _ontology.get_concepts_for_error(error_subtype)


def validate_concept_id(concept_id: str) -> bool:
    """Module-level function to validate a concept ID."""
    return _ontology.validate_concept_id(concept_id)


def get_core_learning_nodes() -> list[str]:
    """Module-level function to get core learning nodes."""
    return _ontology.get_core_learning_nodes()


# =============================================================================
# Main execution for testing
# =============================================================================

if __name__ == "__main__":
    ontology = ConceptOntology()
    
    print("=" * 70)
    print("SQL Concept Ontology - SQL-Engage Integration")
    print("=" * 70)
    
    # Statistics
    stats = ontology.get_statistics()
    print("\n📊 ONTOLOGY STATISTICS")
    print("-" * 40)
    print(f"Total Concepts: {stats['total_concepts']}")
    print(f"Core Learning Nodes: {stats['core_learning_nodes']}")
    print(f"Prerequisite Edges: {stats['total_prerequisite_edges']}")
    print(f"Error Mappings: {stats['total_error_mappings']}")
    print("\nBy Category:")
    for cat, count in sorted(stats['by_category'].items()):
        print(f"  {cat}: {count}")
    print("\nBy Difficulty:")
    for diff, count in sorted(stats['by_difficulty'].items()):
        print(f"  {diff}: {count}")
    
    # Sample concept
    print("\n📖 SAMPLE CONCEPT")
    print("-" * 40)
    concept = ontology.get_concept("select-basic")
    if concept:
        print(f"ID: {concept['id']}")
        print(f"Title: {concept['title']}")
        print(f"Category: {concept['category']}")
        print(f"Difficulty: {concept['difficulty']}")
        print(f"Core Node: {concept['is_core_learning_node']}")
    
    # Prerequisites example
    print("\n🔗 PREREQUISITES EXAMPLE")
    print("-" * 40)
    print(f"Prerequisites for 'group-by': {ontology.get_prerequisites('group-by')}")
    print(f"Prerequisites for 'where-clause': {ontology.get_prerequisites('where-clause')}")
    
    # Downstream example
    print("\n⬇️ DOWNSTREAM EXAMPLE")
    print("-" * 40)
    print(f"Concepts depending on 'select-basic': {ontology.get_downstream('select-basic')[:5]}...")
    
    # Error mapping example
    print("\n❌ ERROR MAPPING EXAMPLE")
    print("-" * 40)
    print(f"Concepts for 'missing_comma_in_select': {ontology.get_concepts_for_error('missing_comma_in_select')}")
    print(f"Concepts for 'missing_join_condition': {ontology.get_concepts_for_error('missing_join_condition')}")
    
    # Learning path example
    print("\n🎓 LEARNING PATH EXAMPLE")
    print("-" * 40)
    path = ontology.get_learning_path("select-basic", "group-by")
    print(f"Path from 'select-basic' to 'group-by': {' -> '.join(path)}")
    
    # Core nodes
    print("\n🎯 CORE LEARNING NODES (sample)")
    print("-" * 40)
    core_nodes = ontology.get_core_learning_nodes()
    for node in core_nodes[:10]:
        concept = ontology.get_concept(node)
        print(f"  - {node}: {concept['title']}")
    print(f"  ... and {len(core_nodes) - 10} more")
    
    print("\n" + "=" * 70)
    print("✅ Ontology validation complete!")
    print("=" * 70)
