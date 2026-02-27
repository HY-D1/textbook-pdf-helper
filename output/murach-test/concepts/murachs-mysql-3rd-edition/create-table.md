# CREATE TABLE

## Definition

In most cases, that means that it uses an aggregate 
function.

## Explanation

How to l·ode subqueries 
The syntax of a WHERE clause that uses an IN phrase 
WHERE test_expression [NOT] IN (subquery) 
Get vendors without invoices 
SELECT vendor_ id, vendor_name, vendor_state 
FROM vendors 
WHERE vendor_ id NOT IN 
(SELECT DISTINCT vendor_ id 
FROM invoic es ) 
ORDER BY vendor id 
The result of the subquery 
vendor_id 
► 
'18 
(34 rows) 
The result set 
vendor jd 
vendor _name 
Nielson 
Cal State Termite 
Graylift 
Venture Communications Int'I 
Custom Printing Company 
I 
tlO 
Nat Assoc of College Stores 
(88 rows) 
vendor _state 
OH 
CA 
CA 
NY 
MO 
OH 
The query restated without a subquery 
SELECT v .vendor_ id, vendor_ name, vendor_ state 
FROM vendors v LEFT JOIN invoices i 
ON v .

vendor_ id = i .vendor_ id 
WHERE i.vendor_ id IS NULL 
ORDER BY v .vendor_ id 
Description 
• 
You can introduce a subquery with the IN operator to provide the list of values that 
are tested against the test expression. • 
When you use the IN operator, the subquery must return a single column of values. • 
A query that uses the NOT IN operator with a subquery can typically be restated 
using an outer join.

How to use the IN operator

More SQL skills cts you need them 
How to use the comparison operators 
expression with the result of a subquery. In this example, the subquery returns 
the average balance due of the invoices in the Invoices table that have a balance 
due greater than zero. Then, it uses that value to retrieve all invoices with a 
balance due that's less than the average. When you use a compaiison operator as shown in this figure, the subquery 
must return a single value.

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

**Question:** Practice using CREATE TABLE in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
