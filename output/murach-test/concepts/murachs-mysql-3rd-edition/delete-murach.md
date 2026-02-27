# DELETE Statement

## Definition

• 
To insert rows selected from one or more tables into another table, you can code a 
subquery in place of the VALUES clause.

## Explanation

Clzapter 5 
How to insert, update, and delete data 
The syntax for using a subquery to insert one or more rows 
INSERT [INTO] table_ name [(column_ list)] select_statement 
Insert paid invoices into the lnvoice_Archive table 
INSERT INTO invoice_archive 
SELECT* 
FROM invoices 
WHERE invoice_ total - payment_total - credit_total = 0 
(103 rows affected) 
The same statement with a column list 
INSERT INTO invoice archive 
(invoice_id, vendor_ id, invoice_number, invoice_total, credit_ total, 
payment_total, terms_id, invoice_date, invoice_due_date) 
SELECT 
invoice_ id, vendor_ id, invoice_number, invoice_ total, credit_ total, 
payment_total, terms_ id, invoice_date, invoice_due_date 
FROM invoices 
WHERE invoice total - payment_total - credit_total = 0 
(103 rows affected) 
Description 
• 
A subquery is a SELECT statement that's coded within another SQL statement.

• 
To insert rows selected from one or more tables into another table, you can code a 
subquery in place of the VALUES clause. Then, MySQL inserts the rows returned 
by the subquery into the target table. For this to work, the target table must already 
. exist. • 
The rules for working with a column list are the same as they are for any INSERT 
statement. How to use a subquery in an INSERT statement

An introduction to MySQL 
How to update existing rows 
To modify the data in one or 1nore rows of a table, you use the UPDATE 
statement.

Although most of the UPDATE statements you code will perform 
simple updates, you can also code more complex UPDATE statements that 
include subqueries if necessary. How to update rows 
statements include all three of the clauses shown here. The UPDATE clause 
names the table to be updated. The SET clause names the columns to be updated 
and the values to be assigned to those columns. And the WHERE clause speci-
fies the condition a row must meet to be updated.

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

**Question:** Practice using DELETE Statement in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
