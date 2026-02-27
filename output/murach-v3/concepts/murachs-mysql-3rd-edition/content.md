# Content

## Definition

The SELECT statement is used in SQL to retrieve data from one or more tables in a database. It's essential for querying and analyzing data stored in MySQL databases.

## Explanation

The SELECT statement allows you to specify which columns of data you want to retrieve from a table. It works by selecting rows that meet certain conditions, defined using the WHERE clause. This is crucial for developers who need to access specific information from large datasets efficiently. Knowing how to use SELECT effectively can save time and improve the performance of your applications.

## Examples

### Basic Usage

```sql
-- Select all columns from a table
SELECT * FROM employees;
```

This example retrieves all columns (indicated by *) from the 'employees' table. It's useful when you need to view all available data.

### Practical Example

```sql
-- Select specific columns with conditions
SELECT name, salary FROM employees WHERE department = 'Sales';
```

This practical example retrieves the 'name' and 'salary' of employees in the 'Sales' department. It demonstrates how to specify column names and use a condition to filter data.

## Common Mistakes

### Forgetting the WHERE clause

**Incorrect:**

```sql
-- Incorrect: Returns all rows
SELECT name FROM employees;
```

**Correct:**

```sql
-- Correct: Filters by department
SELECT name FROM employees WHERE department = 'Sales';
```

**Why this happens:** This mistake happens when a developer assumes that SELECT will always return all data, forgetting to specify conditions. Always include the WHERE clause if you want to filter results.

---

## Practice

**Question:** Write a SELECT statement to retrieve the names and email addresses of customers who have made purchases over $1000.

**Solution:** -- Solution
SELECT c.name, c.email FROM customers c JOIN orders o ON c.customer_id = o.customer_id WHERE o.total > 1000;
-- Explanation: This query joins the 'customers' and 'orders' tables on the customer ID, then filters for orders with a total greater than $1000.
