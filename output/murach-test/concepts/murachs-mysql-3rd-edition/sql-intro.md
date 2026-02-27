# Introduction to SQL

## Definition

You use the AND operator to specify that the 
search must satisfy both of the conditions, and you use the OR operator to specify 
that the search must satisfy at least one of the conditions.

## Explanation

How to retrieve datafrom a single table 
The syntax of the WHERE clause with logical operators 
WHERE [NOT] search_condition_ l 
{ANDIOR} [NOT] search_ condition_ 2 
Examples of WHERE clauses that use logical operators 
The AND operator 
WHERE vendor_state = 'NJ' AND vendor_city = 'Springfield' 
The OR operator 
WHERE vendor_state = 'NJ' OR vendor_city = 'Pittsburg' 
The NOT operator 
WHERE NOT vendor_state = 'CA' 
The NOT operator in a complex search condition 
• • • 
WHERE NOT {invoice_ total >= 5000 OR NOT invoice_date <= '2018-08-01') 
The same condition rephrased to eliminate the NOT operator 
WHERE invoice_ total < 5000 AND invoice_date <= '2018-08-01' 
A compound condition without parentheses 
WHERE invoice_date > '2018-07-03' OR invoice_total > 500 
AND invoice_ total -
payment_total - credit_ total > O 
invoice_number 
invoice_date 
invoice_total 
balance_due 
► 
203339-13 
2018-07-05 
17.50 
0.00 
111-92R-10093 
2018-07-06 
39.n 
0,00 
2018-07-06 
111.00 
0.00 
{33 rows ) 
The same compound condition with parentheses 
WHERE (invoice_date > '2018-07-03' OR invoice_ total > 500) 
AND invoice_ total - payment_total - credit_total > 0 
~ 
invoice-:..number 
invoice_date 
invoice_total 
balance_due 
2018~7-10 
85.31 
85.31 
► 
2018-07-18 
52.25 
52.25 
2018-07-21 
579.42 
579.42 
{11 rows) 
Description 
• 
You can use the AND and OR logical operators to create compound conditions that 
consist of two or more conditions.

You use the AND operator to specify that the 
search must satisfy both of the conditions, and you use the OR operator to specify 
that the search must satisfy at least one of the conditions. • 
You can use the NOT operator to negate a condition. Because this can make the 
search condition unclear, you should rephrase the condition if possible so it doesn't 
use NOT. • 
When MySQL evaluates a compound condition, it evaluates the operators in this 
sequence: (1) NOT, (2) AND, and (3) OR.

You can use parentheses to override this 
order of precedence or to clarify the sequence in which the operations are evaluated. How to use the AND, OR, and NOT logical operators

An introduction to MySQL 
How to use the IN operator 
When you use this operator, the value of the test expression is compared with the 
list of expressions in the IN phrase. If the test expression is equal to one of the 
expressions in the list, the row is included in the query results.

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

**Question:** Practice using Introduction to SQL in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
