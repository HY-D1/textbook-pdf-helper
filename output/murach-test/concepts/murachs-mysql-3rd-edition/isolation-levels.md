# Transaction Isolation Levels

## Definition

AUTO INCREMENT 
Identifies a column whose value is automatically incremented by 
MySQL when a new row is added.

## Explanation

How to create databases, tables, and indexes 
The syntax of the CREATE TABLE statement 
CREATE TABLE [db_name.]table_name 
( 
) 
col,:imn_ name_ l data_ type [column_ attributes] 
[, column_name_ 2 data_ t ype [column_ attributes]] ... [, table_ level_ constraints] 
Common column attributes 
Attribute 
Description 
NOT NULL 
UNIQUE 
Indicates that the column doesn't accept null values. If ornitted, 
the column can accept null values.

DEFAULT default_ value 
Specifies that each value stored in the column must be uajque. Specifies a default value for the column as a literal or as an 
• 
expression. AUTO INCREMENT 
Identifies a column whose value is automatically incremented by 
MySQL when a new row is added. An auto increment column 
must be defined as an integer or a floating-point number. A statement that creates a table without column attributes 
CREATE TABLE vendors 
( 
) 
vendor_ id 
vendor name 
INT, 
VARCHAR ( 5 0) 
A statement that creates a table with column attributes 
CREATE TABLE vendors 
( 
) 
vendor id 
vendor_name 
INT 
VARCHAR ( 5 0) 
NOT NULL 
NOT NULL 
UNIQUE AUTO_ INCREMENT, 
UNIQUE 
Another statement that creates a table with column attributes 
CREATE TABLE invoic es 
( 
invoice_ id 
vendor id 
invoice_ number 
invoice date 
invoice_ total 
payment_ total 
) 
Description 
INT 
INT 
VARCHAR ( 5 0 ) 
DATE, 
DECIMAL (9,2 ) 
DECIMAL (9,2) 
NOT NULL 
NOT NULL, 
NOT NULL, 
NOT NULL, 
UNIQUE, 
DEFAULT 0 
• 
To test the code in this figure and in the figures that follow, you can select the EX 
database.

• 
The CREATE TABLE statement creates a table based on the column names, data 
types, and attributes that you specify. In addition, it allows you to specify some 
attributes and constraints at the table level as described later in this chapter. How to create a table

Database design and impleme11,tation, 
How to code a primary key constraint 
Whether you realize it or not, the NOT NULL and UNIQUE keywords are 
examples of constraints.

## Examples

### SQL Example 1

```sql
drop tables, you must drop the last table that was created first. Then, you can work back to the first table that was created. Otherwise, the foreign keys might not allow you to delete the tables. The SQL script that creates the AP database -- create the database DROP DATABASE IF EXISTS ap;
```

Example SQL query

### SQL Example 3

```sql
select the database USE ap;
```

Example SQL query

### SQL Example 4

```sql
create the tables CREATE TABLE general_ ledger_accounts { account_ number account_description ) ;
```

Example SQL query

### SQL Example 5

```sql
CREATE TABLE terms ( INT VARCHAR ( 5 0) PRIMARY KEY, UNIQUE terms id terms_description terms_due_days INT VARCHAR ( 5 0) INT PRIMARY KEY NOT NULL, NOT NULL AUTO_ INCREMENT, ) ;
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
