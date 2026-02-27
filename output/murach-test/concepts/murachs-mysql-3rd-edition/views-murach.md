# Views

## Definition

Once you 
understand these skills, it's easy to learn how to use a graphical user interface 
such as MySQL Workbench to work with database objects such as tables and 
indexes.

## Explanation

How to create databases, tables, and indexes 
The SQL script that creates the AP database 
CREATE TABLE 
( 
• 
• 
invoices 
invoice_ id 
vendor_ id 
invoice_number 
invoice_date 
invoice_ total 
payment_ total 
credit_ total 
INT 
PRIMARY KEY 
) ; 
terms_ id 
INT 
VARCHAR(SO) 
DATE 
DECIMAL(9,2) 
DECIMAL(9,2) 
DECIMAL(9,2) 
INT 
invoice_due_date 
DATE 
payment_date 
DATE, 
CONSTRAINT invoices_ fk vendors 
FOREIGN KEY (vendor id) 
REFERENCES vendors (vendor_ id), 
CONSTRAINT invoices_ fk_terms 
FOREIGN KEY (terms_ id) 
REFERENCES terms (terms id) 
CREATE TABLE invoice line items 
( 
invoice_ id 
INT 
• 
• 
1nvo1ce_sequence 
INT 
INT 
NOT 
NOT 
NOT 
NOT 
NOT 
NOT 
NOT 
NOT 
account number 
line_ item_amount 
line_ item_description 
CONSTRAINT line_ items_pk 
DECIMAL(9,2) 
VARCHAR(lOO) 
NULL, 
NULL, 
NULL, 
NULL, 
NULL 
NULL 
NULL, 
NULL, 
NOT 
NOT 
NOT 
NOT 
NOT 
PRIMARY KEY (invoice_ id, invoice_sequence), 
CONSTRAINT line_ items_ fk_ invoices 
FOREIGN KEY (invoice id) 
REFERENCES invoices (invoice_ id), 
CONSTRAINT line_ items_ fk_acounts 
FOREIGN KEY (account number) 
NULL, 
NULL, 
NULL, 
NULL, 
NULL, 
AUTO_ INCREMENT, 
DEFAULT O, 
DEFAULT 0, 
REFERENCES general_ ledger_accounts (account number) 
) ; 
-- create an index 
CREATE INDEX invoices_ invoice date ix 
ON invoices (invoice_date DESC); 
The script used to create the AP database (part 2 of 2) 
Page2

Database design and impleme11,tation, 
How to use MySQL Workbench 
Since you often use a script to create tables and other database objects, it's 
important to understand the DDL skills presented in this chapter.

Once you 
understand these skills, it's easy to learn how to use a graphical user interface 
such as MySQL Workbench to work with database objects such as tables and 
indexes. For example, it's often useful to view these database objects before 
writing the SELECT, INSERT, UPDATE, or DELETE statements that use them. How to work with the columns of a table 
start, you can view the column defmitions for a table by right-clicking on the 
table in the Navigator window and selecting Alter Table to display the table in 
the main window.

Then, click on the Columns tab at the bottom of the window. For example, this figure shows the columns for the Invoices table. Here, you 
can see the name, data type, and other attributes of each column. For instance, 
you can see that the invoice_id column is the primary key column and an auto 
increment column. The payment_total and credit_total columns specify a default 
value of 0.00. And the pay1nent_date column allows null values and its default 
value is NULL.

## Examples

### SQL Example 1

```sql
create databases, tables, and indexes The SQL script that creates the AP database CREATE TABLE ( • • invoices invoice_ id vendor_ id invoice_number invoice_date invoice_ total payment_ total credit_ total INT PRIMARY KEY ) ;
```

Example SQL query

### SQL Example 2

```sql
create an index CREATE INDEX invoices_ invoice date ix ON invoices (invoice_date DESC);
```

Example SQL query

### SQL Example 3

```sql
drop existing keys. The foreign keys for the Invoices table ■ MySQl. Workbench D X 1.oca1 IMlance MySOLSO x File Edit Vtew Query Database Server Tools Scripting Help ouerv 1 il:1·\Hftlffll,;
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

**Question:** Practice using Views in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
