# ORDER BY Clause

## Definition

20 
0.00 
2018-04-13 
138.75 
0.00 
2-000-2993 
2018-04-16 
144.70 
0.00 
2018-04-16 
15.50 
0.00 
2018-04-16 
42.

## Explanation

How to retrieve datafrom a single table 
A SELECT statement that renames the columns in the result set 
SELECT invoice_number AS "Invoice Number", invoice_date AS Date, 
invoice total AS Total 
FROM invoices 
Invoice Number 
Date 
Total 
► 
989319-457 
2018-04-08 
3813.33 
2018-04-10 
-10.20 
2018-04-13 
138. 75 
2-000-2993 
2018-04-16 
144. 70 
2018-04-16 
15.50 
2018-04-16 
42.75 
(114 rows) 
A SELECT statement that doesn't name a calculated column 
SELECT invoice_number, invoice_date, invoice_total, 
invoice_total - payment_total - credit_total 
FROM invoices 
~ 
invoice_number 
invoice date 
invoice total 
invoice_tot.al - payment_total - credit_tot.al 
2018-04-08 
3813, 33 
0.00 
► 
989319-457 
2018-04-10 
"10.

20 
0.00 
2018-04-13 
138.75 
0.00 
2-000-2993 
2018-04-16 
144.70 
0.00 
2018-04-16 
15.50 
0.00 
2018-04-16 
42. 75 
0.00 
(114 rows) 
Description 
• 
By default, a column in the result set is given the same name as the column in 
the base table. If that's not what you want, you can specify a substitute name, or 
column alias, for the column. • 
To specify an alias for a column, use the AS phrase.

Although the AS keyword is 
optional, I recommend you code it for readability. • 
If you don't specify an alias for a column that's based on a calculated value, 
MySQL uses the expression for the calculated value as the column name. • 
To include spaces or special characters in an alias, enclose the alias in double 
quotes ( " ) or single quotes ( ' ). How to name the columns in a result set using aliases 
V 
An introduction to MySQL 
How to code arithmetic expressions 
the arithmetic operators you can use in this type of expression.

## Examples

### SQL Example 1

```sql
with literal values. The third example uses another function, CURRENT_DATE, to supply a date value in place of the invoice_date column that's coded in figure 3-7. Four SELECT statements without FROM clauses Example 1 : Testing a calculation SELECT 1000 * (1 + .1) AS 1110% More Than 1000" 10°/4 More Than 1000 ---I -- ► 1100.0 "'-~------;
```

Example SQL query

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

**Question:** Practice using ORDER BY Clause in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
