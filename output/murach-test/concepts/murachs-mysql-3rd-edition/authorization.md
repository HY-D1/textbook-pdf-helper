# SQL Authorization

## Definition

That means that 
you can code views that join tables, summarize data, and use subqueries and 
functions.

## Explanation

How to create views 
Some of the benefits provided by views 
Benefit 
Description 
Design independence 
Data security 
Simplified queries 
Updatability 
Description 
Views can limit the exposure of tables to external users and applications. As a result, if the design of the tables changes, yo1.1 can modify the view 
as necessary so t1sers who query the view don't need to be aware of the 
change, and applications that use the view don't need to be modified.

Views can restrict access to the data in a table by using the SELECT 
clat1se to include only selected columns of a table or by using the 
WHERE clause to include 011ly selected rows in a table. Views can be used to hide the complexity of retrieval operations. Then, 
the data can be retrieved using simple SELECT statements that specify a 
view in the FROM clause. With certain restrictions, views can be used to update, insert, and delete 
data fron1 a base table.

• 
You can create a view based on almost any SELECT statement. That means that 
you can code views that join tables, summarize data, and use subqueries and 
functions. Benefits of using views

Database design and impleme11,tation, 
How to work with views 
Now that you have a general understanding of how views work and of the 
benefits that they provide, you 're ready to learn the details for working with 
them.

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

**Question:** Practice using SQL Authorization in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
