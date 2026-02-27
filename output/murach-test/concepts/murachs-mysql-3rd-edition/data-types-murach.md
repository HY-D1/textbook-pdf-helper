# MySQL Data Types

## Definition

That makes sense because the WHERE clause is applied 
before the rows are grouped, and the ORDER BY clause is applied after the rows 
are grouped.

## Explanation

How to code sum1n.ary queries 
A summary query that uses the COUNT(*), AVG, and SUM functions 
SELECT 'After 1/1/2018' AS selection_date, 
COUNT(*) AS number_of_ invoices, 
ROUND{AVG{invoice_total), 2) AS avg_ invoice_amt, 
SUM{invoice_total) AS total_ invoice_amt 
FROM invoices 
WHERE invoice_date > '2018-01-01' 
selection_date 
number _of _lnvOJces 
avg_ilvoice_amt 
total_invoice_amt 
► 
After 1/1/2018 
1879.74 
214290.51 
A summary query that uses the MIN and MAX functions 
COUNT { *) AS n11mh~r_of_ invoices, 
MAX{invoice_total) AS highest_ invoice_ total, 
MIN(invoice_total) AS lowest_ invoice_total 
WHERE invoice date> '2018-01-01' 
seJection_date 
number _of Jnvoices 
highest_invoice_total 
lowest_invoice_total 
37966.19 
6.00 
A summary query that works on non-numeric columns 
SELECT MIN{vendor_name) AS first_vendor, 
MAX{vendor_name) AS last_vendor, 
COUNT(vendor_name) AS number_of_vendors 
FROM vendors 
I flrst_vendor 
► I Abbey Office Furnishings 
last_vendor 
Zylka Design 
number _of _vendors 
A summary query that uses the DISTINCT keyword 
SELECT COUNT(DISTINCT vendor_ id) AS number_of_vendors, 
COUNT{vendor_ id) AS number_of_ invoices, 
ROUND(AVG(invoice_ total), 2) AS avg_ invoice_amt, 
SUM(invoice_total) AS total_ invoice_ amt 
number _of_vendors 
number _of_involces 
avg_invoic:e_amt 
Description 
• 
To cot1nt all of the selected 1·ows, you typically use the COUNT(*) function.

Alternately, you can use the COUNT function with the name of any column that 
can't contain null values. To cot1nt only the rows with unique values in a specified column, you can code 
the COUNT function with the DISTINCT keyword followed by the name of the 
column. Queries that use aggregate functions

17 4 
More SQL skills cts you need them 
How to group and summarize data 
Now that you understand how aggregate functions work, you're ready to 
learn how to group data and use aggregate functions to summarize the data in 
each group.

To do that, you can use two new clauses of the SELECT statement: 
GROUP BY and HAVING. How to code the GROUP BY and HAVING clauses 
and HAVING clauses. The GROUP BY clause determines how the selected rows 
are grouped, and the HAVING clause determines which groups are included in 
the final results. These clauses are coded after the WHERE clause but before the 
ORDER BY clause. That makes sense because the WHERE clause is applied 
before the rows are grouped, and the ORDER BY clause is applied after the rows 
are grouped.

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

**Question:** Practice using MySQL Data Types in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
