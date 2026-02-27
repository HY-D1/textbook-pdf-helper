# Joining Tables

## Definition

Each of the expressions in the list is automatically converted to the 
same type of data as the test expression.

## Explanation

How to retrieve data from a sin.gle table 
The syntax of the WHERE clause with an IN phrase 
WHERE test_expression [NOT] IN 
({subquerylexpression_ l [, expression_2 ] ... }) 
Examples of the IN phrase 
An IN phrase with a list of numeric literals 
WHERE terms_ id IN (1, 3, 4) 
An IN phrase preceded by NOT 
WHERE vendor_ state NOT IN ('CA', 'NV', 'OR') 
An IN phrase with a subquery 
WHERE vendor id IN 
(SELECT vendor id 
FROM invoices 
WHERE invoice_date = 
1 2018-07-18 1
) 
Description 
• 
You can use the IN phrase to test whether an expression is equal to a value in a list 
of expressions.

Each of the expressions in the list is automatically converted to the 
same type of data as the test expression. • 
The list of expressions can be coded in any order without affecting the order of the 
rows in the result set. • 
You can use the NOT operator to test for an expression that's not in the list of 
• 
expressions. • 
You can also compare the test expression to the items in a list returned by a 
subquery.

You'll learn more about coding subqueries in chapter 7. How to use the IN operator

An introduction to MySQL 
How to use the BETWEEN operator 
When you use this operator, the value of a test expression is compared to the 
range of values specified in the BETWEEN phrase. If the value falls within this 
range, the row is included in the query results. The first example in this figure shows a simple WHERE clause that uses the 
BETWEEN operator.

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

**Question:** Practice using Joining Tables in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
