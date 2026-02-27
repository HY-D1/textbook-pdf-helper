# Stored Functions

## Definition

• 
To delete a view from the database, use the DROP VIEW statement.

## Explanation

A statement that creates a view 
CREATE VIEW vendors_ sw AS 
SELECT* 
FROM vendors 
WHERE vendor state IN ( 'CA' 'AZ' 'NV' 'NM') 
, 
, 
, 
How to create views 
A statement that replaces the view with a new view 
CREATE OR REPLACE VIEW vendors_ sw AS 
SELECT* 
FROM vendors 
WHERE vendor_state IN ('CA','AZ','NV','NM','UT', 'CO') 
A statement that drops the view 
DROP VIEW vendors_ sw 
Description 
• 
To alter a view, use the CREATE OR REPLACE VIEW statement to replace the 
existing view with a new one.

• 
To delete a view from the database, use the DROP VIEW statement. How to alter or drop a view

Database design and impleme11,tation, 
Perspective 
In this chapter, you learned how to create and use views. As you've seen, 
views provide a powerful and flexible way to predefine the data that can be 
retrieved from a database. By using them, you can restJ.ict the access to a 
database while providing a consistent and simplified way for end t1sers and 
application programs to access that data.

Terms 
• 
view 
nested view 
updatable view 
read-only view 
base table 
viewed table 
Exercises 
1. Create a view named open_items that shows the invoices that haven't been 
paid. This view should return four columns from the Vendors and Invoices tables: 
vendor_name, invoice_number, invoice_total, and balance_due 
(invoice_total - payment_total - credit_total). A row should only be returned when the balance due is greater than zero, and 
the rows should be in sequence by vendor_name.

## Examples

### SQL Example 1

```sql
with the USE statement, which selects the AP database. Then, the DROP PROCEDURE IF EXISTS command drops the procedure named test if it already exists. This suppresses any error messages that would be displayed if you attempted to drop a procedure that didn't exist. The DELIMITER statement changes the delimiter from the default delimiter of the semicolon(;
```

Example SQL query

### SQL Example 2

```sql
CREATE PROCEDURE statement, and it allows you to use two front slashes(//) to identify the end of the CREATE PROCEDURE state- ment. Although we use two front slashes as the delimiter in this book, it's also common to see two dollar signs ($$) or two semicolons (;
```

Example SQL query

### SQL Example 3

```sql
DELETE state- ment on a specified table. ls executed at a scbeduJed time. USE ap;
```

Example SQL query

### SQL Example 4

```sql
DROP PROCEDURE IF EXISTS test;
```

Example SQL query

### SQL Example 5

```sql
CREATE PROCEDURE test() BEGIN DECLARE sum_balance_ due_var DECIMAL (9, 2);
```

Example SQL query

### SQL Example 6

```sql
SELECT SUM(invoice_total - payment_total - credit_total ) INTO sum_balance_ due_var FROM invoices WHERE vendor_id = 95;
```

Example SQL query

### SQL Example 7

```sql
SELECT CONCAT('Balance due: $', sum_balance_due_var) AS message;
```

Example SQL query

### SQL Example 8

```sql
SELECT 'Balance paid in full' AS message;
```

Example SQL query

### SQL Example 9

```sql
SELECT statement to return a result set that indicates the balance that is due. Otherwise, the statement in the ELSE clause uses a SELECT statement to return a result set that indicates that the balance is paid in full. After the stored procedure has been created, this script uses the DELIMTER state1nent to change the delimiter back to the default deli1niter of a se1nicolon (;
```

Example SQL query

### SQL Example 10

```sql
CREATE PROCEDURE statement that are necessary to create the stored procedure. Before you execute these statements, you may need to select the appropriate database and drop any procedures with the same name as shown in figure 13-1. Sitnilarly, after you execute these statements, the stored procedure isn't executed until you call it as shown in figure 13-1. A stored procedure that displays a message DELIMITER// CREATE PROCEDURE test() BEGIN SELECT 'This is a test.' AS message;
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

**Question:** Practice using Stored Functions in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
