# Aggregate Functions

## Definition

• 
This query uses comments to clearly identify its three queries.

## Explanation

How to l·ode subqueries 
A complex query that uses three subqueries 
SELECT tl.vendor_ state, vendor_name, tl.sum of invoices 
FROM 
( 
) tl 
-- invoice totals by vendor 
SELECT vendor_ state, vendor_name, 
SUM(invoice_total) AS sum_of_ invoices 
FROM vendors v JOIN invoices i 
ON v.vendor_ id = i.vendor_ id 
GROUP BY vendor_ state, vendor_ name 
JOIN 
( 
-- top invoice totals by state 
SELECT vendor_ state, 
MAX(sum_of_ invoices) AS sum_of_ invoices 
FROM 
( 
) t2 
-- invoice totals by vendor 
FROM vendors v JOIN invoices i 
ON v.vendor id= i.vendor id 
GROUP BY vendor_ state, vendor_name 
GROUP BY vendor_state 
) t3 
ON tl.vendor_ state = t3.vendor_ state AND 
tl.sum of invoices= t3.sum of invoices 
ORDER BY vendor_ state 
The result set 
I vendor _state 
► 
AZ 
CA 
I~ 
(10 rows) 
Description 
vendor _name 
\ft/eDs Fargo Bank 
Digital Dreamworks 
Reiter's Scientific &.Pro Books 
Dean \!'Jitter Reynolds 
sum_of _invoices 
662.00 
7125.34 
600.00 
1367.50 
• 
This query retrieves the vendor from each state that has the largest invoice total.

To 
do that, it uses three subqueries. • 
This query uses comments to clearly identify its three queries. • 
The subqueries named tl and t2 return the same result set. This result set includes 
the vendor state, name, and sum of invoices. • 
The subquery named t3 returns a result set that includes the vendor state and the 
largest sum of invoices for any vendor in that state. To do that, this subquery uses a 
nested subquery named t2.

• 
The subqueries named tl and t3 are joined on both the vendor_state and st1m_of_invoices 
columns. A complex query that uses subqueries

More SQL skills cts you need them 
A procedure for building complex queries 
To build a complex query like the one in the previous figure, you can use a 
procedure like the one in figure 7-12. To sta1t, you should state the question in 
English so you're clear about what you want the query to answer.

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

**Question:** Practice using Aggregate Functions in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
