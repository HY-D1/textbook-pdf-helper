# Events

## Definition

How to use a condition handler (part 1 of 2)

Stored prvgram development 
The first stored procedure in part 2 shows how to exit the current block 
of code as soon as an error occurs.

## Explanation

Language skills for writing stored progra,ns 
A stored procedure that doesn't handle errors 
DELIMITER// 
CREATE PROCEDURE test() 
BEGIN 
INSERT INTO general_ ledger_ accounts VALUES (130, 'Cash'); 
SELECT '1 row was inserted.'; 
END// 
The response from the system 
Error Code: 1062. Duplicate entry 'Cash' for key 'account_description' 
A stored procedure that uses a CONTINUE handler to handle an error 
DELIMITER// 
CREATE PROCEDURE test() 
BEGIN 
DECLARE duplicate_entry_ for_key TINYINT DEFAULT FALSE; 
DECLARE CONTINUE HANDLER FOR 1062 
SET duplicate_entry_ for_key = TRUE; 
INSERT INTO general_ ledger_accounts VALUES (130, 'Cash'); 
IF duplicate_entry_ for_key = TRUE THEN 
SELECT 'Row was not inserted - duplicate key encountered.' AS message; 
ELSE 
SELECT '1 row was inserted.' AS message; 
END IF; 
END// 
The response from the system 
message 
► 
Row was not inserted - duplicate key encountered.

How to use a condition handler (part 1 of 2)

Stored prvgram development 
The first stored procedure in part 2 shows how to exit the current block 
of code as soon as an error occurs. To start, this stored procedure begins by 
declaring a variable named duplicate_entry _for_key just like the stored proce-
dure in part 1. Then, it uses the BEGIN and END keywords to nest a block of 
code within the block of code for the procedu1·e.

Within the nested block of code, 
the frrst statement declares a condition handler for the MySQL error with a code 
of 1062. This handler uses the EXIT keyword to indicate that it should exit the 
block of code when this error occurs. Then, the second statement executes the 
INSERT statement that may cause the error. If no error occurs, the third state-
ment in the block displays a message that indicates that the row was inserted.

## Examples

### SQL Example 1

```sql
CREATE PROCEDURE test() BEGIN INSERT INTO general_ ledger_ accounts VALUES (130, 'Cash');
```

Example SQL query

### SQL Example 2

```sql
SELECT '1 row was inserted.';
```

Example SQL query

### SQL Example 3

```sql
CREATE PROCEDURE test() BEGIN DECLARE duplicate_entry_ for_key TINYINT DEFAULT FALSE;
```

Example SQL query

### SQL Example 4

```sql
INSERT INTO general_ ledger_accounts VALUES (130, 'Cash');
```

Example SQL query

### SQL Example 5

```sql
SELECT 'Row was not inserted - duplicate key encountered.' AS message;
```

Example SQL query

### SQL Example 6

```sql
SELECT '1 row was inserted.' AS message;
```

Example SQL query

### SQL Example 7

```sql
CREATE PROCEDURE test() BEGIN BEGIN DECLARE EXIT HANDLER FOR 1062 END;
```

Example SQL query

### SQL Example 8

```sql
CREATE PROCEDURE test() BEGIN DECLARE sql_ error TINYINT DEFAULT FALSE;
```

Example SQL query

### SQL Example 9

```sql
SELECT 1 1 row was inserted.' AS message;
```

Example SQL query

### SQL Example 10

```sql
SELECT 'Row was not inserted - SQL exception encountered.' AS message;
```

Example SQL query

### SQL Example 11

```sql
INSERT statement. For example, if you enter a third column with a value of 'xx', the stored procedure executes the condition handler for the SQLEXCEPTION condition. A stored procedure that uses multiple condition handlers DELIMITER// CREATE PROCEDURE test() BEGIN DECLARE colwnn_cannot_be_null TINYINT DEFAULT FALSE;
```

Example SQL query

### SQL Example 12

```sql
INSERT INTO general_ ledger_ accounts VALUES (NULL, 'Test');
```

Example SQL query

### SQL Example 13

```sql
SELECT 'Row was not inserted - colwnn cannot be null.' AS message;
```

Example SQL query

### SQL Example 14

```sql
SELECT 'Row was not inserted - END IF;
```

Example SQL query

### SQL Example 15

```sql
update increases the balance in the savings account. Then, if one of these updates fails, the customer either gains or loses the amount of the transaction. But here again, treating the two updates as a single transaction solves this problem. Usually, that's what you want. How to use transactions and locking A stored procedure that runs three INSERT statements as a transaction DELIMITER// CREATE PROCEDURE test(} BEGIN DECLARE CONTINUE HANDLER FOR SQLEXCEPTION SET sql_ error = TRUE;
```

Example SQL query

### SQL Example 16

```sql
INSERT INTO invoices VALUES ( 115, 34, • ZXA-080 •, • 2018-01-18', 14092. 59, 0, 0, 3, '2018-04-18', NULL};
```

Example SQL query

### SQL Example 17

```sql
INSERT INTO invoice_ line_ items VALUES (115, 1, 160, 4447.23, 'HW upgrade');
```

Example SQL query

### SQL Example 18

```sql
SELECT 'The transaction was committed.';
```

Example SQL query

### SQL Example 19

```sql
SELECT 'The transaction was rolled back.';
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

**Question:** Practice using Events in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
