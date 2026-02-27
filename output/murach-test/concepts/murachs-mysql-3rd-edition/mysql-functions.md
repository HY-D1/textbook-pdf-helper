# MySQL Functions

## Definition

How to code sum1ncary queries 
The sum of the line item amount columns in the Invoice Line Items table 
that have the same account_nu1nber 
Return only those rows where the count of line items is greater than 1.

## Explanation

How to code sum1ncary queries 
The sum of the line item amount columns in the Invoice Line Items table 
that have the same account_nu1nber 
Return only those rows where the count of line items is greater than 1. This 
sl1ould return 10 rows. Group the result set by the account_description column. Sort the resL1lt set in descending sequence by the sum of the line item 
a1nounts. 5. Modify the solution to exercise 4 so it returns only invoices dated in the 
second quarter of 2018 (April 1, 2018 to June 30, 2018).

This should still 
return 10 rows but with some different line item counts for each vendor. Hint: 
Join to tlie Invoices table to code a secirch condition based on invoice_date. 6. Write a SELECT statement that answers this question: What is the total 
amount invoiced for each general ledger account nt1mber? Return these 
columns: 
The account number column fro1n the Invoice Line Items table 
The sum of the line_item_amount columns from the Invoice_Line_Items 
table 
Use the WITH ROLLUP operator to include a row that gives the grand total.

This should return 22 rows. 7. being paid from more than one account? Return these columns: 
The vendor name colL1mn from the Vendors table 
The count of distinct general ledger accounts that apply to that vendor's 
• 
• 
1nvo1ces 
This should return 2 rows.

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

**Question:** Practice using MySQL Functions in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
