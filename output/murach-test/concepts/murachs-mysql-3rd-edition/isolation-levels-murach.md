# Transaction Isolation Levels

## Definition

• 
To set a default value for a parameter, you can use an IF statement to check if the 
parameter contains a null value.

## Explanation

How to create stored prvcedures and functions 
A CREATE PROCEDURE statement that provides a default value 
DELIMITER// 
CREATE PROCEDURE update_ invoices_credit_total 
( 
invoice_ id_param 
INT, 
credit_ total_param 
DECIMAL(9,2) 
) 
BEGIN 
DECLARE sql_error TINYINT DEFAULT FALSE; 
DECLARE CONTINUE HANDLER FOR SQLEXCEPTION 
SET sql_error = TRUE; 
-- Set default values for NULL values 
IF credit_ total_param IS NULL THEN 
SET credit_ total_param = 100; 
END IF; 
START TRANSACTION; 
UPDATE invoices 
SET credit_total = credit_ total_param 
WHERE invoice id= invoice_ id_param; 
IF sql_ error = FALSE THEN 
COMMIT; 
ELSE 
ROLLBACK; 
END IF; 
END// 
A statement that calls the stored procedure 
CALL update_ invoices_credit_total(56, 200); 
Another statement that calls the stored procedure 
CALL update_ invoices_credit_total(56, NULL); 
Description 
• 
You can provide a default value for a parameter so that if the calling program 
passes a null value for the parameter, the default value is used instead.

• 
To set a default value for a parameter, you can use an IF statement to check if the 
parameter contains a null value. If it does, you can assign a default value to the 
parameter. • 
It's a good programming practice to code your CREATE PROCEDURE statements 
so they list parameters that require values first, fallowed by parameters that allow 
null values. How to set a default value for a parameter

Stored prvgram development 
How to validate parameters and raise errors 
Within a stored procedure, it's generally considered a good practice to 
prevent errors by checking the parameters before they 're used to make sure 
they're valid.

This is often refe1Ted to as data validation. Then, if the data isn't 
valid, you can execute code that makes it valid, or you can raise an error, which 
returns the error to the calling program. that are available from MySQL. To do that, you code the SIGNAL statement 
followed by the SQLSTATE keyword, followed by a SQLSTATE code. Then, 
you can optionally include a SET statement that sets a message and MySQL 
error code for the error.

## Examples

### SQL Example 1

```sql
create stored prvcedures and functions A CREATE PROCEDURE statement that provides a default value DELIMITER// CREATE PROCEDURE update_ invoices_credit_total ( invoice_ id_param INT, credit_ total_param DECIMAL(9,2) ) BEGIN DECLARE sql_error TINYINT DEFAULT FALSE;
```

Example SQL query

### SQL Example 2

```sql
UPDATE invoices SET credit_total = credit_ total_param WHERE invoice id= invoice_ id_param;
```

Example SQL query

### SQL Example 3

```sql
UPDATE invoices WHERE invoice_ id = invoice_ id__param;
```

Example SQL query

### SQL Example 4

```sql
CREATE PROCEDURE insert_ invoice ( vendor_id_param invoice_ number_param invoice_date_param invoice_ total_param terms_id_param invoice_due_date_param INT, VARCHAR(SO), DATE, DECIMAL(9,2), INT, ) BEGIN DECLARE terms id var DATE DECLARE invoice_due_date_var DECLARE terms_due_days_var -- Validate paramater values INT;
```

Example SQL query

### SQL Example 5

```sql
SELECT default_ terms_ id INTO terms id var FROM vendors WHERE vendor_ id = vendor_ id_param;
```

Example SQL query

### SQL Example 6

```sql
SELECT terms_due_days INTO terms_due_days_var FROM terms WHERE terms_ id = terms_ id_var;
```

Example SQL query

### SQL Example 7

```sql
SELECT DATE_ADD(invoice_ date_param, INTERVAL terms_due_days_var DAY) INTO invoice_due_date_var;
```

Example SQL query

### SQL Example 8

```sql
INSERT INTO invoices (vendor_ id, invoice_nwnber, invoice_date, invoice_ total, terms_id, invoice_due_date) VALUES (vendor_ id_param, invoice_number_param, invoice_date_param, invoice_total_param, terms_ id_var, invoice_due_date_var);
```

Example SQL query

### SQL Example 9

```sql
insert 1 row(s) affected A statement that raises an error CALL insert_ invoice(34, 'ZXA-080', '2018-01-18', -14092.59, NULL, NULL) ;
```

Example SQL query

### SQL Example 10

```sql
SELECT statement displays the value of the @count variable a.fter it has been set and incremented by the two CALL statements. You can also use the SET statement outside of a stored program to set the value of a user variable. The syntax for setting a user variable SET @variable_name = expression Two stored procedures that work with the same user variable DELIMITER // CREATE PROCEDURE set_global_ count ( count var :INT ) BEGIN SET @count= count_var;
```

Example SQL query

### SQL Example 11

```sql
CREATE PROCEDURE increment_ global_ count( ) BEGIN SET @count= @count+ 1;
```

Example SQL query

### SQL Example 12

```sql
SELECT statement to the user. Finally, the DEALLOCATE PREPARE state- ment releases the prepared statement. Once a prepared statement is released, it can no longer be executed. A stored procedure that uses dynamic SQL DELIMITER// CREATE PROCEDURE select_ invoices ( min_ invoice_date_param min_ invoice_total_param ) BEGIN DATE, DECIMAL(9,2) DECLARE select clause VARCHAR(200);
```

Example SQL query

### SQL Example 13

```sql
SELECT invoice_ id, invoice_ nwnber, invoice_date, invoice total FROM invoices 11 ;
```

Example SQL query

### SQL Example 14

```sql
select invoices statement FROM @dynamic_ sql;
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

**Question:** Practice using Transaction Isolation Levels in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
