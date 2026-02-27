# Relational Databases

## Definition

See textbook for details.

## Explanation

See textbook for details.

## Common Mistakes

### Using 'SELECT *' without specifying conditions can lead to performance issues, especially with large tables.

**Incorrect:**

```sql
-- Wrong approach
```

**Correct:**

```sql
-- Fixed approach
```

**Why this happens:** Always specify necessary columns instead of using '*'.

### Forgetting to use a WHERE clause in an UPDATE statement can result in unintended data changes across the entire table.

**Incorrect:**

```sql
-- Wrong approach
```

**Correct:**

```sql
-- Fixed approach
```

**Why this happens:** Always include a WHERE clause to target specific records.

### Using incorrect column names or table aliases can lead to errors in SQL queries.

**Incorrect:**

```sql
-- Wrong approach
```

**Correct:**

```sql
-- Fixed approach
```

**Why this happens:** Double-check column and table names for accuracy, especially when using aliases.

---
