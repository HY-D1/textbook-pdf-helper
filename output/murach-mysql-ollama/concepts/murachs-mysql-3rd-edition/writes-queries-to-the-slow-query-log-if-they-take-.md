# writes queries to the slow query log if they take longer than 5 seconds

## Definition

The slow query log is a feature in databases that records SQL queries that take longer than a specified amount of time to execute. This helps database administrators identify and optimize slow-performing queries.

## Explanation

Imagine you're building a house, and some parts of the construction are taking much longer than expected. The slow query log is like a handyman checking which tools or steps are causing delays. By identifying these slow parts (queries), we can make them more efficient, just like finding ways to speed up certain tasks during construction.

## Examples

### Basic Usage

```sql
-- Set the long_query_time to 5 seconds
SET GLOBAL long_query_time = 5;
```

This example shows how to set the `long_query_time` variable to log queries that take longer than 5 seconds. Setting this value helps in identifying slow queries for further optimization.

### Practical Example

```sql
-- Example of a query that might appear in the slow query log
SELECT * FROM users WHERE last_login < DATE_SUB(NOW(), INTERVAL 1 YEAR);
```

This practical example demonstrates what a slow query might look like. Queries like this could be optimized by adding an index on `last_login` to speed up the search.

## Common Mistakes

### Setting `long_query_time` too low

**Incorrect:**

```sql
-- Incorrectly setting long_query_time
SET GLOBAL long_query_time = 1;
```

**Correct:**

```sql
-- Correct way to set long_query_time
SET GLOBAL long_query_time = 5;
```

**Why this happens:** Setting the `long_query_time` too low might miss important slow queries that are still taking a significant amount of time. It's better to be conservative and set it to a reasonable value.

---

## Practice

**Question:** How would you configure your database to log queries that take longer than 10 seconds?

**Solution:** The solution is to set the `long_query_time` variable to 10. Here's how you can do it:

SET GLOBAL long_query_time = 10;

This will help in identifying and optimizing slow queries that are taking more than 10 seconds to execute.
