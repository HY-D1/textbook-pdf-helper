# SELECT Statement Basics

🟢 **Difficulty:** Beginner
⏱️ **Estimated Time:** 10 minutes

## Learning Objectives

- Understand the basic structure of a SELECT statement
- Retrieve specific columns vs all columns using *
- Use table aliases for cleaner queries

## What is This?

The SELECT statement is the foundation of SQL queries, allowing you to retrieve data from one or more tables.

## Examples

### Example 1: Basic SELECT

**Difficulty:** Beginner

**Scenario:** Retrieve all information about users

```sql
SELECT * FROM users;
```

**Explanation:** The * wildcard selects all columns from the table.

**Expected Output:**

| id | name | email | age | city |
| --- | --- | --- | --- | --- |
| 1 | Alice | alice@email.com | 25 | Seattle |
| 2 | Bob | bob@email.com | 30 | Portland |
| 3 | Charlie | charlie@email.com | 22 | Seattle |

### Example 2: Select Specific Columns

**Difficulty:** Beginner

**Scenario:** Get just the names and emails of all users

```sql
SELECT name, email FROM users;
```

**Explanation:** Specify column names to retrieve only the data you need.

**Expected Output:**

| name | email |
| --- | --- |
| Alice | alice@email.com |
| Bob | bob@email.com |

## Common Mistakes

### Mistake 1: Forgetting the FROM clause

**Incorrect SQL:**
```sql
SELECT * WHERE age > 25;
```

**Error Message:** `Error: near 'WHERE': syntax error`

**Why it happens:** The FROM clause is required to specify which table to query. Without it, SQL doesn't know where to look for the 'age' column.

**Corrected SQL:**
```sql
SELECT * FROM users WHERE age > 25;
```

💡 **Key Takeaway:** Always include FROM table_name after SELECT

### Mistake 2: Selecting all columns unnecessarily

**Incorrect SQL:**
```sql
SELECT * FROM users;
```

**Error Message:** `No error, but inefficient`

**Why it happens:** Using * retrieves all columns, which can be slow with large tables and unnecessary data transfer.

**Corrected SQL:**
```sql
SELECT id, name, email FROM users;
```

💡 **Key Takeaway:** Specify only the columns you need

## Practice Challenge

**Write a query to find all users from 'Seattle' who are older than 25.**

💡 **Hint:** Use WHERE with AND to combine conditions.

<details>
<summary>Click to see solution</summary>

```sql
SELECT * FROM users WHERE city = 'Seattle' AND age > 25;
```

**Explanation:** This query filters for users where both conditions are true: city is 'Seattle' AND age is greater than 25.
</details>

## Related Practice Problems

- [problem-1](/practice/problem-1)

---

*Content generated for SQL-Adapt Learning Platform*
