# Transactions

## Definition

Since each transaction is unaware 
of the other, the later update overwrites the earlier update.

## Explanation

How to use transactions and locking 
The four types of concurrency problems 
Problem 
Description 
Losl updates 
Dirty reads 
Nonrepeatable reads 
Phantom reads 
Description 
Occur when two transactions select the same row a11d then update the row 
based on the values originally selected. Since each transaction is unaware 
of the other, the later update overwrites the earlier update. Occur when a transaction selects data that l1asn 't been committed by 
another transaction.

For example, transaction A cha11ges a row. Tra11saction 
B then selects the changed row before transaction A commits the change. If transaction A then rolls back the change, transaction B has selected data 
that doesn't exist in the database. Occur when two SELECT statements tl1at try to get the same data get 
different values because another transaction has updated the data in the 
time between the two statements.

For example, transaction A selects a row. Transaction B then updates the row. When transaction A selects the same 
row again, the data is different. Occur when you perlor1n an update or delete on a set of rows at the same 
time that another transaction is pe1fo1ming an insert or delete that affects 
one or more rows in that same set of rows. For exa1nple, transaction A 
updates the payment total for each invoice that has a balance due, but trans-
action B inserts a new, unpaid, invoice while transaction A is still running.

## Examples

### SQL Example 1

```sql
SELECT statement in transaction B is executed. This returns four rows with rep_id values of 1, 2, 3, and 4. Four transactions that show how to work with locking reads Transaction A -- Execute each statement one at a time. - - Al tern.ate with Transactions B, C, and D as described. START TRANSACTION;
```

Example SQL query

### SQL Example 2

```sql
with rep_ id of 2 in parent table ---- SELECT* FROM sales_ reps WHERE rep_ id = 2 FOR SHARE;
```

Example SQL query

### SQL Example 3

```sql
insert row with rep_ id of 2 into child table INSERT INTO sales_ totals (rep_ id, sales_year, sales_ total) VALUES (2, 2019, 138193.69);
```

Example SQL query

### SQL Example 4

```sql
SELECT * FROM sales_reps WHERE rep_id < 5 FOR UPDATE';
```

Example SQL query

### SQL Example 6

```sql
update the same resources, code the updates in the same order in each transaction. UPDATE statements that illustrate deadlocking Transaction A START TRANSACTION;
```

Example SQL query

### SQL Example 7

```sql
UPDATE savings SET balance= balance - transfer_amount;
```

Example SQL query

### SQL Example 8

```sql
UPDATE checking SET balance= balance + transfer_amount ;
```

Example SQL query

### SQL Example 9

```sql
UPDATE checking SET balance = balance - t r ansf er_ amount ;
```

Example SQL query

### SQL Example 10

```sql
UPDATE savings SET balance= balance+ transfer_ amount;
```

Example SQL query

### SQL Example 11

```sql
UPDATE savings SET balance = balance+ transfer_ amount;
```

Example SQL query

### SQL Example 12

```sql
create stored proce- How to create stored prvcedures and functions The syntax of the CREATE PROCEDURE statement CREATE PROCEDURE procedure_ name ( [parameter_name_ l data_type] [, parameter_name_ 2 data_type] ... ) sql_block A script that creates a stored procedure that updates a table DELIMITER / / CREATE PROCEDURE update_ invoices_credit_total ( invoice_ id_param credit_total_param ) BEGIN INT, DECIMAL(9,2) DECLARE sql_ error TINYINT DEFAULT FALSE;
```

Example SQL query

### SQL Example 13

```sql
UPDATE invoices SET credit_total = credit_total_param WHERE invoice id= invoice_ id_param;
```

Example SQL query

### SQL Example 14

```sql
CREATE PROCEDURE update_ invoices_credit_ total ( IN invoice_ id_param IN credit_ total_param OUT update_ count ) BEGIN INT, DECIMAL(9,2}, INT SET sql_ error = TRUE;
```

Example SQL query

### SQL Example 15

```sql
UPDATE invoices SET credit total= credit_ total_param IF sql_ error = FALSE THEN SET update_count = 1;
```

Example SQL query

### SQL Example 16

```sql
SELECT CONCAT('row count: ', @row_ count} AS update_ count;
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

**Question:** Practice using Transactions in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
