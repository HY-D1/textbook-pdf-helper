# Integrity Constraints

## Definition

• 
You can use the NOT EXISTS operator to test that no rows are returned by the 
subquery.

## Explanation

How to l·ode subqueries 
The syntax of a subquery that uses the EXISTS operator 
WHERE [NOT] EXISTS (subquery) 
Get all vendors that don't have invoices 
SELECT vendor id, vendor_ name, vendor_state 
FROM vendors 
WHERE NOT EXISTS 
(SELECT* 
FROM invoices 
WHERE vendor_ id = vendors.vendor_ id) 
The result set 
vendor jd 
vendor _name 
-33 
39 I 
'10 
(88 rows ) 
Description 
Nielson 
Cal State Termite 
Grayfift 
Venture Communications Int'I 
Custom Printing Company 
Nat Assoc of CoUege Stores 
vendor _state 
OH 
CA 
CA 
NY 
MO 
OH 
• 
You can use the EXISTS operator to test that one or more rows are returned by the 
subquery.

• 
You can use the NOT EXISTS operator to test that no rows are returned by the 
subquery. • 
When you use these operators with a subquery, it doesn't matter what columns you 
specify in the SELECT clause. As a result, you typically just code an asterisk ( * ). How to use the EXISTS operator 
More SQL skills cts you need them 
How to code subqueries 
in other clauses 
Now that you know how to code subqueries in the WHERE clause of a 
SELECT statement, you're ready to learn how to code them in the HAVING, 
FROM, and SELECT clauses.

How to code subqueries in the HAVING clause 
When you code a HA YING clause, you specify a search condition just as 
you do when you code a WHERE clause. That includes search conditions that 
contain subqueries. To learn how to code subqueries in a HAVING clause, then, 
you can refer back to figures 7-3 through 7-8. How to code subqueries in the SELECT clause 
that, you code the subquery in place of a column specification.

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

**Question:** Practice using Integrity Constraints in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
