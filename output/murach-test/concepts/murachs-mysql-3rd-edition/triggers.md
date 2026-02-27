# Triggers

## Definition

How to declare and set variables

Stored prvgram development 
How to code IF statements 
statements based on a value that's returned by a Boolean expression.

## Explanation

Language skills for writing stored progra,ns 
The syntax for declaring a variable 
DECLARE variable_name data_type [DEFAULT literal_value]; 
The syntax for setting a variable to a literal value or an expression 
SET variable_name = {literal_value lexpression}; 
The syntax for setting a variable to a selected value 
SELECT column_ l[, column_ 2] ••• 
INTO variable_ name_ l[, variable_name_ 2] ••• 
A stored procedure that uses variables 
DELIMITER/ / 
CREATE PROCEDURE test() 
BEGIN 
DECLARE max_ invoice_total 
DECLARE min invoice total 
DECLARE percent_difference 
DECLARE count_ invoice id 
DECLARE vendor id var 
SET vendor_ id_var = 95; 
DECIMAL (9,2); 
DECIMAL(9,2); 
DECIMAL (9,4); 
INT; 
INT; 
SELECT MAX(invoice_total), MIN(invoice_total), COUNT(invoice_ id) 
INTO max_ invoice_total, min_ invoice_total, count_ invoice_ id 
FROM invoices WHERE vendor_ id = vendor_ id_var; 
SET percent_difference = (max_ invoice_total - min_ invoice_total) / 
min_ invoice_ total * 100; 
SELECT CONCAT('$', max_ invoice_total) AS 'Maximum invoice', 
CONCAT('$', min_ invoice_total) AS 'Minimum invoice•, 
CONCAT(' %', ROUND (percent_difference, 2 ) ) AS 'Percent difference', 
count invoice id AS 'Number of invoices'; 
END// 
The response from the system when the procedure is called 
Maxmum 
invoice 
► 
$46.21 
Description 
Minimum 
invoice 
S16.33 
Percent 
difference 
%182.98 
Number of 
invoices 
• 
A variable stores a value that can change as a stored program executes.

.I 
• 
A variable must have a name that's different from the names of any columns used 
in any SELECT statement within the stored program. To distinguish a variable from 
a column, you can add a suffix like ''_ var'' to the variable name. How to declare and set variables

Stored prvgram development 
How to code IF statements 
statements based on a value that's returned by a Boolean expression. A Boolean 
expression is an expression that returns a true value or a false value.

The script in this figure uses an IF statement to test the value of a variable. This variable contains the oldest invoice due date in the Invoices table. If this 
due date is less than the current date, the Boolean expression evaluates to true, 
and the statement in the IF clause shows that outstanding invoices are overdue. If the value is equal to the current date, the statement in the ELSEIF clause 
indicates that outstanding invoices are due today.

## Examples

### SQL Example 1

```sql
SELECT column_ l[, column_ 2] ••• INTO variable_ name_ l[, variable_name_ 2] ••• A stored procedure that uses variables DELIMITER/ / CREATE PROCEDURE test() BEGIN DECLARE max_ invoice_total DECLARE min invoice total DECLARE percent_difference DECLARE count_ invoice id DECLARE vendor id var SET vendor_ id_var = 95;
```

Example SQL query

### SQL Example 2

```sql
SELECT MAX(invoice_total), MIN(invoice_total), COUNT(invoice_ id) INTO max_ invoice_total, min_ invoice_total, count_ invoice_ id FROM invoices WHERE vendor_ id = vendor_ id_var;
```

Example SQL query

### SQL Example 3

```sql
SELECT CONCAT('$', max_ invoice_total) AS 'Maximum invoice', CONCAT('$', min_ invoice_total) AS 'Minimum invoice•, CONCAT(' %', ROUND (percent_difference, 2 ) ) AS 'Percent difference', count invoice id AS 'Number of invoices';
```

Example SQL query

### SQL Example 4

```sql
SELECT 'Outstanding invoices are overdue!';
```

Example SQL query

### SQL Example 5

```sql
SELECT 'No invoices are overdue.';
```

Example SQL query

### SQL Example 7

```sql
CREATE PROCEDURE test() BEGIN DECLARE first invoice due date DATE;
```

Example SQL query

### SQL Example 8

```sql
SELECT MIN(invoice_ due_date) INTO first_ invoice_ due_date FROM invoices WHERE invoice_ total - payment_total - credit_total > O;
```

Example SQL query

### SQL Example 9

```sql
SELECT •outstanding invoices are overdue!';
```

Example SQL query

### SQL Example 10

```sql
SELECT •outstanding invoices are due today!';
```

Example SQL query

### SQL Example 11

```sql
SELECT (•outstanding invoices are overdue!');
```

Example SQL query

### SQL Example 12

```sql
SELECT ('Outstanding invoices are due today!');
```

Example SQL query

### SQL Example 13

```sql
SELECT ('No invoices are overdue.');
```

Example SQL query

### SQL Example 14

```sql
CREATE PROCEDURE test(} BEGIN DECLARE terms_ id_var INT;
```

Example SQL query

### SQL Example 15

```sql
SELECT terms_id INTO terms_ id_ var FROM invoices WHERE invoice_ id = 4;
```

Example SQL query

### SQL Example 16

```sql
SELECT 'Net due 10 days• AS Terms;
```

Example SQL query

### SQL Example 17

```sql
SELECT 'Net due 20 days• AS Terms;
```

Example SQL query

### SQL Example 18

```sql
SELECT 'Net due 30 days' AS Terms;
```

Example SQL query

### SQL Example 19

```sql
SELECT 'Net due more tha.n 3 0 days ' AS Terms;
```

Example SQL query

### SQL Example 20

```sql
CREATE PROCEDURE test( ) BEGIN DECLARE i INT DEFAULT 1;
```

Example SQL query

### SQL Example 21

```sql
SELECT s AS message;
```

Example SQL query

### SQL Example 22

```sql
update as the stored procedure in this figure with this UPDATE statement: UPDATE invoices SET credit_total = credit_total + (invoice_total * .1) WHERE invoice_total - payment_total - credit_total > 0 AND invoice_total > 1000 However, if you encounter a situation where it makes sense to use a cursor, the skills presented in this figure should help you do that. The syntax Declare a cursor DECLARE cursor_ name CURSOR FOR select_statement;
```

Example SQL query

### SQL Example 23

```sql
CREATE PROCEDURE test() BEGIN DECLARE invoice_ id_var DECLARE invoice total var DECLARE row_not_ found DECLARE update_count INT;
```

Example SQL query

### SQL Example 24

```sql
SELECT invoice_ id, invoice_total FROM invoices WHERE invoice_total - payment_total - credit total> O;
```

Example SQL query

### SQL Example 25

```sql
UPDATE invoices SET credit_total = credit_total + (invoice total* .1) WHERE invoice id= invoice_ id_var;
```

Example SQL query

### SQL Example 26

```sql
SELECT CONCAT{update_count, ' row(s) updated.');
```

Example SQL query

### SQL Example 27

```sql
SELECT statement to retrieve data and no data is found. Occurs when any error condition other than the NOT FOUND condition occtrrs. condition occurs or when any warning messages occur. The syntax for declaring a condition handler DECLARE {CONTINUE jEXIT} HANDLER FOR {mysql_error_ codelSQLSTATE sqlstate_ code lnamed_condition} handl er_ ac tions;
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

**Question:** Practice using Triggers in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
