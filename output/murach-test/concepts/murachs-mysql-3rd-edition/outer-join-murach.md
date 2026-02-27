# Outer Join

## Definition

• 
If you code a single argument, it specifies the maximum row count, beginning with 
the first row.

## Explanation

How to retrieve data from a sin.gle table 
The expanded syntax of the LIMIT clause 
LIMIT [offset,] row_count 
A SELECT statement with a LIMIT clause that starts with the first row 
SELECT vendor_ id, invoice_ total 
FROM invoices 
ORDER BY invoice_total DESC 
LIMIT 5 
vendorjd 
invoice_ total 
► 
37966.19 
26881 .40 
23517.58 
21842.00 
20551. 18 
SELECT invoice_ id, vendor_ id, invoice_ total 
FROM invoices 
ORDER BY invoice_ id 
LIMIT 2, 3 
invoice id -
vendor_id 
invoice total 
► 
138.75 
144.70 
15.50 
SELECT invoice_ id, vendor_ id, invoice_total 
FROM invoices 
ORDER BY invoice id 
LIMIT 100, 1000 
invoice id -
vendor_id 
invoice_total 
► 
30.75 
20551.18 
2051.59 
44.44 
(14 rows ) 
Description 
• 
You can use the LIMIT clause to limit the number of rows returned by the SELECT 
statement.

This clause takes one or two intege1· arguments. • 
If you code a single argument, it specifies the maximum row count, beginning with 
the first row. If you code both arguments, the offset specifies the first row to return, 
where the offset of the first row is 0. • If you want to retrieve all of the rows from a certain offset to the end of the result 
set, code -1 for the row count. • 
Typically, you'll use an ORDER BY clause whenever you use the LIMIT clause.

How to code the LIMIT clause 
'

An introduction to MySQL 
Perspective 
The goal of this chapter has been to teach you the basic skills for coding 
SELECT statements. As a result, you'll use these skills in almost every 
SELECT statement you code. As you'll see in the next chapter and in chapters 6 and 7, though, there's 
a lot more to coding SELECT statements than what's presented here. In these 
chapters, then, you'll learn additional skills for coding SELECT statements.

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

**Question:** Practice using Outer Join in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
