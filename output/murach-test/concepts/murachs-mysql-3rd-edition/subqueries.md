# Subqueries

## Definition

To include two or more columns or expressions, separate them by commas.

## Explanation

How to code sum1ncary queries 
The syntax of a SELECT statement with GROUP BY and HAVING clauses 
SELECT select_list 
FROM table_ source 
[WHERE search_ condition] 
[GROUP BY group_by_ list] 
[HAVING search_condition] 
[ORDER BY order_by_ list] 
A summary query that calculates the average invoice amount by vendor 
SELECT vendor_ id, ROUND(AVG(invoice_total), 2) AS average_ invoice_amount 
FROM invoices 
GROUP BY vendor_ id 
HAVING AVG(invoice_total) > 2000 
ORDER BY average_ invoice_amount DESC 
vendor id 
average_lnvoice_amount 
► 
23978.48 
10963.66 
7125.34 
6940.25 
4901.26 
2575.33 
2433.00 
2184.50 
(8 rows) 
A summary query that includes a functionally dependent column 
SELECT vendor_ name, ~endor_ state, 
ROUND(AVG(invoice_total), 2) AS average_ invoice_amount 
FROM vendors JOIN invoices ON vendors.vendor_ id = invoices.vendor_ id 
GROUP BY vendor_narn~ 
HAVING AVG(invoice total) > 2000 
Description 
• 
The GROUP BY clause groups the rows of a result set based on one or more columns or 
expressions.

To include two or more columns or expressions, separate them by commas. • If you include aggregate functions in the SELECT clause, the aggregate is calculated for 
each group specified by the GROUP BY clause. • If you include two or more colu1nns or expressions in the GROUP BY clause, they form 
a hierarchy where each column or expression is subordinate to the previous one. • 
The HAVING clause specifies a search condition for a group or an aggregate.

MySQL 
applies this condition after it groups the rows that satisfy the search condition in the 
WHERE clause. • 
When a SELECT statement includes a GROUP BY clause, the SELECT clause can 
include the columns used for grouping, aggregate functions, and expressions that 
result in a constant value. • 
The SELECT clause can also include columns that are functionally dependent on a 
column used fo1· grouping.

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

**Question:** Practice using Subqueries in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
