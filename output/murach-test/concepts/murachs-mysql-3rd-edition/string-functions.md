# String Functions

## Definition

Write a SELECT statement that uses aggregate window functions to calculate 
the total due for all vendors and the total due for each vendor.

## Explanation

More SQL skills cts you need them 
9. Write a SELECT statement that uses aggregate window functions to calculate 
the total due for all vendors and the total due for each vendor. Return these 
columns: 
The vendor id from the Invoices table 
The balance due (invoice_total - payment_total - credit_total) for each 
invoice in the Invoices table with a balance due greater than 0 
The total balance due for all vendors in the Invoices table 
The total balance due for each vendor in the Invoices table 
Modify the column that contains the balance due £01· each vendor so it 
contains a cumulative total by balance due.

This should return 11 rows. average balance due for each vendor in the Invoices table. This column should 
contain a cumulative average by balance due. Modify the SELECT statement so it uses a named window for the last two 
aggregate window functions. late a moving average of the sum of invoice totals. Return these columns: 
The month of the invoice date from the Invoices table 
The sum of the invoice totals from the Invoices table 
The moving average of the invoice totals sorted by invoice month 
The result set should be grouped by invoice month and the frame for the 
moving average should include the current row plus tlu·ee rows before the 
current row.

How to code subqueries 
Subqueries allow you to build queries that would be difficult or impossible 
to build otherwise. In chapter 5, you learned how to use them in INSERT, 
UPDATE, and DELETE statements. In this chapter, you'll learn how to use 
subqueries in SELECT statements. An introduction to subqueries .......................................... 200 
Where to code subqueries ...........................................................................

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

**Question:** Practice using String Functions in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
