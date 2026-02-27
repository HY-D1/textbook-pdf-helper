# HAVING Clause

## Definition

• 
You specify the conditions that must be met for a row to be deleted in the WHERE 
clause.

## Explanation

The syntax of the DELETE statement 
DELETE FROM table_name 
[WHERE search_ condition] 
Delete one row 
DELETE FROM general_ledger_accounts 
WHERE account_ number = 306 
(1 row affected) 
Clzapter 5 
How to insert, update, and delete data 
Delete one row using a compound condition 
DELETE FROM invoice_ line_items 
WHERE invoice id= 78 AND invoice_ sequence = 2 
(1 row affected) 
Delete multiple rows 
DELETE FROM invoice_line_ items 
WHERE invoice id= 12 
(4 rows affected) 
Use a subquery in a DELETE statement 
WHERE invoice_ id IN 
(SELECT invoice_ id 
FROM invoices 
WHERE vendor id= 115) 
(4 rows affected) 
Description 
• 
You can use the DELETE statement to delete one or more rows from the table you 
name in the DELETE clause.

• 
You specify the conditions that must be met for a row to be deleted in the WHERE 
clause. • 
You can use a subquery within the WHERE clause. • 
A foreign key constraint may prevent you from deleting a row. In that case, you can 
only delete the row if you delete all child rows for that row first. • 
By default, MySQL Workbench runs in safe update mode. That prevents you from 
deleting rows if the WHERE clause is omitted or doesn't refer to a primary key or 
foreign key column.

For information on turning safe update mode off, see figure 
5-5. Warning 
• 
If you tum safe update mode off and omit th.e WHERE clause from a DELETE 
statement, all the rows in the table will be deleted. How to delete rows

An introduction to MySQL 
Perspective 
In this chapter, you learned how to use the INSERT, UPDATE, and 
DELETE statements to modify the data in a database. In chapters 10 and 11, 
you'll learn more about how table definitions can affect the way these state-
ments work.

## Examples

### Example

```sql
-- See textbook for complete examples
```

Code examples available in the source material

## Common Mistakes

### Not understanding the concept fully

**Incorrect:**

```sql
-- Incorrect usage
```

**Correct:**

```sql
-- Correct usage (see textbook)
```

**Why this happens:** Review the textbook explanation carefully

---

## Practice

**Question:** Practice using HAVING Clause in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
