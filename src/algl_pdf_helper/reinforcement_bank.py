"""
Reinforcement Bank Generator for Spaced Repetition Micro-Checks.

This module generates micro-checks for spaced repetition learning, including:
- 10-second recall prompts: Quick "What is X?" questions
- Minimal SQL completions: Fill-in-the-blank SQL statements
- Misconception discrimination: "Which query has an error?"
- Choose-better-query items: Compare two queries, pick the better one

The module also includes a spaced repetition scheduler (SM-2 algorithm) and
session management for delivering reinforcement items to learners.

Usage:
    bank = ReinforcementBank()
    items = bank.generate_for_concept("group-by", concept_units, config)
    
    scheduler = SpacedRepetitionScheduler()
    next_review = scheduler.calculate_next_review("group-by", performance_history)
    
    session = ReinforcementSession()
    micro_session = session.create_session(["group-by", "joins"], bank, max_items=5)
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from .instructional_models import (
    InstructionalUnit,
    ReinforcementItem,
    ReinforcementType,
)
from .misconception_bank import (
    GenerationConfig,
    MisconceptionBank,
    MisconceptionPattern,
)


# =============================================================================
# Reinforcement Bank Configuration
# =============================================================================


@dataclass
class ReinforcementConfig:
    """
    Configuration for reinforcement item generation.
    
    Controls the number of items per type, difficulty distribution,
    and content generation parameters.
    """
    
    # Item counts per concept
    recall_prompts_per_concept: int = 3
    sql_completions_per_concept: int = 3
    misconception_items_per_concept: int = 2
    query_choice_items_per_concept: int = 2
    
    # Difficulty distribution
    difficulty_distribution: dict[str, float] = field(default_factory=lambda: {
        "beginner": 0.4,
        "intermediate": 0.4,
        "advanced": 0.2,
    })
    
    # Content constraints
    max_prompt_length: int = 500
    max_answer_length: int = 500
    min_sql_completion_length: int = 20
    max_sql_completion_length: int = 200
    
    # Time estimates
    recall_time_seconds: int = 10
    completion_time_seconds: int = 20
    discrimination_time_seconds: int = 30
    choice_time_seconds: int = 25


# =============================================================================
# Performance Tracking Models
# =============================================================================


@dataclass
class PerformanceRecord:
    """A single performance record for a reinforcement item."""
    item_id: str
    concept_id: str
    answered_at: datetime
    is_correct: bool
    response_time_ms: int
    difficulty_rating: int | None = None  # 1-5 self-reported difficulty


@dataclass
class ConceptPerformanceHistory:
    """Performance history for a specific concept."""
    concept_id: str
    records: list[PerformanceRecord] = field(default_factory=list)
    current_interval_days: float = 1.0
    ease_factor: float = 2.5
    review_count: int = 0
    
    def add_record(self, record: PerformanceRecord) -> None:
        """Add a new performance record."""
        self.records.append(record)
        self.review_count += 1
    
    def get_success_rate(self, last_n: int = 5) -> float:
        """Calculate success rate over last N attempts."""
        recent = self.records[-last_n:] if self.records else []
        if not recent:
            return 0.5
        correct = sum(1 for r in recent if r.is_correct)
        return correct / len(recent)
    
    def get_average_response_time(self, last_n: int = 5) -> float:
        """Calculate average response time over last N attempts."""
        recent = self.records[-last_n:] if self.records else []
        if not recent:
            return 0.0
        return sum(r.response_time_ms for r in recent) / len(recent)


# =============================================================================
# Reinforcement Bank
# =============================================================================


class ReinforcementBank:
    """
    Generator for spaced repetition reinforcement items.
    
    Creates micro-checks for each concept including recall prompts,
    SQL completions, misconception discrimination, and query choice items.
    All items are designed to be completable in 10-30 seconds.
    
    Example:
        bank = ReinforcementBank()
        
        # Generate all item types for a concept
        items = bank.generate_for_concept(
            concept_id="group-by",
            concept_units=[unit1, unit2],
            config=ReinforcementConfig()
        )
        
        # Generate specific item types
        recall = bank.generate_recall_prompt(
            "group-by",
            definition="Groups rows with same values",
            key_points=["Required with aggregates", "Multiple columns allowed"]
        )
    """
    
    def __init__(self):
        """Initialize the reinforcement bank."""
        self._items: dict[str, ReinforcementItem] = {}
        self._concept_items: dict[str, list[str]] = {}
        self._misconception_bank = MisconceptionBank.load_default()
        
        # Template banks for generation
        self._recall_templates = self._load_recall_templates()
        self._completion_templates = self._load_completion_templates()
        self._scenario_templates = self._load_scenario_templates()
    
    def _load_recall_templates(self) -> dict[str, list[dict]]:
        """Load recall prompt templates by concept type."""
        return {
            "default": [
                {
                    "template": "In 1 sentence, what does {concept} do?",
                    "expected": "{definition}",
                },
                {
                    "template": "What is the main purpose of {concept}?",
                    "expected": "{key_point}",
                },
                {
                    "template": "When would you use {concept}?",
                    "expected": "{use_case}",
                },
            ],
            "select-basic": [
                {
                    "template": "What is the basic syntax of a SELECT statement?",
                    "expected": "SELECT column1, column2 FROM table_name;",
                },
                {
                    "template": "What does SELECT * retrieve?",
                    "expected": "All columns from the specified table",
                },
                {
                    "template": "In what order do SELECT and FROM appear?",
                    "expected": "SELECT comes first, then FROM",
                },
            ],
            "where-clause": [
                {
                    "template": "What is the difference between WHERE and HAVING?",
                    "expected": "WHERE filters rows before grouping; HAVING filters groups after aggregation",
                },
                {
                    "template": "How do you check for NULL values in SQL?",
                    "expected": "Use IS NULL or IS NOT NULL, never = NULL",
                },
                {
                    "template": "Can you use aggregate functions in a WHERE clause?",
                    "expected": "No, aggregate functions can only be used in HAVING clauses",
                },
            ],
            "joins": [
                {
                    "template": "What is the difference between INNER JOIN and LEFT JOIN?",
                    "expected": "INNER JOIN returns only matching rows; LEFT JOIN returns all rows from the left table",
                },
                {
                    "template": "What is required after the JOIN keyword?",
                    "expected": "An ON clause specifying the join condition",
                },
                {
                    "template": "What happens if you omit the ON clause in a JOIN?",
                    "expected": "You get a Cartesian product (every row combined with every row)",
                },
            ],
            "group-by": [
                {
                    "template": "When is GROUP BY required?",
                    "expected": "When using aggregate functions with non-aggregated columns",
                },
                {
                    "template": "What columns must appear in GROUP BY?",
                    "expected": "All non-aggregated columns in the SELECT list",
                },
                {
                    "template": "Where does GROUP BY appear in the SQL order?",
                    "expected": "After WHERE and before HAVING or ORDER BY",
                },
            ],
            "aggregate-functions": [
                {
                    "template": "What does COUNT(*) count?",
                    "expected": "All rows including those with NULL values",
                },
                {
                    "template": "What is the difference between COUNT(*) and COUNT(column)?",
                    "expected": "COUNT(*) counts all rows; COUNT(column) counts only non-NULL values",
                },
                {
                    "template": "Which aggregate ignores NULL values?",
                    "expected": "All aggregates except COUNT(*) ignore NULL values",
                },
            ],
            "subqueries": [
                {
                    "template": "When should you use IN instead of = with a subquery?",
                    "expected": "When the subquery might return multiple rows",
                },
                {
                    "template": "What is a correlated subquery?",
                    "expected": "A subquery that references columns from the outer query",
                },
                {
                    "template": "Where can subqueries be used?",
                    "expected": "In SELECT, FROM, WHERE, and HAVING clauses",
                },
            ],
        }
    
    def _load_completion_templates(self) -> dict[str, list[dict]]:
        """Load SQL completion templates by concept."""
        return {
            "select-basic": [
                {
                    "sql": "SELECT first_name, last_name\nFROM employees\nWHERE department = _____;",
                    "answer": "'Sales'",
                    "hint": "Use a string literal in quotes",
                },
                {
                    "sql": "SELECT _____(*)\nFROM products\nWHERE price > 100;",
                    "answer": "COUNT",
                    "hint": "Function to count rows",
                },
                {
                    "sql": "SELECT product_name\nFROM inventory\nORDER BY quantity _____;",
                    "answer": "DESC",
                    "hint": "Descending order keyword",
                },
            ],
            "where-clause": [
                {
                    "sql": "SELECT *\nFROM employees\nWHERE manager_id _____ NULL;",
                    "answer": "IS",
                    "hint": "Correct operator for NULL comparison",
                },
                {
                    "sql": "SELECT name\nFROM customers\nWHERE country _____ ('USA', 'UK', 'Canada');",
                    "answer": "IN",
                    "hint": "Operator to check multiple values",
                },
                {
                    "sql": "SELECT product_name\nFROM products\nWHERE price _____ 10 AND price _____ 100;",
                    "answer": ">=, <=",
                    "hint": "Between range operators",
                },
            ],
            "joins": [
                {
                    "sql": "SELECT e.name, d.name\nFROM employees e\n_____ JOIN departments d\nON e.dept_id = d.id;",
                    "answer": "INNER",
                    "hint": "Default join type for matching rows",
                },
                {
                    "sql": "SELECT c.name, o.total\nFROM customers c\nLEFT JOIN orders o\n_____ c.id = o.customer_id;",
                    "answer": "ON",
                    "hint": "Keyword before join condition",
                },
                {
                    "sql": "SELECT _____(e.salary)\nFROM employees e\nJOIN departments d ON e.dept_id = d.id;",
                    "answer": "AVG",
                    "hint": "Aggregate function for average",
                },
            ],
            "group-by": [
                {
                    "sql": "SELECT department, _____(salary)\nFROM employees\nGROUP BY department;",
                    "answer": "AVG",
                    "hint": "Aggregate function for average",
                },
                {
                    "sql": "SELECT city, state, COUNT(*)\nFROM customers\nGROUP BY _____, _____;",
                    "answer": "city, state",
                    "hint": "Both non-aggregated columns",
                },
                {
                    "sql": "SELECT category, SUM(price)\nFROM products\n_____ BY category;",
                    "answer": "GROUP",
                    "hint": "Clause for grouping rows",
                },
            ],
            "aggregate-functions": [
                {
                    "sql": "SELECT _____, MAX(salary)\nFROM employees;",
                    "answer": "department",
                    "hint": "Column to group by",
                },
                {
                    "sql": "SELECT _____(*)\nFROM orders\nWHERE status = 'completed';",
                    "answer": "COUNT",
                    "hint": "Function to count all matching rows",
                },
                {
                    "sql": "SELECT department, _____(salary) as avg_salary\nFROM employees\nGROUP BY department;",
                    "answer": "AVG",
                    "hint": "Function to calculate average",
                },
            ],
            "having": [
                {
                    "sql": "SELECT department, COUNT(*)\nFROM employees\nGROUP BY department\n_____ COUNT(*) > 5;",
                    "answer": "HAVING",
                    "hint": "Clause to filter groups",
                },
                {
                    "sql": "SELECT category, AVG(price) as avg_price\nFROM products\nGROUP BY category\nHAVING _____(price) > 100;",
                    "answer": "AVG",
                    "hint": "Aggregate function in HAVING",
                },
                {
                    "sql": "SELECT dept_id, SUM(salary) as total\nFROM employees\nGROUP BY dept_id\nHAVING total _____ 100000;",
                    "answer": ">",
                    "hint": "Greater than operator",
                },
            ],
            "subqueries": [
                {
                    "sql": "SELECT name\nFROM employees\nWHERE dept_id _____ (SELECT id FROM departments WHERE location = 'NYC');",
                    "answer": "IN",
                    "hint": "Operator for multiple possible values",
                },
                {
                    "sql": "SELECT product_name\nFROM products\nWHERE price > (SELECT _____(price) FROM products);",
                    "answer": "AVG",
                    "hint": "Aggregate function for average",
                },
                {
                    "sql": "SELECT *\nFROM employees\nWHERE salary > (SELECT salary FROM employees WHERE name _____ 'Smith');",
                    "answer": "=",
                    "hint": "Equality operator for single value",
                },
            ],
        }
    
    def _load_scenario_templates(self) -> dict[str, list[dict]]:
        """Load scenario templates for query choice items."""
        return {
            "select-basic": [
                {
                    "scenario": "Get all employees from the Sales department",
                    "query_a": "SELECT * FROM employees WHERE department = 'Sales';",
                    "query_b": "SELECT * FROM employees WHERE department = Sales;",
                    "better": "a",
                    "reason": "String literals must be quoted in SQL",
                },
                {
                    "scenario": "List employee names ordered by hire date (newest first)",
                    "query_a": "SELECT name FROM employees ORDER BY hire_date;",
                    "query_b": "SELECT name FROM employees ORDER BY hire_date DESC;",
                    "better": "b",
                    "reason": "DESC gives newest first; default ASC gives oldest first",
                },
            ],
            "where-clause": [
                {
                    "scenario": "Find employees with no manager (manager_id is NULL)",
                    "query_a": "SELECT * FROM employees WHERE manager_id = NULL;",
                    "query_b": "SELECT * FROM employees WHERE manager_id IS NULL;",
                    "better": "b",
                    "reason": "Must use IS NULL, not = NULL for NULL comparisons",
                },
                {
                    "scenario": "Find customers in the USA, UK, or Canada",
                    "query_a": "SELECT * FROM customers WHERE country = 'USA' OR country = 'UK' OR country = 'Canada';",
                    "query_b": "SELECT * FROM customers WHERE country IN ('USA', 'UK', 'Canada');",
                    "better": "b",
                    "reason": "IN operator is cleaner and more efficient for multiple values",
                },
            ],
            "joins": [
                {
                    "scenario": "List all employees and their department names (include employees without departments)",
                    "query_a": "SELECT e.name, d.name FROM employees e INNER JOIN departments d ON e.dept_id = d.id;",
                    "query_b": "SELECT e.name, d.name FROM employees e LEFT JOIN departments d ON e.dept_id = d.id;",
                    "better": "b",
                    "reason": "LEFT JOIN includes all employees, even those without matching departments",
                },
                {
                    "scenario": "Get matching employees and departments with proper join condition",
                    "query_a": "SELECT e.name, d.name FROM employees e, departments d WHERE e.dept_id = d.id;",
                    "query_b": "SELECT e.name, d.name FROM employees e JOIN departments d ON e.dept_id = d.id;",
                    "better": "b",
                    "reason": "Explicit JOIN syntax is clearer and less prone to accidental Cartesian products",
                },
            ],
            "group-by": [
                {
                    "scenario": "Count employees per department",
                    "query_a": "SELECT department, COUNT(*) FROM employees;",
                    "query_b": "SELECT department, COUNT(*) FROM employees GROUP BY department;",
                    "better": "b",
                    "reason": "GROUP BY is required when using aggregates with non-aggregated columns",
                },
                {
                    "scenario": "Get average salary by department for departments with more than 5 employees",
                    "query_a": "SELECT department, AVG(salary) FROM employees WHERE COUNT(*) > 5 GROUP BY department;",
                    "query_b": "SELECT department, AVG(salary) FROM employees GROUP BY department HAVING COUNT(*) > 5;",
                    "better": "b",
                    "reason": "HAVING (not WHERE) must be used for conditions on aggregate functions",
                },
            ],
            "aggregate-functions": [
                {
                    "scenario": "Calculate total payroll (sum of all salaries)",
                    "query_a": "SELECT COUNT(salary) FROM employees;",
                    "query_b": "SELECT SUM(salary) FROM employees;",
                    "better": "b",
                    "reason": "SUM adds values; COUNT just counts rows",
                },
                {
                    "scenario": "Count all employees including those without email addresses",
                    "query_a": "SELECT COUNT(email) FROM employees;",
                    "query_b": "SELECT COUNT(*) FROM employees;",
                    "better": "b",
                    "reason": "COUNT(*) counts all rows; COUNT(column) excludes NULL values",
                },
            ],
            "subqueries": [
                {
                    "scenario": "Find employees in departments located in 'NYC' (subquery may return multiple departments)",
                    "query_a": "SELECT * FROM employees WHERE dept_id = (SELECT id FROM departments WHERE location = 'NYC');",
                    "query_b": "SELECT * FROM employees WHERE dept_id IN (SELECT id FROM departments WHERE location = 'NYC');",
                    "better": "b",
                    "reason": "IN must be used when subquery can return multiple rows; = expects single value",
                },
                {
                    "scenario": "Find products priced above the average price",
                    "query_a": "SELECT * FROM products WHERE price > AVG(price);",
                    "query_b": "SELECT * FROM products WHERE price > (SELECT AVG(price) FROM products);",
                    "better": "b",
                    "reason": "Aggregate functions in WHERE need a subquery; they can't reference the outer table directly",
                },
            ],
        }
    
    def generate_for_concept(
        self,
        concept_id: str,
        concept_units: list[InstructionalUnit],
        config: ReinforcementConfig | None = None,
    ) -> list[ReinforcementItem]:
        """
        Generate all 4 types of reinforcement items for a concept.
        
        Args:
            concept_id: The concept identifier (e.g., 'group-by', 'joins')
            concept_units: List of instructional units for this concept
            config: Generation configuration
            
        Returns:
            List of ReinforcementItem objects for all types
        """
        config = config or ReinforcementConfig()
        items: list[ReinforcementItem] = []
        
        # Extract content from units
        definition = self._extract_definition(concept_units)
        key_points = self._extract_key_points(concept_units)
        examples = self._extract_examples(concept_units)
        
        # Generate recall prompts
        for i in range(config.recall_prompts_per_concept):
            item = self.generate_recall_prompt(
                concept_id, definition, key_points, i + 1, config
            )
            if item:
                items.append(item)
        
        # Generate SQL completions
        for i in range(config.sql_completions_per_concept):
            item = self.generate_sql_completion(
                concept_id, examples, i + 1, config
            )
            if item:
                items.append(item)
        
        # Generate misconception discrimination items
        for i in range(config.misconception_items_per_concept):
            item = self.generate_misconception_discrimination(
                concept_id, examples, i + 1, config
            )
            if item:
                items.append(item)
        
        # Generate query choice items
        for i in range(config.query_choice_items_per_concept):
            item = self.generate_query_choice(
                concept_id, examples, i + 1, config
            )
            if item:
                items.append(item)
        
        # Store items in bank
        for item in items:
            self._items[item.item_id] = item
            if item.concept_id not in self._concept_items:
                self._concept_items[item.concept_id] = []
            self._concept_items[item.concept_id].append(item.item_id)
        
        return items
    
    def generate_recall_prompt(
        self,
        concept_id: str,
        definition: str,
        key_points: list[str],
        variant: int = 1,
        config: ReinforcementConfig | None = None,
    ) -> ReinforcementItem | None:
        """
        Generate a 10-second recall prompt.
        
        Args:
            concept_id: The concept identifier
            definition: Concept definition text
            key_points: List of key learning points
            variant: Variant number for ID generation
            config: Generation configuration
            
        Returns:
            ReinforcementItem with recall prompt
        """
        config = config or ReinforcementConfig()
        
        # Get templates for this concept or use default
        templates = self._recall_templates.get(concept_id, self._recall_templates["default"])
        
        if not templates:
            return None
        
        # Select template based on variant
        template = templates[(variant - 1) % len(templates)]
        
        # Format prompt
        prompt = template["template"].format(
            concept=concept_id.replace("-", " ").title(),
            definition=definition[:100] if definition else "",
            key_point=key_points[0] if key_points else "",
            use_case="when working with related data",
        )
        
        expected = template["expected"].format(
            concept=concept_id.replace("-", " ").title(),
            definition=definition[:100] if definition else f"Definition of {concept_id}",
            key_point=key_points[0] if key_points else f"Key concept for {concept_id}",
            use_case=f"when working with {concept_id.replace('-', ' ')}",
        )
        
        # Ensure expected answer is not empty
        if not expected or not expected.strip():
            expected = f"Understand and apply {concept_id.replace('-', ' ')} correctly"
        
        return ReinforcementItem(
            item_id=f"{concept_id}_recall_{variant:03d}",
            concept_id=concept_id,
            item_type="recall_prompt",
            prompt=prompt,
            expected_answer=expected,
            estimated_time_seconds=config.recall_time_seconds,
        )
    
    def generate_sql_completion(
        self,
        concept_id: str,
        examples: list[dict],
        variant: int = 1,
        config: ReinforcementConfig | None = None,
    ) -> ReinforcementItem | None:
        """
        Generate a fill-in-the-blank SQL completion item.
        
        Args:
            concept_id: The concept identifier
            examples: List of SQL examples from instructional units
            variant: Variant number for ID generation
            config: Generation configuration
            
        Returns:
            ReinforcementItem with SQL completion
        """
        config = config or ReinforcementConfig()
        
        # Get templates for this concept
        templates = self._completion_templates.get(concept_id, [])
        
        if not templates:
            # Generate generic completion if no templates
            return self._generate_generic_completion(concept_id, variant, config)
        
        # Select template based on variant
        template = templates[(variant - 1) % len(templates)]
        
        prompt = f"""Fill in the blank(s) to complete this SQL query:

```sql
{template['sql']}
```

Hint: {template['hint']}"""
        
        return ReinforcementItem(
            item_id=f"{concept_id}_completion_{variant:03d}",
            concept_id=concept_id,
            item_type="sql_completion",
            prompt=prompt,
            expected_answer=template["answer"],
            estimated_time_seconds=config.completion_time_seconds,
        )
    
    def generate_misconception_discrimination(
        self,
        concept_id: str,
        examples: list[dict],
        variant: int = 1,
        config: ReinforcementConfig | None = None,
    ) -> ReinforcementItem | None:
        """
        Generate a misconception discrimination item.
        
        Presents two SQL snippets (one correct, one with common error)
        and asks student to identify which has the error.
        
        Args:
            concept_id: The concept identifier
            examples: List of SQL examples
            variant: Variant number for ID generation
            config: Generation configuration
            
        Returns:
            ReinforcementItem with discrimination question
        """
        config = config or ReinforcementConfig()
        
        # Get misconception patterns for this concept
        patterns = self._misconception_bank.get_patterns_for_concept(concept_id)
        
        if not patterns:
            # Use generic patterns
            patterns = self._get_generic_misconceptions(concept_id)
        
        if not patterns:
            return None
        
        # Select pattern based on variant
        pattern = patterns[(variant - 1) % len(patterns)]
        
        # Randomize which option is correct
        correct_first = random.choice([True, False])
        
        if correct_first:
            query_a = pattern.example_good_sql
            query_b = pattern.example_bad_sql
            correct_answer = "A"
        else:
            query_a = pattern.example_bad_sql
            query_b = pattern.example_good_sql
            correct_answer = "B"
        
        prompt = f"""Which query has an error? Identify the error and explain why it's wrong.

**Query A:**
```sql
{query_a}
```

**Query B:**
```sql
{query_b}
```"""
        
        expected = f"""Query {correct_answer} has the error.

Error: {pattern.pattern_name}
Explanation: {pattern.learner_symptom}

{self._get_fix_explanation(pattern)}"""
        
        return ReinforcementItem(
            item_id=f"{concept_id}_discrim_{variant:03d}",
            concept_id=concept_id,
            item_type="misconception_discrimination",
            prompt=prompt,
            expected_answer=expected,
            estimated_time_seconds=config.discrimination_time_seconds,
        )
    
    def generate_query_choice(
        self,
        concept_id: str,
        examples: list[dict],
        variant: int = 1,
        config: ReinforcementConfig | None = None,
    ) -> ReinforcementItem | None:
        """
        Generate a choose-better-query item.
        
        Presents a scenario and two query options,
        student picks the better query with justification.
        
        Args:
            concept_id: The concept identifier
            examples: List of SQL examples
            variant: Variant number for ID generation
            config: Generation configuration
            
        Returns:
            ReinforcementItem with query choice question
        """
        config = config or ReinforcementConfig()
        
        # Get scenario templates for this concept
        templates = self._scenario_templates.get(concept_id, [])
        
        if not templates:
            return None
        
        # Select template based on variant
        template = templates[(variant - 1) % len(templates)]
        
        prompt = f"""Given this scenario, which query is better?

**Scenario:** {template['scenario']}

**Query A:**
```sql
{template['query_a']}
```

**Query B:**
```sql
{template['query_b']}
```

Select the better query and explain your choice."""
        
        expected = f"""Query {template['better'].upper()} is better.

Reason: {template['reason']}"""
        
        return ReinforcementItem(
            item_id=f"{concept_id}_choice_{variant:03d}",
            concept_id=concept_id,
            item_type="query_choice",
            prompt=prompt,
            expected_answer=expected,
            estimated_time_seconds=config.choice_time_seconds,
        )
    
    def get_items_for_concept(self, concept_id: str) -> list[ReinforcementItem]:
        """Get all reinforcement items for a concept."""
        item_ids = self._concept_items.get(concept_id, [])
        return [self._items[item_id] for item_id in item_ids if item_id in self._items]
    
    def get_items_by_type(
        self, concept_id: str, item_type: ReinforcementType
    ) -> list[ReinforcementItem]:
        """Get reinforcement items of a specific type for a concept."""
        items = self.get_items_for_concept(concept_id)
        return [item for item in items if item.item_type == item_type]
    
    def get_all_items(self) -> list[ReinforcementItem]:
        """Get all reinforcement items in the bank."""
        return list(self._items.values())
    
    def _extract_definition(self, units: list[InstructionalUnit]) -> str:
        """Extract definition from instructional units."""
        for unit in units:
            content = unit.content
            if isinstance(content, dict):
                if "definition" in content:
                    return content["definition"]
                if "text" in content:
                    return content["text"][:200]
        return ""
    
    def _extract_key_points(self, units: list[InstructionalUnit]) -> list[str]:
        """Extract key points from instructional units."""
        points: list[str] = []
        for unit in units:
            content = unit.content
            if isinstance(content, dict):
                if "key_points" in content:
                    points.extend(content["key_points"])
                if "bullet_points" in content:
                    points.extend(content["bullet_points"])
        return points[:5] if points else ["Master the syntax", "Practice with examples"]
    
    def _extract_examples(self, units: list[InstructionalUnit]) -> list[dict]:
        """Extract SQL examples from instructional units."""
        examples: list[dict] = []
        for unit in units:
            content = unit.content
            if isinstance(content, dict):
                if "examples" in content:
                    examples.extend(content["examples"])
                if "sql" in content:
                    examples.append({"sql": content["sql"], "explanation": content.get("text", "")})
        return examples
    
    def _generate_generic_completion(
        self, concept_id: str, variant: int, config: ReinforcementConfig
    ) -> ReinforcementItem | None:
        """Generate a generic SQL completion when no templates exist."""
        generic_templates = [
            {
                "sql": f"SELECT *\nFROM table_name\nWHERE column _____ value;",
                "answer": "=",
                "hint": "Equality comparison operator",
            },
            {
                "sql": f"SELECT column1, column2\nFROM table_name\n_____ BY column1;",
                "answer": "ORDER",
                "hint": "Clause for sorting results",
            },
            {
                "sql": f"SELECT _____, column2\nFROM table_name;",
                "answer": "column1",
                "hint": "First column name",
            },
        ]
        
        template = generic_templates[(variant - 1) % len(generic_templates)]
        
        prompt = f"""Fill in the blank to complete this SQL query:

```sql
{template['sql']}
```

Hint: {template['hint']}"""
        
        return ReinforcementItem(
            item_id=f"{concept_id}_completion_{variant:03d}",
            concept_id=concept_id,
            item_type="sql_completion",
            prompt=prompt,
            expected_answer=template["answer"],
            estimated_time_seconds=config.completion_time_seconds,
        )
    
    def _get_generic_misconceptions(self, concept_id: str) -> list[MisconceptionPattern]:
        """Get generic misconception patterns for concepts without specific ones."""
        return [
            MisconceptionPattern(
                pattern_id="syntax_error_generic",
                error_subtype_id="syntax_error",
                concept_id=concept_id,
                pattern_name="General Syntax Error",
                learner_symptom="SQL syntax error or unexpected behavior",
                likely_prereq_failure=None,
                sql_pattern=r".*",
                remediation_order=1,
                example_bad_sql="SELECT col1 col2 FROM table;",
                example_good_sql="SELECT col1, col2 FROM table;",
            ),
        ]
    
    def _get_fix_explanation(self, pattern: MisconceptionPattern) -> str:
        """Get explanation for fixing a misconception."""
        explanations = {
            "missing_comma_select_v1": "Add commas between columns in SELECT list.",
            "extra_comma_select_v1": "Remove the trailing comma before FROM.",
            "incorrect_null_comparison_v1": "Use IS NULL instead of = NULL.",
            "missing_join_condition_v1": "Add an ON clause with join conditions.",
            "missing_group_by_v1": "Add GROUP BY with all non-aggregated columns.",
            "where_having_confusion_v1": "Move aggregate conditions to HAVING clause.",
            "subquery_multiple_rows_v1": "Use IN instead of = for multi-row subqueries.",
        }
        return explanations.get(pattern.pattern_id, "Review the correct syntax.")


# =============================================================================
# Spaced Repetition Scheduler (SM-2 Algorithm)
# =============================================================================


class SpacedRepetitionScheduler:
    """
    SM-2 based spaced repetition scheduler.
    
    Implements the SuperMemo-2 algorithm for calculating optimal review intervals
    based on learner performance. Adapts intervals based on how well the learner
    remembers each concept.
    
    The SM-2 algorithm:
    - Quality of response (0-5) determines next interval
    - EF (ease factor) adjusts based on performance
    - Intervals grow exponentially for well-remembered items
    - Difficult items are reviewed more frequently
    
    Example:
        scheduler = SpacedRepetitionScheduler()
        
        # After a review
        next_date = scheduler.calculate_next_review(
            "group-by",
            history,
            quality=4  # 0-5 rating of how well they knew it
        )
        
        # Get items due today
        due_items = scheduler.get_due_items(bank, learner_history, today)
    """
    
    def __init__(
        self,
        initial_interval: int = 1,
        default_ease_factor: float = 2.5,
        min_ease_factor: float = 1.3,
    ):
        """
        Initialize the scheduler.
        
        Args:
            initial_interval: First review interval in days (default: 1)
            default_ease_factor: Starting ease factor (default: 2.5)
            min_ease_factor: Minimum ease factor (default: 1.3)
        """
        self.initial_interval = initial_interval
        self.default_ease_factor = default_ease_factor
        self.min_ease_factor = min_ease_factor
    
    def calculate_next_review(
        self,
        concept_id: str,
        performance_history: dict[str, ConceptPerformanceHistory],
        quality: int | None = None,
    ) -> datetime:
        """
        Calculate the next review date for a concept.
        
        Uses SM-2 algorithm to determine optimal review timing based on
        historical performance and latest quality rating.
        
        Args:
            concept_id: The concept to schedule
            performance_history: Map of concept_id to performance history
            quality: Quality of response (0-5), auto-calculated if None
            
        Returns:
            datetime for next review
        """
        now = datetime.now(timezone.utc)
        
        # Get or create history for this concept
        history = performance_history.get(concept_id)
        if history is None:
            # First review - schedule for tomorrow
            return now + timedelta(days=self.initial_interval)
        
        # Calculate quality if not provided
        if quality is None:
            quality = self._calculate_quality_from_history(history)
        
        # Clamp quality to valid range
        quality = max(0, min(5, quality))
        
        # Get current interval and ease factor
        interval = history.current_interval_days
        ease_factor = history.ease_factor
        repetitions = history.review_count
        
        # Apply SM-2 algorithm
        if quality < 3:
            # Failed response - reset interval
            new_interval = self.initial_interval
            repetitions = 0
        elif repetitions == 0:
            # First successful response
            new_interval = 1
        elif repetitions == 1:
            # Second successful response
            new_interval = 6
        else:
            # Subsequent successful responses
            new_interval = interval * ease_factor
        
        # Update ease factor
        new_ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        new_ease_factor = max(self.min_ease_factor, new_ease_factor)
        
        # Update history
        history.current_interval_days = new_interval
        history.ease_factor = new_ease_factor
        
        return now + timedelta(days=new_interval)
    
    def get_due_items(
        self,
        reinforcement_bank: ReinforcementBank,
        learner_history: dict[str, ConceptPerformanceHistory],
        date: datetime | None = None,
    ) -> list[ReinforcementItem]:
        """
        Get reinforcement items due for review on a specific date.
        
        Args:
            reinforcement_bank: The bank of reinforcement items
            learner_history: Map of concept_id to performance history
            date: Date to check (default: today)
            
        Returns:
            List of ReinforcementItem due for review
        """
        if date is None:
            date = datetime.now(timezone.utc)
        
        due_items: list[ReinforcementItem] = []
        
        for concept_id, history in learner_history.items():
            # Calculate next review date
            next_review = self.calculate_next_review(
                concept_id, learner_history, quality=None
            )
            
            # Check if due
            if next_review.date() <= date.date():
                # Get items for this concept
                items = reinforcement_bank.get_items_for_concept(concept_id)
                
                # Prioritize by item type (mix of all types)
                items_by_type: dict[str, list[ReinforcementItem]] = {
                    "recall_prompt": [],
                    "sql_completion": [],
                    "misconception_discrimination": [],
                    "query_choice": [],
                }
                
                for item in items:
                    if item.item_type in items_by_type:
                        items_by_type[item.item_type].append(item)
                
                # Add one of each type if available
                for item_type, type_items in items_by_type.items():
                    if type_items:
                        due_items.append(type_items[0])
        
        return due_items
    
    def _calculate_quality_from_history(
        self, history: ConceptPerformanceHistory
    ) -> int:
        """
        Calculate quality rating from performance history.
        
        Maps success rate and response time to a 0-5 quality rating.
        
        Args:
            history: Performance history for a concept
            
        Returns:
            Quality rating (0-5)
        """
        success_rate = history.get_success_rate(last_n=3)
        avg_time = history.get_average_response_time(last_n=3)
        
        # Base quality on success rate
        if success_rate >= 0.9:
            quality = 5
        elif success_rate >= 0.7:
            quality = 4
        elif success_rate >= 0.5:
            quality = 3
        elif success_rate >= 0.3:
            quality = 2
        elif success_rate > 0:
            quality = 1
        else:
            quality = 0
        
        # Adjust for response time (faster = slightly better)
        if avg_time < 10000:  # Under 10 seconds
            quality = min(5, quality + 1)
        elif avg_time > 60000:  # Over 60 seconds
            quality = max(0, quality - 1)
        
        return quality


# =============================================================================
# Reinforcement Session
# =============================================================================


class ReinforcementSession:
    """
    Manages micro-learning sessions with reinforcement items.
    
    Creates focused learning sessions with a mix of item types,
    tracks responses, and updates learner history.
    
    Example:
        session = ReinforcementSession()
        
        # Create a session with items from multiple concepts
        micro_session = session.create_session(
            ["group-by", "joins", "where-clause"],
            bank,
            max_items=5
        )
        
        # Record a response
        result = session.record_response(
            item_id="group-by:recall:001",
            is_correct=True,
            response_time_ms=8500
        )
    """
    
    def __init__(self):
        """Initialize the session manager."""
        self._session_items: list[ReinforcementItem] = []
        self._session_responses: list[dict] = []
        self._current_session: dict | None = None
    
    def create_session(
        self,
        concept_ids: list[str],
        bank: ReinforcementBank,
        max_items: int = 5,
        scheduler: SpacedRepetitionScheduler | None = None,
        learner_history: dict[str, ConceptPerformanceHistory] | None = None,
    ) -> dict:
        """
        Create a micro-learning session with mixed item types.
        
        Args:
            concept_ids: List of concept IDs to include
            bank: Reinforcement bank with items
            max_items: Maximum number of items in session
            scheduler: Optional scheduler to prioritize due items
            learner_history: Optional learner history for scheduling
            
        Returns:
            Session dictionary with items and metadata
        """
        # Collect items from all concepts
        all_items: list[ReinforcementItem] = []
        
        for concept_id in concept_ids:
            items = bank.get_items_for_concept(concept_id)
            all_items.extend(items)
        
        # If scheduler provided, prioritize due items
        if scheduler and learner_history:
            due_items = scheduler.get_due_items(bank, learner_history)
            due_ids = {item.item_id for item in due_items}
            
            # Sort: due items first, then shuffle others
            all_items.sort(key=lambda item: item.item_id not in due_ids)
        else:
            # Shuffle for variety
            random.shuffle(all_items)
        
        # Select items ensuring type variety
        selected_items: list[ReinforcementItem] = []
        items_by_type: dict[str, list[ReinforcementItem]] = {
            "recall_prompt": [],
            "sql_completion": [],
            "misconception_discrimination": [],
            "query_choice": [],
        }
        
        for item in all_items:
            if item.item_type in items_by_type:
                items_by_type[item.item_type].append(item)
        
        # Round-robin selection for variety
        type_order = list(items_by_type.keys())
        type_index = 0
        
        while len(selected_items) < max_items:
            item_type = type_order[type_index % len(type_order)]
            type_items = items_by_type[item_type]
            
            if type_items:
                selected_items.append(type_items.pop(0))
            
            type_index += 1
            
            # Break if no more items
            if not any(items_by_type.values()):
                break
        
        self._session_items = selected_items
        self._session_responses = []
        
        # Calculate total estimated time
        total_time = sum(item.estimated_time_seconds for item in selected_items)
        
        session = {
            "session_id": self._generate_session_id(),
            "items": [item.model_dump() for item in selected_items],
            "item_count": len(selected_items),
            "concepts": concept_ids,
            "estimated_time_seconds": total_time,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        
        self._current_session = session
        return session
    
    def record_response(
        self,
        item_id: str,
        is_correct: bool,
        response_time_ms: int,
        difficulty_rating: int | None = None,
    ) -> dict:
        """
        Record a learner's response to an item.
        
        Args:
            item_id: ID of the item responded to
            is_correct: Whether the response was correct
            response_time_ms: Time taken to respond in milliseconds
            difficulty_rating: Optional 1-5 self-reported difficulty
            
        Returns:
            Response record with updated statistics
        """
        response = {
            "item_id": item_id,
            "is_correct": is_correct,
            "response_time_ms": response_time_ms,
            "difficulty_rating": difficulty_rating,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        
        self._session_responses.append(response)
        
        # Calculate session stats
        total_responses = len(self._session_responses)
        correct_count = sum(1 for r in self._session_responses if r["is_correct"])
        accuracy = correct_count / total_responses if total_responses > 0 else 0
        avg_time = sum(r["response_time_ms"] for r in self._session_responses) / total_responses
        
        return {
            "response": response,
            "session_progress": {
                "answered": total_responses,
                "total": len(self._session_items),
                "accuracy": round(accuracy, 2),
                "average_time_ms": round(avg_time, 0),
            },
        }
    
    def get_session_summary(self) -> dict:
        """Get summary of the current session."""
        if not self._current_session:
            return {"error": "No active session"}
        
        total_items = len(self._session_items)
        answered = len(self._session_responses)
        correct = sum(1 for r in self._session_responses if r["is_correct"])
        
        return {
            "session_id": self._current_session.get("session_id"),
            "completed": answered >= total_items,
            "total_items": total_items,
            "answered": answered,
            "correct": correct,
            "accuracy": round(correct / answered, 2) if answered > 0 else 0,
            "concepts": self._current_session.get("concepts", []),
        }
    
    def update_learner_history(
        self,
        learner_history: dict[str, ConceptPerformanceHistory],
    ) -> dict[str, ConceptPerformanceHistory]:
        """
        Update learner history with session responses.
        
        Args:
            learner_history: Existing learner history to update
            
        Returns:
            Updated learner history
        """
        for response in self._session_responses:
            item_id = response["item_id"]
            
            # Extract concept_id from item_id (format: concept_id_type_variant)
            concept_id = item_id.rsplit("_", 2)[0] if "_" in item_id else item_id
            
            # Get or create history for this concept
            if concept_id not in learner_history:
                learner_history[concept_id] = ConceptPerformanceHistory(
                    concept_id=concept_id
                )
            
            history = learner_history[concept_id]
            
            # Create performance record
            record = PerformanceRecord(
                item_id=item_id,
                concept_id=concept_id,
                answered_at=datetime.fromisoformat(response["recorded_at"]),
                is_correct=response["is_correct"],
                response_time_ms=response["response_time_ms"],
                difficulty_rating=response.get("difficulty_rating"),
            )
            
            history.add_record(record)
        
        return learner_history
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        random_suffix = random.randint(1000, 9999)
        return f"session_{timestamp}_{random_suffix}"


# =============================================================================
# Utility Functions
# =============================================================================


def create_default_bank(
    concept_ids: list[str] | None = None,
) -> ReinforcementBank:
    """
    Create a reinforcement bank with default items.
    
    Args:
        concept_ids: List of concept IDs to generate items for.
                     If None, uses common SQL concepts.
    
    Returns:
        Populated ReinforcementBank
    """
    if concept_ids is None:
        concept_ids = [
            "select-basic",
            "where-clause",
            "joins",
            "inner-join",
            "outer-join",
            "aggregate-functions",
            "group-by",
            "having",
            "subqueries",
            "order-by",
        ]
    
    bank = ReinforcementBank()
    config = ReinforcementConfig()
    
    # Generate items for each concept (with empty units list)
    for concept_id in concept_ids:
        bank.generate_for_concept(concept_id, [], config)
    
    return bank


def get_reinforcement_stats(bank: ReinforcementBank) -> dict[str, Any]:
    """
    Get statistics about a reinforcement bank.
    
    Args:
        bank: The reinforcement bank
        
    Returns:
        Dictionary with statistics
    """
    items = bank.get_all_items()
    
    stats = {
        "total_items": len(items),
        "items_by_type": {},
        "items_by_concept": {},
        "total_estimated_time_seconds": 0,
    }
    
    for item in items:
        # Count by type
        item_type = item.item_type
        stats["items_by_type"][item_type] = stats["items_by_type"].get(item_type, 0) + 1
        
        # Count by concept
        concept_id = item.concept_id
        stats["items_by_concept"][concept_id] = stats["items_by_concept"].get(concept_id, 0) + 1
        
        # Sum estimated time
        stats["total_estimated_time_seconds"] += item.estimated_time_seconds
    
    return stats
