# Stored Procedures

## Definition

How to create views 
As you've seen throughout this book, SELECT queries can be complicated, 
particularly if they use multiple joins, subqueries, or complex functions.

## Explanation

How to create views 
As you've seen throughout this book, SELECT queries can be complicated, 
particularly if they use multiple joins, subqueries, or complex functions. Because of that, you may want to save the queries you use regularly. One way 
to do that is to store the statement in a script. Another way is to create a view. Unlike scripts, which are stored in files, views are stored as part of the 
database.

As a result, they can be used by SQL programmers and by custom 
applications that have access to the database. This provides some advantages 
over using tables directly. An introduction to views .................................................... 382 
How views work ........................................................................................... 382 
Benefits of using views .................................................................................

384 
How to work with views ..................................................... 386 
How to c·reate a view .................................................................................... 386 
How to create an updatable view ................................................................. 390 
How to use the WITH CHECK OPTION clause ........................................ 392 
How to insert or delete rows through a view ...............................................

## Examples

### SQL Example 1

```sql
WITH CHECK OPTION clause CREATE OR REPLACE VIEW vendor_payment AS SELECT vendor_name, invoice_ number, invoice_date, payment_date, invoice_ total, credit_total, payment_total WHERE invoice_total - payment_total - credit_total >= 0 WITH CHECK OPTION A SELECT statement that displays a row from the view SELECT* FROM vendor_payment WHERE invoice_ DtJmh~r = 'P-0608' The result set vendor _name ► MaDoy Lithographing Inc invoice _number P-0608 invoice date payment_date 2018-0 7 _23;
```

Example SQL query

### SQL Example 2

```sql
UPDATE statement that updates the view UPDATE vendor_payment SET payment_total = 400.00, payment_date = '2018-08-01' WHERE invoice_ numher = 'P-0608' The response from the system (1 row affected) The same row data after the update credit_total 1200.00 payment_total 0.00 invoice_number invoice_date 2018-07-23 2018-08-01 1200. 00 .WO. 00 An UPDATE statement that attempts to update the view SET payment_ total = 30000.00, WHERE invoice_number = 'P-0608';
```

Example SQL query

### SQL Example 3

```sql
delete or update a parent row: a foreign key constraint fails ('ap'.'invoice_line_items', CONSTRAINT 'line_ items_fk_invoices' FOREIGN KEY ( 'invoice_id' ) REFERENCES 'invoices' { ' invoice id• ) ) Two DELETE statements that succeed DELETE FROM invoice_ line_ items WHERE invoice_ id = (SELECT invoice_ id FROM WHERE invoice number= DELETE FROM ihm invoices WHERE invoice_n11mher = • QS45443';
```

Example SQL query

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

**Question:** Practice using Stored Procedures in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
