# Cardinality Constraints

## Definition

To start, this figure shows some of the columns and rows of the 
Invoices table.

## Explanation

Cl1apter 1 
An introduction to relational databases 
A statement that creates a new database 
CREATE DATABASE ap 
A statement that selects the current database 
USE ap 
A statement that creates a new table 
CREATE TABLE invoices 
( 
) 
invoice_ id 
vendor_ id 
invoice_nwnber 
invoice date 
invoice_ total 
payment_ total 
credit_total 
terms_ id 
INT 
INT 
VARCHAR ( 5 0) 
DATE 
DECIMAL(9,2) 
DECIMAL(9,2) 
DECIMAL(9,2) 
INT 
invoice_due_date 
DATE 
payment_date 
DATE, 
CONSTRAINT invoices_ fk_vendors 
FOREIGN KEY (vendor id) 
REFERENCES vendors (vendor_id), 
CONSTRAINT invoices_ fk_terms 
FOREIGN KEY (terms_ id) 
REFERENCES terms (terms id) 
PRIMARY KEY 
NOT NULL, 
NOT NULL, 
NOT NULL, 
NOT NULL, 
NOT NULL, 
NOT NULL, 
A statement that adds a new column to a table 
ALTER TABLE invoices 
ADD balance_due DECIMAL(9,2) 
A statement that deletes the new column 
ALTER TABLE invoices 
DROP COLUMN balance_due 
A statement that creates an index on the table 
CREATE INDEX invoices_vendor_ id_ index 
ON invoices (vendor_ id) 
A statement that deletes the new index 
DROP INDEX invoices_vendor_ id_ index 
ON invoices 
Typical statements for working with database objects 
AUTO_ INCREMENT, 
DEFAULT 0, 
DEFAULT 0,

An introduction to MySQL 
How to query a single table 
in a database.

To start, this figure shows some of the columns and rows of the 
Invoices table. Then, in the SELECT statement that follows, the SELECT clause 
names the columns to be retrieved, and the FROM clause names the table that 
contains the columns, called the base table. In this case, six columns will be 
retrieved from the Invoices table. Note that the last column, balance_due, is calculated from three other 
columns in the table.

In other words, a column by the name of balance_due 
doesn't actually exist in the database. This type of column is called a calculated 
value, and it exists only in the results of the query. In addition to the SELECT and FROM clauses, this SELECT statement 
includes a WHERE clause and an ORDER BY clause. The WHERE clause gives 
the criteria for the rows to be selected. In this case, a row is selected only if it bas 
a balance due that's greater than zero.

## Examples

### SQL Example 1

```sql
SELECT statement to be executed. Of course, if an application updates data, it can execute INSERT, UPDATE, and DELETE statements as well. With the skills that you'll learn in this book, though, you won't have any trouble coding the SQL statements you need. Cl1apter 1 <?php $query= "SELECT vendor_name, invoice_number, invoice_total! ON vendors . vendor_ id = invoices.vendor_ id WHERE invoice_total >= 500 ORDER BY vendor_narne, invoice_total $dsn = 'mysql:host=localhost;
```

Example SQL query

### SQL Example 2

```sql
with totals over 500:</hl> <?php foreach ($rows as $row) : ?> <p> Vendor: <?php echo $row['vendor_ name'];
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

**Question:** Practice using Cardinality Constraints in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
