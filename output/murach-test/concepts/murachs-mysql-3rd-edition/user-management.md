# User Management

## Definition

Indicates that the function does not produce the same results given 
the same inpt1t values.

## Explanation

How to create stored prvcedures and functions 
Some of the characteristics for a MySQL function 
Characteristic 
Description 
DETERMINISTIC 
NOT DETERMI NISTIC 
READS SQL DATA 
MODIFIES SQL DATA 
CONTAINS SQL 
NO SQL 
Indicates that the function produces the same results given the same 
input values. Indicates that the function does not produce the same results given 
the same inpt1t values. This is the default.

Indicates that the function contains one or more SQL statem.ents 
st1ch as SELECT statements that read data from a database but no 
statements that write data. Indicates that the function contains SQL statements such as INSERT, 
UPDATE, and DELETE statements tl1at write data to a database. such as SET statements that don't read from or write to a database. This is the default. Indicates that the function doesn't contain SQL statements.

A function that gets a random number 
DELIMITER // 
CREATE FUNCTION rand_ i nt () 
RETURNS INT 
NOT DETERMINISTIC 
NO SQL 
BEGIN 
RETURN ROUND (RAND () * 1000); 
END// 
A SELECT statement that uses the function 
SELECT rand_ int () AS random_number; 
I random_number 
► l3LS 
Description 
• 
If binary logging is enabled, which it is by default with MySQL 8.0, each function 
must include the DETERMINISTIC, NO SQL, or READS SQL DATA characteristic.

## Examples

### SQL Example 1

```sql
DELETE statements tl1at write data to a database. such as SET statements that don't read from or write to a database. This is the default. Indicates that the function doesn't contain SQL statements. A function that gets a random number DELIMITER // CREATE FUNCTION rand_ i nt () RETURNS INT NOT DETERMINISTIC NO SQL BEGIN RETURN ROUND (RAND () * 1000);
```

Example SQL query

### SQL Example 2

```sql
SELECT statement that uses the function SELECT rand_ int () AS random_number;
```

Example SQL query

### SQL Example 3

```sql
CREATE FUNCTION get_balance_ due ( invoice_id_pararn INT ) RETURNS DECIMAL(9,2 ) DETERMINISTIC READS SQL DATA BEGIN DECLARE balance_ due_var DECIMAL(9,2);
```

Example SQL query

### SQL Example 4

```sql
SELECT invoice_total - payment_total - credit_total INTO balance_ due_var FROM invoices WHERE invoice_ id = invoice_ id_param;
```

Example SQL query

### SQL Example 5

```sql
drop the get_balance_due function, the get_sum_balance_due function won't work. As a result, yo11 should avoid dropping any database objects that other database objects depend on. The syntax of the DROP FUNCTION statement DROP FUNCTION [IF EXISTS] function_name A statement that creates a function DELIMITER // CREATE FUNCTION get_ swn_balance_due ( vendor_ id_pararn INT ) RETURNS DECIMAL(9,2) DETERMINISTIC READS SQL DATA BEGIN DECLARE swn_ balance_ due_var DECIMAL(9,2);
```

Example SQL query

### SQL Example 6

```sql
SELECT SUM(get_balance_due(invoice_ id}) INTO swn_balance_due_var FROM invoices WHERE vendor_ id = vendor_ id_param;
```

Example SQL query

### SQL Example 7

```sql
SELECT vendor_ id, invoice_ nwnber, get_balance_due (invoice_ id) AS balance_ due, get_ swn_balance_ due (vendor_ id) AS swn_bala.nce_due FROM invoices WHERE vendor_ id = 37;
```

Example SQL query

### SQL Example 8

```sql
DROP FUNCTION get_ swn_ balance_ due;
```

Example SQL query

### SQL Example 9

```sql
DROP FUNCTION IF EXISTS get_ swn_balance_ due;
```

Example SQL query

### SQL Example 10

```sql
Alter S!ored Procedure. [)fop Stored Procedure. Refresh All SET MESSAGE_TEXT = The invoice_total col~ 111Jst ~ a posi1 Wormatton Procedure: test MYSQL_ERRNO = ;
```

Example SQL query

### SQL Example 11

```sql
create triggers and events The syntax of the CREATE TRIGGER statement CREATE TRIGGER trigger_name {BEFOREIAFTER} {INSERTjUPDATEIDELETE} ON table_ name FOR EACH ROW trigger_body A CREATE TRIGGER statement that corrects mixed-case state names DELIMITER// CREATE TRIGGER vendors_before_ update BEFORE UPDATE ON vendors FOR EACH ROW BEGIN SET NEW.vendor_ state = UPPER(NEW.vendor_ state);
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

**Question:** Practice using User Management in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
