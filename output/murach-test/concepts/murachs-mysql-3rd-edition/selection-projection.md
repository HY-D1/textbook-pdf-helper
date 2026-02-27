# Selection and Projection

## Definition

If, for example, you have selected 
the EX database and you try to run a statement that refers to tables in the AP 
database, you will get an error.

## Explanation

An introduction to MySQL 
How to handle syntax errors 
If an error occurs during the execution of a SQL statement, MySQL 
Workbench displays a message that includes the error numbe1· and a brief 
description of the error. In figure 2-9, for example, the message displays an error 
number of 1146 and a brief description that says ''Table ap.vendor doesn't exist." 
In this example, the problem is that the Vendor table doesn't exist in the 
database.

To fix the problem, you need to edit the SQL statement so the table is 
Vendors instead of Vendor. Then, you should be able to successfully run the SQL 
statement. This figure also lists some other common causes of errors. As you can see, 
most e1Tors are caused by incorrect syntax. However, it's also common to get an 
error if you have selected the wrong database. If, for example, you have selected 
the EX database and you try to run a statement that refers to tables in the AP 
database, you will get an error.

Regardless of what's causing the problem, you 
can usually identify and correct the problem without much trouble. In some 
cases, though, it may be diffict1lt to figure out the cause of an error. Then, you 
can usually get more information about the error by searching the Internet or by 
searching the MySQL Reference Manual as described later in this chapter. Cliapter 2 
How to use MySQL Workbench and other develop,nent tools 
How to handle syntax errors 
iJ MySQL Workbench 
D 
X 
4i-
Local inslance MySOl.80 X 
File 
&lit v,_ 0uef)' 
Oatabas-e 
Server 
Tools 
Scnpb119 
Help 
iil'Hi1 _________________________ _ 
SCKEMAS 
c;i Q I ~ lll' fl 
I~ I 
Q I Lmit to 1000rows 
• I 
q_ [niter obJeds 
y § ap 
1 • 
SE~ECT vendor_name, vendor_city, vendor_shrte 
FR0'1 vendor 
T 
Tables 
ORDER BV vendor _nam~ 
► II Qeneral_ledger_accounts 
► II lnvolce_archlve 
► II lnvolce:_line:_ltems 
► 
Invoices 
► II terms 
► 8 ve:ndor_contacls 
► 
vendors 
Views 
'rJl Stored Procedures 
i;ai Funcbons 
► 
ex 
► 
om 
► 
sys 
Administration 
Schemas 
Table: vendors 
Columns: 
vendor id 
vendor_name 
vendor llddress l 
vendor -address2 
vendof =dty 
vendor _state 
ObJe:ct Info 
Session 
< 
014)1 
,.

## Examples

### SQL Example 1

```sql
SELECT vendor_natie, vcndor_city, vendor_strte fRc»1 vendors ORDER BY vendor name;
```

Example SQL query

### SQL Example 2

```sql
SELECT vendor_name, vendor_city FR<Y-1 vendors T Tables ► II gcneral_ledger_accounts ► 6J lnvoice_archlve ► invoiu_line_items l,lfERE vendor_id: ;
```

Example SQL query

### SQL Example 3

```sql
SELECT COUttT(*) AS number_of_invoices, SUM(invoice_total - payment_total - credit_total) AS total_due FRCJ1 invoices ► Invoice ► II terms i..HERE vendor id= ;
```

Example SQL query

### SQL Example 4

```sql
SELECT statement, the MySQL Command Line Client displays a message giving the nu1nber of rows that are included in the result set and the amount of time it took to run the query. In this case, it took less than 1/100 of a second to run the query. Cliapter 2 How to list the names of all databases managed by the server mysql> show databases;
```

Example SQL query

### SQL Example 5

```sql
select a database for use mysql> use ap;
```

Example SQL query

### SQL Example 6

```sql
select data from a database mysql> select vendor_name from vendors limit 5;
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

**Question:** Practice using Selection and Projection in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
