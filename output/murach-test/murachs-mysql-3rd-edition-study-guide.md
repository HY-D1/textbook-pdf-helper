# Study Guide
Generated: 2026-02-27T10:15:30.955736

## Introduction to Relational Databases

**Definition:** 4 
The hardware con1ponents of a client/server system ......................................................

### Explanation
, ___ _ 
. --· . . -
-.. .. -- . ,. -
MASTER THE SQL STATEMENTS 
tl1at every application developer needs 
for retrieving and updating the data 
in a MySQL database 
D SIGN DATABASES IKE A PRO 
and code tl1e SQL state1nents tl1at create 
databases, tables, indexes, and ,ie,vs 
GAIN PROFESSIONAL SKILLS 
like using transactions, stored procedures, 
functions, triggers, and events 
GET STARTED AS A DBA 
by learning l1ow to configure tl1e server, 
manage security, and create bacluips

3RD EDITION 
Joel Murach

TRAINING & REFERENCE 
3RD EDITION 
Joel Murach 
M IKE M URACH & A SSOCIATES, I NC.

4340 N. Knoll Ave. • Fresno, CA 93722 
www.murach.com • murachbooks@murach.com

Editorial team 
Author: 
Writer/Editor: 
Editorial Support: 
Production: 
Joel Murach 
Anne Boehm 
Steven Mannion 
Samantha Walker 
Books on general-purpose programming languages 
Murach's Python Programming 
Murach's Java Programming 
Murach's C++ Programming 
Murach's C# 
Murach 's Visual Basic 
Books for web developers 
Murach's HTML5 and CSS3 
Murach's JavaScript and)Query 
Murach's PHP and MySQL 
Murach.'s Java Servlets and JSP 
Murach's ASP.NET Web Progra11iming with C# 
Books for database programmers 
Murach 's MySQL 
Murach's SQL Server for Developers 
Murach's Oracle SQL and PLJSQL for Developers 
For more on Murach books, 
please visit us at www.murach.com 
© 2019, Mike Murach & Associates, Inc.

All rights reserved. Printed in the United States of America 
10 9 8 7 6 5 4 3 2 1 
ISBN: 978-1-943872-36-7

Content 
Introduction 
An introduction to relational databases 
How to use MySQL Workbench and other development tools 
How to retrieve data from a single table 
How to retrieve data from two or more tables 
How to insert, update, and delete data 
How to code summary queries 
How to code subqueries 
How to work with data types 
How to use functions 
How to design a database 
How to create databases, tables, and indexes 
How to create views 
Language skills for writing stored programs 
How to use transactions and locking 
How to create stored procedures and functions 
How to create triggers and events 
An introduction to database administration 
How to secure a database 
How to backup and restore a database 
Appendixes 
Appendix A 
Appendix B 
How to install the software for this book on Windows 
How to install the software for this book on macOS 
• •• 
Xlll

•• 
Expanded contents 
VI I 
Expanded contents 
============= 
An introduction to client/server systems .........................................

### Key Points
- Understanding Introduction to Relational Databases is essential for working with databases

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Data Independence

**Definition:** ••• 
Expanded contents 
XI 11 
How to use function characteristics ............................................................................

### Explanation
••• 
Expanded contents 
XI 11 
How to use function characteristics ............................................................................ 466 
A function that calculates balance due ....................................................................... 468 
How to drop a function ............................................................................................... 470 
How to use Workbench with procedures 
and functions ..................................................................................

472 
How to view and edit to red routines ......................................................................... 472 
How to create stored routines ..................................................................................... 472 
How to drop stored routines ........................................................................................ 472 
How to work with triggers ..............................................................

478 
How to create a BEFORE trigger ............................................................................... 478 
How to use a trigger to enforce data consistency ....................................................... 480 
How to create an AFTER trigger ............................................................................... 482 
How to view or drop triggers ......................................................................................

### Key Points
- 466 
A function that calculates balance due .......................................................................
- 468 
How to drop a function ...............................................................................................
- 470 
How to use Workbench with procedures 
and functions ..................................................................................
- 472 
How to view and edit to red routines .........................................................................
- 472 
How to create stored routines .....................................................................................

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Entity-Relationship Model

**Definition:** • 
The set1rer is a con1puter that stores the files and database of· the system and 
provide services to the clients.

### Explanation
Cl1t1pter 1 
Ai, i11trodi1ctio11 to 1?latio1,al datal1t1ses 
A simple client/server system 
I 
Database Server 
Network 
Client 
Client 
Client 
The three hardware components of a client/server system 
• 
The clie111.r are the PC . • Mac . or workstation. of the system. Tl1ey can also be 
mobile de,1ice like laptops. tablet~, and smartphones. • 
The set1rer is a con1puter that stores the files and database of· the system and 
provide services to the clients.

W11en it stores dntabnses. itls often referred to as a 
datab,1~~e sen·er. • 
The 11en,•ork con. i ts of the cabling. communication line , and other component 
that connect the clienu and the erver ot· lhe . y tem. Client/server system implementations 
• 
In a si1nple clie11t/sen•er S)'Ste111 like the one above. the sen·er i t),.pically a 
high-po\vered PC that comn1unicate \vith the clients o er a local area nen,•ork 
(IAN).

### Key Points
- Tl1ey can also be 
mobile de,1ice like laptops.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## ER Diagrams

**Definition:** • 
Each column definition also indicates whether or not it can contain null values.

### Explanation
The columns of the Invoices table 
Column Name 
Datatype 
PK 
NIii 
invoice_id 
[N'T{ll) 
vendor_id 
IN'T{ll) 
□ 0 
invoice_number 
VARCHAR{SO) 
□ 0 
invoice_date 
DATE 
□ 121 
lnvoice_toti.i 
D ECIMAL(9,2) 
□ 121 
payment_total 
DECIMAL{9,2) 
□ 0 
credjt_toti.i 
DECIMAL(9,2) 
□ 121 
terms Id 
INT(ll) 
□ 0 
invoice_due_dare 
DATE 
□ 121 
payment_dat e 
DATE 
□ □ 
□ □ 
Column Name: 
O,arset/CoDation: 
Comments: 
Common MySQL data types 
Type 
Description 
Cl1apter 1 
An introduction to relational databases 
UQ 
B 
UN 
Zf 
AI 
□ □ □ □ 0 
□ □ □ □ □ 
□ □ □ □ □ 
□ □ □ □ □ 
□ □ □ □ □ 
□ □ □ □ □ 
□ □ □ □ □ 
□ □ □ □ □ 
□ □ □ □ □ 
□ □ □ □ □ 
□ □ □ □ □ 
Data Type: 
Default: 
Storage: 
V-rb.Jal 
Prrnary Key 
Brlary 
G 
□ 
□ 
□ 
□ 
□ 
□ 
□ 
□ 
□ 
□ 
□ 
DefaultJExpression 
·o.oo· 
'0.00' 
NULL 
Stored 
NotNul 
Unsigned 
Unique 
Zero Al 
Auto Increment 
Generated 
CHAR, VARCHAR 
INT, DECIMAL 
FLOAT 
A string of letters, symbols, and numbers.

DATE 
Description 
Integer and deci111al numbers that contain an exact value. Floating-point numbers that contain an approximate value. Dates and times. • 
The data type that's assigned to a column determines the type of information that 
can be stored in the column. • 
Each column definition also indicates whether or not it can contain null values. A 
null value indicates that the value of the column is unknown.

• 
A column can also be defined with a def a ult value. Then, that value is used if 
another value isn't provided when a row is added to the table. • 
A column can also be defined as an auto increment column. An auto increment 
column is a numeric column whose value is generated automatically when a row is 
added to the table. How columns are defined

An introduction to MySQL 
How to read a database diagram 
When working with relational databases, you can use an entity-relationship 
(ER) diagrani to show how the tables in a database are defined and related.

### Key Points
- DATE 
Description 
Integer and deci111al numbers that contain an exact value.
- Floating-point numbers that contain an approximate value.
- • 
The data type that's assigned to a column determines the type of information that 
can be stored in the column.
- • 
Each column definition also indicates whether or not it can contain null values.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Cardinality Constraints

**Definition:** To start, this figure shows some of the columns and rows of the 
Invoices table.

### Explanation
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

### Key Points
- To start, this figure shows some of the columns and rows of the 
Invoices table.
- Then, in the SELECT statement that follows, the SELECT clause 
names the columns to be retrieved, and the FROM clause names the table that 
contains the columns, called the base table.
- In this case, six columns will be 
retrieved from the Invoices table.
- Note that the last column, balance_due, is calculated from three other 
columns in the table.
- In other words, a column by the name of balance_due 
doesn't actually exist in the database.

### Examples
**SQL Example 1:**
```sql
SELECT statement to be executed. Of course, if an application updates data, it can execute INSERT, UPDATE, and DELETE statements as well. With the skills that you'll learn in this book, though, you won't have any trouble coding the SQL statements you need. Cl1apter 1 <?php $query= "SELECT vendor_name, invoice_number, invoice_total! ON vendors . vendor_ id = invoices.vendor_ id WHERE invoice_total >= 500 ORDER BY vendor_narne, invoice_total $dsn = 'mysql:host=localhost;
```
Example SQL query

**SQL Example 2:**
```sql
with totals over 500:</hl> <?php foreach ($rows as $row) : ?> <p> Vendor: <?php echo $row['vendor_ name'];
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Relational Algebra

**Definition:** CA 
NC 
CA 
CA 
Sacrament!> 
CA 
Fresno 
CA 
Mssion Viejo 
CA 
())cnard 
CA 
Mahe.Tl 
CA 
FortWashi...

### Explanation
Cliapter 2 
How to use MySQL Workbench and other develop,nent tools 
A SELECT statement and its results 
Create New 
SQL Tab button 
11 M 
orkbench 
/ wcat tns:tance MySQL.80 X 
Execute Current 
Statement button 
File 1 -1 V!e'N 
Query 
Database 
Saver 
T oals 
Sc · · no 
Help 
Query 1 
X 
SQL 
editor 
SCHEMAS 
~ I 
Fil~ ob]l!CIS 
,, J ap 
u .,,. l"'"'I 
Umil to 100(hows 
• I 1-9 I ~ Q. l1l ~ 
• 
Tables 
► Ell 9enual_led9l!l'_accounts 
► iJ invoice_archlve 
► El lnvoice_ll~_,t,ms 
► ii Invoices 
► 
terms 
► el ve.ndor_contacts 
" El vendors 
► t-1 Columns 
► 
Indexes 
► 
Foreigo Keys 
►~Triggers 
Vi~ 
'al Stored Procedures 
!?Ii Funrtlnn~ 
Adml11istrallon Sch~as 
ll'form.won 
Table: vendors 
Columns: 
vernlor ld 
vendor_name 
vendor _addressl 
vendor _address2 
vt'fldor -dty 
vendor _state 
...

lnl{I I) 
AlPK 
vard,a 
varcha 
varc:ha 
varcha 
diar(2 "' 
l • 
SELECT vendor_naee, vendor_city, vendor_state 
FR0'-1 vendors 
ORDER 8Y ve ndor_nam~ 
< 
vendor_name 
► 
Abbev 0~ F\lnlsmgs 
Amencan Booksde's Assoc 
American Elqlress 
ASC~ 
Ascom Hasler Maino Systems 
AT&T 
Aztekl.cbel 
Baker & Taylor Books 
Bertelsmam indus1Jy Svcs. Inc 
6fl tndUstrles 
Bil Jon6 
Bil Marvn Electnc Inc 
Blanchartf & Johnson Associates 
Bkietross 
Blue Shield of California 
Bouche,- Cwmncabons Inc 
earners Pub\shino ~v 
Cal State Termite 
vendor_dty 
Fresno 
Tarrytown 
vendor _state 
CA 
NY 
Los Angdes 
CA 
Fresno 
Sheltot'I 
Phoenix 
Anahesn 
Owtotte 
Valenoa 
Fresno 
CA 
CT 
A1.

CA 
NC 
CA 
CA 
Sacrament!> 
CA 
Fresno 
CA 
Mssion Viejo 
CA 
())cnard 
CA 
Mahe.Tl 
CA 
FortWashi... PA 
Tuel.ala! m 
Selma 
CA 
Fresno 
CA 
Result 
grid 
D 
X 
□ 
... "' 
Feld 
Tvi-
> 
ObJect Info 
Session 
Califumia Business Machines 
vendors 1 >< 
0 ReadOnly 
Description 
• 
To open a new SQL tab, press Ctrl+T or click the Create New SQL Tab button ( 
) 
in the SQL Editor toolbar. • 
To select the current database, double-click it in the Schemas tab of the Navigator 
window.

### Key Points
- CA 
NC 
CA 
CA 
Sacrament!> 
CA 
Fresno 
CA 
Mssion Viejo 
CA 
())cnard 
CA 
Mahe.Tl 
CA 
FortWashi...

### Examples
**SQL Example 1:**
```sql
SELECT vendor_natie, vcndor_city, vendor_strte fRc»1 vendors ORDER BY vendor name;
```
Example SQL query

**SQL Example 2:**
```sql
SELECT vendor_name, vendor_city FR<Y-1 vendors T Tables ► II gcneral_ledger_accounts ► 6J lnvoice_archlve ► invoiu_line_items l,lfERE vendor_id: ;
```
Example SQL query

**SQL Example 3:**
```sql
SELECT COUttT(*) AS number_of_invoices, SUM(invoice_total - payment_total - credit_total) AS total_due FRCJ1 invoices ► Invoice ► II terms i..HERE vendor id= ;
```
Example SQL query

**SQL Example 4:**
```sql
SELECT statement, the MySQL Command Line Client displays a message giving the nu1nber of rows that are included in the result set and the amount of time it took to run the query. In this case, it took less than 1/100 of a second to run the query. Cliapter 2 How to list the names of all databases managed by the server mysql> show databases;
```
Example SQL query

**SQL Example 5:**
```sql
select a database for use mysql> use ap;
```
Example SQL query

**SQL Example 6:**
```sql
select data from a database mysql> select vendor_name from vendors limit 5;
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Selection and Projection

**Definition:** If, for example, you have selected 
the EX database and you try to run a statement that refers to tables in the AP 
database, you will get an error.

### Explanation
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

### Key Points
- To fix the problem, you need to edit the SQL statement so the table is 
Vendors instead of Vendor.
- Then, you should be able to successfully run the SQL 
statement.
- This figure also lists some other common causes of errors.
- As you can see, 
most e1Tors are caused by incorrect syntax.

### Examples
**SQL Example 1:**
```sql
SELECT vendor_natie, vcndor_city, vendor_strte fRc»1 vendors ORDER BY vendor name;
```
Example SQL query

**SQL Example 2:**
```sql
SELECT vendor_name, vendor_city FR<Y-1 vendors T Tables ► II gcneral_ledger_accounts ► 6J lnvoice_archlve ► invoiu_line_items l,lfERE vendor_id: ;
```
Example SQL query

**SQL Example 3:**
```sql
SELECT COUttT(*) AS number_of_invoices, SUM(invoice_total - payment_total - credit_total) AS total_due FRCJ1 invoices ► Invoice ► II terms i..HERE vendor id= ;
```
Example SQL query

**SQL Example 4:**
```sql
SELECT statement, the MySQL Command Line Client displays a message giving the nu1nber of rows that are included in the result set and the amount of time it took to run the query. In this case, it took less than 1/100 of a second to run the query. Cliapter 2 How to list the names of all databases managed by the server mysql> show databases;
```
Example SQL query

**SQL Example 5:**
```sql
select a database for use mysql> use ap;
```
Example SQL query

**SQL Example 6:**
```sql
select data from a database mysql> select vendor_name from vendors limit 5;
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Set Operations in SQL

**Definition:** How to retrieve data 
from a single table 
In this chapter, you'll learn how to code SELECT statements that 1·etrieve data 
from a single table.

### Explanation
How to retrieve data 
from a single table 
In this chapter, you'll learn how to code SELECT statements that 1·etrieve data 
from a single table. The skills covered here are the essential ones that apply to 
any SELECT statement you code ... no matter how many tables it operates on, 
no matter how complex the retrieval. So you'll want to be sure you have a good 
understanding ot· the material in this chapter before you go on to the chapters 
that follow.

An introduction to the SELECT statement ........................ 74 
The basic syntax of the SELECT statement .................................................. 74 
SELECT statement examples ........................................................................ 76 
How to code the SELECT clause ........................................ 78 
How to code column specifications ...............................................................

78 
How to name the columns in a result set using aliases ................................. 80 
How to code arithmetic expressions .............................................................. 82 
How to use the CONCAT function to join strings ....................................... 84 
How to use functions with strings, dates, and n11mbers ................................ 86 
How to test expressions by coding statements without FROM clauses ........

### Key Points
- The skills covered here are the essential ones that apply to 
any SELECT statement you code ...
- no matter how many tables it operates on, 
no matter how complex the retrieval.
- So you'll want to be sure you have a good 
understanding ot· the material in this chapter before you go on to the chapters 
that follow.
- An introduction to the SELECT statement ........................
- 74 
The basic syntax of the SELECT statement ..................................................

### Examples
**SQL Example 1:**
```sql
SELECT statement that retrieves three columns from each row, sorted in descending sequence by invoice total SELECT invoice_number, invoice_date, invoice_ total FROM invoices ORDER BY invoice_total DESC invoice number invoice date invoice total -;
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Introduction to SQL

**Definition:** You use the AND operator to specify that the 
search must satisfy both of the conditions, and you use the OR operator to specify 
that the search must satisfy at least one of the conditions.

### Explanation
How to retrieve datafrom a single table 
The syntax of the WHERE clause with logical operators 
WHERE [NOT] search_condition_ l 
{ANDIOR} [NOT] search_ condition_ 2 
Examples of WHERE clauses that use logical operators 
The AND operator 
WHERE vendor_state = 'NJ' AND vendor_city = 'Springfield' 
The OR operator 
WHERE vendor_state = 'NJ' OR vendor_city = 'Pittsburg' 
The NOT operator 
WHERE NOT vendor_state = 'CA' 
The NOT operator in a complex search condition 
• • • 
WHERE NOT {invoice_ total >= 5000 OR NOT invoice_date <= '2018-08-01') 
The same condition rephrased to eliminate the NOT operator 
WHERE invoice_ total < 5000 AND invoice_date <= '2018-08-01' 
A compound condition without parentheses 
WHERE invoice_date > '2018-07-03' OR invoice_total > 500 
AND invoice_ total -
payment_total - credit_ total > O 
invoice_number 
invoice_date 
invoice_total 
balance_due 
► 
203339-13 
2018-07-05 
17.50 
0.00 
111-92R-10093 
2018-07-06 
39.n 
0,00 
2018-07-06 
111.00 
0.00 
{33 rows ) 
The same compound condition with parentheses 
WHERE (invoice_date > '2018-07-03' OR invoice_ total > 500) 
AND invoice_ total - payment_total - credit_total > 0 
~ 
invoice-:..number 
invoice_date 
invoice_total 
balance_due 
2018~7-10 
85.31 
85.31 
► 
2018-07-18 
52.25 
52.25 
2018-07-21 
579.42 
579.42 
{11 rows) 
Description 
• 
You can use the AND and OR logical operators to create compound conditions that 
consist of two or more conditions.

You use the AND operator to specify that the 
search must satisfy both of the conditions, and you use the OR operator to specify 
that the search must satisfy at least one of the conditions. • 
You can use the NOT operator to negate a condition. Because this can make the 
search condition unclear, you should rephrase the condition if possible so it doesn't 
use NOT. • 
When MySQL evaluates a compound condition, it evaluates the operators in this 
sequence: (1) NOT, (2) AND, and (3) OR.

You can use parentheses to override this 
order of precedence or to clarify the sequence in which the operations are evaluated. How to use the AND, OR, and NOT logical operators

An introduction to MySQL 
How to use the IN operator 
When you use this operator, the value of the test expression is compared with the 
list of expressions in the IN phrase. If the test expression is equal to one of the 
expressions in the list, the row is included in the query results.

### Key Points
- You use the AND operator to specify that the 
search must satisfy both of the conditions, and you use the OR operator to specify 
that the search must satisfy at least one of the conditions.
- • 
You can use the NOT operator to negate a condition.
- Because this can make the 
search condition unclear, you should rephrase the condition if possible so it doesn't 
use NOT.
- • 
When MySQL evaluates a compound condition, it evaluates the operators in this 
sequence: (1) NOT, (2) AND, and (3) OR.
- You can use parentheses to override this 
order of precedence or to clarify the sequence in which the operations are evaluated.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## SELECT Statement Basics

**Definition:** You use the AND operator to specify that the 
search must satisfy both of the conditions, and you use the OR operator to specify 
that the search must satisfy at least one of the conditions.

### Explanation
How to retrieve datafrom a single table 
The syntax of the WHERE clause with logical operators 
WHERE [NOT] search_condition_ l 
{ANDIOR} [NOT] search_ condition_ 2 
Examples of WHERE clauses that use logical operators 
The AND operator 
WHERE vendor_state = 'NJ' AND vendor_city = 'Springfield' 
The OR operator 
WHERE vendor_state = 'NJ' OR vendor_city = 'Pittsburg' 
The NOT operator 
WHERE NOT vendor_state = 'CA' 
The NOT operator in a complex search condition 
• • • 
WHERE NOT {invoice_ total >= 5000 OR NOT invoice_date <= '2018-08-01') 
The same condition rephrased to eliminate the NOT operator 
WHERE invoice_ total < 5000 AND invoice_date <= '2018-08-01' 
A compound condition without parentheses 
WHERE invoice_date > '2018-07-03' OR invoice_total > 500 
AND invoice_ total -
payment_total - credit_ total > O 
invoice_number 
invoice_date 
invoice_total 
balance_due 
► 
203339-13 
2018-07-05 
17.50 
0.00 
111-92R-10093 
2018-07-06 
39.n 
0,00 
2018-07-06 
111.00 
0.00 
{33 rows ) 
The same compound condition with parentheses 
WHERE (invoice_date > '2018-07-03' OR invoice_ total > 500) 
AND invoice_ total - payment_total - credit_total > 0 
~ 
invoice-:..number 
invoice_date 
invoice_total 
balance_due 
2018~7-10 
85.31 
85.31 
► 
2018-07-18 
52.25 
52.25 
2018-07-21 
579.42 
579.42 
{11 rows) 
Description 
• 
You can use the AND and OR logical operators to create compound conditions that 
consist of two or more conditions.

You use the AND operator to specify that the 
search must satisfy both of the conditions, and you use the OR operator to specify 
that the search must satisfy at least one of the conditions. • 
You can use the NOT operator to negate a condition. Because this can make the 
search condition unclear, you should rephrase the condition if possible so it doesn't 
use NOT. • 
When MySQL evaluates a compound condition, it evaluates the operators in this 
sequence: (1) NOT, (2) AND, and (3) OR.

You can use parentheses to override this 
order of precedence or to clarify the sequence in which the operations are evaluated. How to use the AND, OR, and NOT logical operators

An introduction to MySQL 
How to use the IN operator 
When you use this operator, the value of the test expression is compared with the 
list of expressions in the IN phrase. If the test expression is equal to one of the 
expressions in the list, the row is included in the query results.

### Key Points
- You use the AND operator to specify that the 
search must satisfy both of the conditions, and you use the OR operator to specify 
that the search must satisfy at least one of the conditions.
- • 
You can use the NOT operator to negate a condition.
- Because this can make the 
search condition unclear, you should rephrase the condition if possible so it doesn't 
use NOT.
- • 
When MySQL evaluates a compound condition, it evaluates the operators in this 
sequence: (1) NOT, (2) AND, and (3) OR.
- You can use parentheses to override this 
order of precedence or to clarify the sequence in which the operations are evaluated.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## WHERE Clause and Filtering

**Definition:** An introduction to MySQL 
How to use the LIKE and REGEXP operators 
To retrieve rows that match a specific string pattern, or mask, you can use 
the LIKE or REGEXP operators as shown in figure 3-14.

### Explanation
An introduction to MySQL 
How to use the LIKE and REGEXP operators 
To retrieve rows that match a specific string pattern, or mask, you can use 
the LIKE or REGEXP operators as shown in figure 3-14. The LIKE operator is 
an older operator that lets you search for simple string patterns. When you use 
this operator, the mask can contain one or both of the wildcard symbols shown 
in the first table in this figure.

In contrast to the LIKE operator, the REGEXP operator allows you to create 
complex string patterns known as regular expressions. To do that, you can use 
the special characters and constructs shown in the second table in this figure. Although creating regular expressions can be tricky at frrst, they allow you to 
search for virtually any string pattern. In the first example in this figure, the LIKE phrase specifies that all vendors 
in cities that start with the letters SAN should be included in the query results.

Here, the percent sign (%) indicates that any character or characters can follow 
these three letters. So San Diego and Santa Ana are both included in the results. The second example selects all vendors whose vendor name starts with the 
letters COMPU, followed by any one character, the letters ER, and any charac-
ters after that. The vendor names Compuserve and Computerworld both match 
that pattern.

### Key Points
- The LIKE operator is 
an older operator that lets you search for simple string patterns.
- When you use 
this operator, the mask can contain one or both of the wildcard symbols shown 
in the first table in this figure.
- In contrast to the LIKE operator, the REGEXP operator allows you to create 
complex string patterns known as regular expressions.
- To do that, you can use 
the special characters and constructs shown in the second table in this figure.
- Although creating regular expressions can be tricky at frrst, they allow you to 
search for virtually any string pattern.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## SQL Joins

**Definition:** An introduction to MySQL 
How to use compound join conditions 
Although a join condition typically consists of a single comparison, you can 
include two or more co1nparisons in a join condition using the AND and OR 
operators.

### Explanation
An introduction to MySQL 
How to use compound join conditions 
Although a join condition typically consists of a single comparison, you can 
include two or more co1nparisons in a join condition using the AND and OR 
operators. Figure 4-4 shows how this works. The query in tllis figure uses the AND operator to return the frrst and last 
names of all customers in the Customers table whose frrst and last names also 
exist in the Employees table.

Since Thomas Hardy is the only name that exists in 
both tables, this is the only row that's returned in the result set for this query. How to retrieve data from two or m.ore tables 
The Customers table 
rustomerJd 
rustomer _last_name 
rustomer _first_name 
customer _address 
rustomer _city 
rustomer _state "" 
► 
Anders 
Maria 
345WinchellPI 
Trujillo 
Ana 
1298 E Smathers St 
Moreno 
Antonio 
6925 N Parkland Ave 
Hardy 
Thomas 
83 d'Urberville Ln 
Berglund 
Christina 
22717E 73rd Ave 
Moos 
Hanna 
1778 N Bovine Ave 
Citeaux 
Fred 
1234Main St 
< 
(24 rows) 
The Employees table 
employeejd 
last_name 
first_name 
department_JlUJTiber 
managerJd 
► 
Smith 
Cindy 
2.

OOJ◄I 
Jones 
8mer 
Simonian 
Ralph 
2. Hernandez 
Olivia 
Aaronsen 
Robert 
2. Watson 
Denise 
Hardy 
Thomas 
(9 rows) 
An inner join with two conditions 
SELECT customer_first_ name, customer_ last_name 
FROM customers c JOIN employees e 
ON c.customer first name= e.first_ name 
AND c.customer_ last_name = e.last_name 
rustomer _first_name 
rustomer last name 
--+--
► 
Thomas 
Hardy 
(1 row) 
Description 
Anderson 
IN 
Benton 
AR 
Puyaftup 
'vVA 
Casterbridge 
GA 
Dubuque 
IA 
Peona 
IL 
Normal 
IL 
• 
A join condition can include two or more conditions connected by AND or OR 
operators.

### Key Points
- The query in tllis figure uses the AND operator to return the frrst and last 
names of all customers in the Customers table whose frrst and last names also 
exist in the Employees table.
- Since Thomas Hardy is the only name that exists in 
both tables, this is the only row that's returned in the result set for this query.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## INNER JOIN

**Definition:** An introduction to MySQL 
How to use compound join conditions 
Although a join condition typically consists of a single comparison, you can 
include two or more co1nparisons in a join condition using the AND and OR 
operators.

### Explanation
An introduction to MySQL 
How to use compound join conditions 
Although a join condition typically consists of a single comparison, you can 
include two or more co1nparisons in a join condition using the AND and OR 
operators. Figure 4-4 shows how this works. The query in tllis figure uses the AND operator to return the frrst and last 
names of all customers in the Customers table whose frrst and last names also 
exist in the Employees table.

Since Thomas Hardy is the only name that exists in 
both tables, this is the only row that's returned in the result set for this query. How to retrieve data from two or m.ore tables 
The Customers table 
rustomerJd 
rustomer _last_name 
rustomer _first_name 
customer _address 
rustomer _city 
rustomer _state "" 
► 
Anders 
Maria 
345WinchellPI 
Trujillo 
Ana 
1298 E Smathers St 
Moreno 
Antonio 
6925 N Parkland Ave 
Hardy 
Thomas 
83 d'Urberville Ln 
Berglund 
Christina 
22717E 73rd Ave 
Moos 
Hanna 
1778 N Bovine Ave 
Citeaux 
Fred 
1234Main St 
< 
(24 rows) 
The Employees table 
employeejd 
last_name 
first_name 
department_JlUJTiber 
managerJd 
► 
Smith 
Cindy 
2.

OOJ◄I 
Jones 
8mer 
Simonian 
Ralph 
2. Hernandez 
Olivia 
Aaronsen 
Robert 
2. Watson 
Denise 
Hardy 
Thomas 
(9 rows) 
An inner join with two conditions 
SELECT customer_first_ name, customer_ last_name 
FROM customers c JOIN employees e 
ON c.customer first name= e.first_ name 
AND c.customer_ last_name = e.last_name 
rustomer _first_name 
rustomer last name 
--+--
► 
Thomas 
Hardy 
(1 row) 
Description 
Anderson 
IN 
Benton 
AR 
Puyaftup 
'vVA 
Casterbridge 
GA 
Dubuque 
IA 
Peona 
IL 
Normal 
IL 
• 
A join condition can include two or more conditions connected by AND or OR 
operators.

### Key Points
- The query in tllis figure uses the AND operator to return the frrst and last 
names of all customers in the Customers table whose frrst and last names also 
exist in the Employees table.
- Since Thomas Hardy is the only name that exists in 
both tables, this is the only row that's returned in the result set for this query.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## OUTER JOIN

**Definition:** An introduction to MySQL 
How to work with outer joins 
Although inner joins are the most common type of join, MySQL also 
supports outer joins.

### Explanation
An introduction to MySQL 
How to work with outer joins 
Although inner joins are the most common type of join, MySQL also 
supports outer joins. Unlike an inner join, an outer join returns all of the rows 
from one of the tables involved in the join, regardless of whether the join condi-
tion is true. How to code an outer join 
sy.ntax is similar to the explicit syntax for inner joins, you shouldn't have any 
trouble understanding how it works.

The main difference is that you include the 
LEFT or RIGHT keyword to specify the type of outer join you want to perform. You can also include the OUTER keyword, but it's optional and is usually 
omitted. When you use a left outer join, the result set includes all the rows from 
the first, or left, table. Similarly, when you use a right outer join, the result set 
includes all the rows from the second, or right, table.

The example in this figure illustrates a left outer join. Here, the Vendors 
table is joined with the Invoices table. In addition, the result set includes vendor 
rows even if no matching invoices are found. In that case, null values are 
returned for the columns in the Invoices table. How to retrieve data f rom two or m.ore tables 
The explicit syntax for an outer join 
SELECT select_ list 
FROM table_ l 
{LEFTIRIGHT} [OUTER] JOIN table_ 2 
ON join_condition_ l 
[{LEFTIRIGHT} [OUTER] JOIN table_ 3 
ON join_condition_ 2] ...

### Key Points
- Unlike an inner join, an outer join returns all of the rows 
from one of the tables involved in the join, regardless of whether the join condi-
tion is true.
- How to code an outer join 
sy.ntax is similar to the explicit syntax for inner joins, you shouldn't have any 
trouble understanding how it works.
- The main difference is that you include the 
LEFT or RIGHT keyword to specify the type of outer join you want to perform.
- You can also include the OUTER keyword, but it's optional and is usually 
omitted.
- When you use a left outer join, the result set includes all the rows from 
the first, or left, table.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Aggregate Functions

**Definition:** • 
MySQL doesn't provide language keywords for full outer joins, but you can 
simulate a full outer join by using the UNION keyword to combine the result sets 
from a left outer join and a right outer join.

### Explanation
How to retrieve data from two or m.ore tables 
A union that simulates a full outer join 
SELECT department_name AS dept_name, d.department_ n11mber AS d_ dept_no, 
e.department_number AS e _dept_no, last_ name 
FROM departments d 
LEFT JOIN employees e 
ON d. department_number = e. department_ n11mber 
UNION 
SELECT department_ name AS dept_name, d.department_number AS d_ dept_ no, 
FROM departments d 
RIGHT JOIN employees e 
ORDER BY dept_name 
► 
dept_name 
Accounting 
Maintenance 
Operations 
Payroll 
Payroll 
Payroll 
I 
Personnel 
Personnel 
(10 rows ) 
Description 
d_dept_no 
ffi991 
e_dept_no 
last_name 
Watson 
locario 
Hernandez 
Hardy 
001!1 
lit!lil 
Smith 
Simonian 
Aaronsen 
Jones 
Oleary 
• 
When you use afull outer join, the result set includes all the 1·ows from both tables.

• 
MySQL doesn't provide language keywords for full outer joins, but you can 
simulate a full outer join by using the UNION keyword to combine the result sets 
from a left outer join and a right outer join. How to simulate a full outer join

An introduction to MySQL 
Perspective 
In this chapter, you learned a variety of techniques for combining data 
from two or more tables into a single result set.

In particular, you learned how 
to use the explicit syntax to code inner joins. Of all the techniques presented in 
this chapter, this is the one you'll use most often. So you'll want to be sure you 
understand it thorough! y before you go on. Terms 
• 
• 
JOin 
join condition 
• 
• 
• 
mner JOtn 
ad hoc relationship 
qualified column name 
explicit syntax 
SQL-92 syntax 
table alias 
schema 
self-join 
Exercises 
implicit syntax 
outer join 
left outer join 
right outer join 
• • 
• 
eqUIJOlll 
natural join 
• 
• 
cross JOtn 
Ca1tesian product 
• 
union 
full outer join 
1.

### Key Points
- How to simulate a full outer join

An introduction to MySQL 
Perspective 
In this chapter, you learned a variety of techniques for combining data 
from two or more tables into a single result set.
- In particular, you learned how 
to use the explicit syntax to code inner joins.

### Examples
**SQL Example 1:**
```sql
SELECT clause. Sort the final result set by the account_number column. 7. Use the UNION operator to generate a result set consisting of two columns from the Vendors table: vendor_name and vendor_state. If the vendor is in California, the vendor_state value should be ''CA'';
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## GROUP BY Clause

**Definition:** Then, the default value or null value is assigned automatically.

### Explanation
Clzapter 5 
How to insert, update, and delete data 
The column definitions for the Color_Sample table 
color_ id 
color_number 
color_name 
INT 
INT 
VARCHAR { 5 0) 
NOT NULL 
NOT NULL 
AUTO_ INCREMENT, 
DEFAULT O, 
Five INSERT statements for the Color_Sample table 
INSERT INTO color_ sample {color_number) 
VALUES {606) 
INSERT INTO color_ sample {color_ namA) 
VALUES {'Yellow') 
INSERT INTO color_ sample 
VALUES {DEFAULT, DEFAULT, 'Orange') 
INSERT INTO color_ sample 
VALUES (DEFAULT, 808, NULL) 
INSERT INTO color_ sample 
VALUES (DEFAULT, DEFAULT, NULL) 
The Color_Sample table after the rows have been inserted 
color Jd 
color _number 
color_name 
► 
UM!I 
Yellow 
Orange 
.q 
"®'' 
H®!I 
Description 
• If a column is defined so it allows null values, you can use the NULL keyword in 
the list of values to insert a null value into that column.

• 
If a column is defined with a default va]11e, you can use the DEFAULT keyword in 
the list of values to insert the default value for t11at column. • If a column is defined as an auto increment column, you can use the DEFAULT 
keyword in the list of values to have MySQL generate the value for the column. • If you include a column list, you can omit columns with default values and null 
values. Then, the default value or null value is assigned automatically.

You can also 
omit an auto increment column. Then, MySQL generates the value for the column. How to insert default values and null values

An introduction to MySQL 
How to use a subquery in an INSERT statement 
A subquery is just a SELECT statement that's coded within another SQL 
statement. Since you ah·eady know how to code SELECT statements, you 
shouldn't have much trouble coding subqueries as described in this chapter.

### Key Points
- • 
If a column is defined with a default va]11e, you can use the DEFAULT keyword in 
the list of values to insert the default value for t11at column.
- • If a column is defined as an auto increment column, you can use the DEFAULT 
keyword in the list of values to have MySQL generate the value for the column.
- • If you include a column list, you can omit columns with default values and null 
values.
- Then, the default value or null value is assigned automatically.
- You can also 
omit an auto increment column.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## HAVING Clause

**Definition:** • 
You specify the conditions that must be met for a row to be deleted in the WHERE 
clause.

### Explanation
The syntax of the DELETE statement 
DELETE FROM table_name 
[WHERE search_ condition] 
Delete one row 
DELETE FROM general_ledger_accounts 
WHERE account_ number = 306 
(1 row affected) 
Clzapter 5 
How to insert, update, and delete data 
Delete one row using a compound condition 
DELETE FROM invoice_ line_items 
WHERE invoice id= 78 AND invoice_ sequence = 2 
(1 row affected) 
Delete multiple rows 
DELETE FROM invoice_line_ items 
WHERE invoice id= 12 
(4 rows affected) 
Use a subquery in a DELETE statement 
WHERE invoice_ id IN 
(SELECT invoice_ id 
FROM invoices 
WHERE vendor id= 115) 
(4 rows affected) 
Description 
• 
You can use the DELETE statement to delete one or more rows from the table you 
name in the DELETE clause.

• 
You specify the conditions that must be met for a row to be deleted in the WHERE 
clause. • 
You can use a subquery within the WHERE clause. • 
A foreign key constraint may prevent you from deleting a row. In that case, you can 
only delete the row if you delete all child rows for that row first. • 
By default, MySQL Workbench runs in safe update mode. That prevents you from 
deleting rows if the WHERE clause is omitted or doesn't refer to a primary key or 
foreign key column.

For information on turning safe update mode off, see figure 
5-5. Warning 
• 
If you tum safe update mode off and omit th.e WHERE clause from a DELETE 
statement, all the rows in the table will be deleted. How to delete rows

An introduction to MySQL 
Perspective 
In this chapter, you learned how to use the INSERT, UPDATE, and 
DELETE statements to modify the data in a database. In chapters 10 and 11, 
you'll learn more about how table definitions can affect the way these state-
ments work.

### Key Points
- • 
You specify the conditions that must be met for a row to be deleted in the WHERE 
clause.
- • 
You can use a subquery within the WHERE clause.
- • 
A foreign key constraint may prevent you from deleting a row.
- In that case, you can 
only delete the row if you delete all child rows for that row first.
- • 
By default, MySQL Workbench runs in safe update mode.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Subqueries

**Definition:** To include two or more columns or expressions, separate them by commas.

### Explanation
How to code sum1ncary queries 
The syntax of a SELECT statement with GROUP BY and HAVING clauses 
SELECT select_list 
FROM table_ source 
[WHERE search_ condition] 
[GROUP BY group_by_ list] 
[HAVING search_condition] 
[ORDER BY order_by_ list] 
A summary query that calculates the average invoice amount by vendor 
SELECT vendor_ id, ROUND(AVG(invoice_total), 2) AS average_ invoice_amount 
FROM invoices 
GROUP BY vendor_ id 
HAVING AVG(invoice_total) > 2000 
ORDER BY average_ invoice_amount DESC 
vendor id 
average_lnvoice_amount 
► 
23978.48 
10963.66 
7125.34 
6940.25 
4901.26 
2575.33 
2433.00 
2184.50 
(8 rows) 
A summary query that includes a functionally dependent column 
SELECT vendor_ name, ~endor_ state, 
ROUND(AVG(invoice_total), 2) AS average_ invoice_amount 
FROM vendors JOIN invoices ON vendors.vendor_ id = invoices.vendor_ id 
GROUP BY vendor_narn~ 
HAVING AVG(invoice total) > 2000 
Description 
• 
The GROUP BY clause groups the rows of a result set based on one or more columns or 
expressions.

To include two or more columns or expressions, separate them by commas. • If you include aggregate functions in the SELECT clause, the aggregate is calculated for 
each group specified by the GROUP BY clause. • If you include two or more colu1nns or expressions in the GROUP BY clause, they form 
a hierarchy where each column or expression is subordinate to the previous one. • 
The HAVING clause specifies a search condition for a group or an aggregate.

MySQL 
applies this condition after it groups the rows that satisfy the search condition in the 
WHERE clause. • 
When a SELECT statement includes a GROUP BY clause, the SELECT clause can 
include the columns used for grouping, aggregate functions, and expressions that 
result in a constant value. • 
The SELECT clause can also include columns that are functionally dependent on a 
column used fo1· grouping.

### Key Points
- To include two or more columns or expressions, separate them by commas.
- • If you include aggregate functions in the SELECT clause, the aggregate is calculated for 
each group specified by the GROUP BY clause.
- • If you include two or more colu1nns or expressions in the GROUP BY clause, they form 
a hierarchy where each column or expression is subordinate to the previous one.
- • 
The HAVING clause specifies a search condition for a group or an aggregate.
- MySQL 
applies this condition after it groups the rows that satisfy the search condition in the 
WHERE clause.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Correlated Subqueries

**Definition:** How to use the GROUPING function (part 1 of 2)

More SQL skills cts you need them 
Part 2 of figure 6-8 shows another common use for the GROUPING 
function.

### Explanation
How to code sum1ncary queries 
The basic syntax of the GROUPING function 
GROUPING (expression) 
A summary query that uses WITH ROLLUP on a table with null values 
SELECT invoice_date, payment_date, 
SUM(invoice_total) AS invoice_total, 
SUM(invoice_total - credit_total - payment_total) AS balance_due 
FROM invoices 
WHERE invoice_date BETWEEN '2018-07-24' AND 
1 2018-07-31 1 
GROUP BY invoice_date, payment_date WITH ROLLUP 
invoice_date 
payment_date 
Invoice_ total 
balance_ due 
► 
2018-07-24 
0®91 
503.20 
503.20 
2018-07-24 
2018-08-19 
3689.99 
0.00 
2018-07-24 
2018-08-23 
67.00 
0.00 
2018-07-24 
2018-08-27 
23517.58 
0.00 
2018-07-24 
HPJII 
27777.n 
503.20 
2018-07-25 
2018-08-22 
1000.'16 
0,00 
2018-07-25 
l®!I 
1000.-46 
0.00 
2018-07-28 
UQl!I 
90.36 
90.36 
2018-07-28 
HW!I 
90.36 
90.36 
2018-07-30 
2018-09-03 
22.57 
0.00 
2018--0 7-30 
®J!I 
22.57 
o.oo 
2018-07-31 
lllij!i 
10976.06 
10976.06 
~&,;8-07-31 
il®!I 
10976.06 
10976.06 
HW!I 
39867.22 
11569.62 
A query that substitutes literals for nulls in summary rows 
SELECT IF(GROUPI:NG(invoice_ date) = 1 , 'Grand totals', invoice_ date) 
AS invoice_date, 
IF(GROUPI:NG(payment_ date) = 1 , 'Invoice date totals', payment_ date) 
AS payme.nt_date, 
SUM(invoice_total - credit_total - payment_ total) AS balance_ due 
FROM invoices 
1 2018-07-31 1 
J 
invoice_date 
payment_date 
Invoice_ total 
balance _due 
H©il 
► 
2018-07-24 
503.20 
503.20 
2018-07-24 
2018-08-19 
3689.99 
0.00 
2018-07-24 
2018-08-23 
67.00 
o.oo 
2018-07-24 
2018-08-27 
23517.58 
0.00 
2018-07-24 
Invoice date totals 
L777/.77 
503.20 
2018-07-25 
2018-08-22 
1000.-46 
0.00 
2018-07-25 
Invoice date totals 
1000.-46 
0.00 
2018-07-28 
llill!I 
90.36 
90.36 
2018-07-28 
Invoice date totals 
90.36 
90.36 
2018-07-30 
2018-09-03 
22.57 
0.00 
2018-07-30 
Invoice date totals 
22.57 
0.00 
2018-07-31 
Ut!HI 
10976.06 
10976.06 
2018-07-31 
Invoice date totals 
10976.06 
10976.06 
Grand totals 
Invoice date totals 
39867.22 
11569.62 
Description 
• 
The GROUPING function returns 1 if the expression is null because it's in a 
summary row.

Otherwise, it returns 0. How to use the GROUPING function (part 1 of 2)

More SQL skills cts you need them 
Part 2 of figure 6-8 shows another common use for the GROUPING 
function. The query in this example is identical to the second one in part 1 
of this figure, except that it includes a HAVING clause. This clause uses the 
GROUPING function to filter the result set so only the summary rows are 
included.

To do that, it checks if this function returns a value of 1 for the 
invoice_date or payment_date column. How to code sum1n.ary queries 
A query that displays only summary rows 
SELECT IF(GROUPING(invoice_date) = l , 'Grand totals', invoice_date) 
AS invoice_date, 
IF(GROUPING (payment_date) = l , 'Invoice date totals', payment_date) 
AS payment_date, 
SUM(invoice_ total - credit_ total - payment_total) AS balance_due 
FROM invoices 
WHERE invoice_date BETWEEN '2018-07-24' AND '2018-07- 31' 
HAVING GROUPING(invoice date) = 1 OR GROUPING{payment date)
= ~ 
• 
invoice _date 
payment_date 
invoice_total 
balance_due 
► 
2018-07-24 
Invoice date totals 
l.7111.

### Key Points
- How to use the GROUPING function (part 1 of 2)

More SQL skills cts you need them 
Part 2 of figure 6-8 shows another common use for the GROUPING 
function.
- The query in this example is identical to the second one in part 1 
of this figure, except that it includes a HAVING clause.
- This clause uses the 
GROUPING function to filter the result set so only the summary rows are 
included.
- To do that, it checks if this function returns a value of 1 for the 
invoice_date or payment_date column.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## CREATE TABLE

**Definition:** In most cases, that means that it uses an aggregate 
function.

### Explanation
How to l·ode subqueries 
The syntax of a WHERE clause that uses an IN phrase 
WHERE test_expression [NOT] IN (subquery) 
Get vendors without invoices 
SELECT vendor_ id, vendor_name, vendor_state 
FROM vendors 
WHERE vendor_ id NOT IN 
(SELECT DISTINCT vendor_ id 
FROM invoic es ) 
ORDER BY vendor id 
The result of the subquery 
vendor_id 
► 
'18 
(34 rows) 
The result set 
vendor jd 
vendor _name 
Nielson 
Cal State Termite 
Graylift 
Venture Communications Int'I 
Custom Printing Company 
I 
tlO 
Nat Assoc of College Stores 
(88 rows) 
vendor _state 
OH 
CA 
CA 
NY 
MO 
OH 
The query restated without a subquery 
SELECT v .vendor_ id, vendor_ name, vendor_ state 
FROM vendors v LEFT JOIN invoices i 
ON v .

vendor_ id = i .vendor_ id 
WHERE i.vendor_ id IS NULL 
ORDER BY v .vendor_ id 
Description 
• 
You can introduce a subquery with the IN operator to provide the list of values that 
are tested against the test expression. • 
When you use the IN operator, the subquery must return a single column of values. • 
A query that uses the NOT IN operator with a subquery can typically be restated 
using an outer join.

How to use the IN operator

More SQL skills cts you need them 
How to use the comparison operators 
expression with the result of a subquery. In this example, the subquery returns 
the average balance due of the invoices in the Invoices table that have a balance 
due greater than zero. Then, it uses that value to retrieve all invoices with a 
balance due that's less than the average. When you use a compaiison operator as shown in this figure, the subquery 
must return a single value.

### Key Points
- • 
When you use the IN operator, the subquery must return a single column of values.
- • 
A query that uses the NOT IN operator with a subquery can typically be restated 
using an outer join.
- How to use the IN operator

More SQL skills cts you need them 
How to use the comparison operators 
expression with the result of a subquery.
- In this example, the subquery returns 
the average balance due of the invoices in the Invoices table that have a balance 
due greater than zero.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## SQL Data Types

**Definition:** More SQL skills cts you need them 
How to use the ALL keyword 
operator so the condition must be true for all the values returned by a subquery.

### Explanation
More SQL skills cts you need them 
How to use the ALL keyword 
operator so the condition must be true for all the values returned by a subquery. The table at the top of this figure shows how this works. Here, the values in 
parentheses 1·epresent the values returned by the query. If you use the greater than operator(>), the expression must be greater than 
the maximum value returned by the subquery.

Conversely, if you use the less 
than operator ( < ), the expression must be less than the minimum value returned 
by the subquery. If you use the equal operator ( = ), all of the values returned by 
the subquery must be the same and the expression must be equal to that value. And if you use the not equal operator ( <>), the expression must not equal any 
of the values returned by the subquery. However, a not equal condition can be 
restated using the NOT IN operator, which is easier to read.

As a result, it's a 
better practice to use the NOT IN operator for this type of condition. The query in this figure shows how to use the greater than operator with the 
ALL keyword. Here, the subquery selects the invoice_total column for all the 
invoices with a vendor_id value of 34. This results in a list of two values. Then, 
the main query retrieves the rows from the Invoices table that have invoice totals 
greater than both of the values returned by the subquery.

### Key Points
- The table at the top of this figure shows how this works.
- Here, the values in 
parentheses 1·epresent the values returned by the query.
- If you use the greater than operator(>), the expression must be greater than 
the maximum value returned by the subquery.
- Conversely, if you use the less 
than operator ( < ), the expression must be less than the minimum value returned 
by the subquery.
- If you use the equal operator ( = ), all of the values returned by 
the subquery must be the same and the expression must be equal to that value.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Integrity Constraints

**Definition:** • 
You can use the NOT EXISTS operator to test that no rows are returned by the 
subquery.

### Explanation
How to l·ode subqueries 
The syntax of a subquery that uses the EXISTS operator 
WHERE [NOT] EXISTS (subquery) 
Get all vendors that don't have invoices 
SELECT vendor id, vendor_ name, vendor_state 
FROM vendors 
WHERE NOT EXISTS 
(SELECT* 
FROM invoices 
WHERE vendor_ id = vendors.vendor_ id) 
The result set 
vendor jd 
vendor _name 
-33 
39 I 
'10 
(88 rows ) 
Description 
Nielson 
Cal State Termite 
Grayfift 
Venture Communications Int'I 
Custom Printing Company 
Nat Assoc of CoUege Stores 
vendor _state 
OH 
CA 
CA 
NY 
MO 
OH 
• 
You can use the EXISTS operator to test that one or more rows are returned by the 
subquery.

• 
You can use the NOT EXISTS operator to test that no rows are returned by the 
subquery. • 
When you use these operators with a subquery, it doesn't matter what columns you 
specify in the SELECT clause. As a result, you typically just code an asterisk ( * ). How to use the EXISTS operator 
More SQL skills cts you need them 
How to code subqueries 
in other clauses 
Now that you know how to code subqueries in the WHERE clause of a 
SELECT statement, you're ready to learn how to code them in the HAVING, 
FROM, and SELECT clauses.

How to code subqueries in the HAVING clause 
When you code a HA YING clause, you specify a search condition just as 
you do when you code a WHERE clause. That includes search conditions that 
contain subqueries. To learn how to code subqueries in a HAVING clause, then, 
you can refer back to figures 7-3 through 7-8. How to code subqueries in the SELECT clause 
that, you code the subquery in place of a column specification.

### Key Points
- • 
You can use the NOT EXISTS operator to test that no rows are returned by the 
subquery.
- • 
When you use these operators with a subquery, it doesn't matter what columns you 
specify in the SELECT clause.
- As a result, you typically just code an asterisk ( * ).
- How to code subqueries in the HAVING clause 
When you code a HA YING clause, you specify a search condition just as 
you do when you code a WHERE clause.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Primary Key Constraint

**Definition:** • 
You can use the NOT EXISTS operator to test that no rows are returned by the 
subquery.

### Explanation
How to l·ode subqueries 
The syntax of a subquery that uses the EXISTS operator 
WHERE [NOT] EXISTS (subquery) 
Get all vendors that don't have invoices 
SELECT vendor id, vendor_ name, vendor_state 
FROM vendors 
WHERE NOT EXISTS 
(SELECT* 
FROM invoices 
WHERE vendor_ id = vendors.vendor_ id) 
The result set 
vendor jd 
vendor _name 
-33 
39 I 
'10 
(88 rows ) 
Description 
Nielson 
Cal State Termite 
Grayfift 
Venture Communications Int'I 
Custom Printing Company 
Nat Assoc of CoUege Stores 
vendor _state 
OH 
CA 
CA 
NY 
MO 
OH 
• 
You can use the EXISTS operator to test that one or more rows are returned by the 
subquery.

• 
You can use the NOT EXISTS operator to test that no rows are returned by the 
subquery. • 
When you use these operators with a subquery, it doesn't matter what columns you 
specify in the SELECT clause. As a result, you typically just code an asterisk ( * ). How to use the EXISTS operator 
More SQL skills cts you need them 
How to code subqueries 
in other clauses 
Now that you know how to code subqueries in the WHERE clause of a 
SELECT statement, you're ready to learn how to code them in the HAVING, 
FROM, and SELECT clauses.

How to code subqueries in the HAVING clause 
When you code a HA YING clause, you specify a search condition just as 
you do when you code a WHERE clause. That includes search conditions that 
contain subqueries. To learn how to code subqueries in a HAVING clause, then, 
you can refer back to figures 7-3 through 7-8. How to code subqueries in the SELECT clause 
that, you code the subquery in place of a column specification.

### Key Points
- • 
You can use the NOT EXISTS operator to test that no rows are returned by the 
subquery.
- • 
When you use these operators with a subquery, it doesn't matter what columns you 
specify in the SELECT clause.
- As a result, you typically just code an asterisk ( * ).
- How to code subqueries in the HAVING clause 
When you code a HA YING clause, you specify a search condition just as 
you do when you code a WHERE clause.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Foreign Key Constraint

**Definition:** The seco11d subquery is also used in the FROM clause of the outer query to 
create a result set that's joined with the first result set.

### Explanation
More SQL skills cts you need them 
How to work with complex queries 
So far, the examples you've seen of queries that use subqueries have been 
relatively simple. However, these types of queries can get complicated in a hurry, 
particularly if the subqueries are nested. Because of that, you'll want to be st1re 
that you plan and test these queries carefully. In a moment, you'll learn how to 
do that.

But first, this chapter presents an example of a complex query. A complex query that uses subqueries 
subquery is used in the FROM clause of the outer query to create a result set that 
contains the state, name, and total invoice amount for each vendor in the Vendors 
table. This is the same subquery that was described in figure 7-10. As a result, 
you should already understand how it works. The seco11d subquery is also used in the FROM clause of the outer query to 
create a result set that's joined with the first result set.

This result set contains 
the state and total invoice amount for the vendor in each state that has the largest 
invoice total. To create this result set, a third subquery is nested within the 
FROM clause of the subquery. This subquery is identical to the frrst subquery. After this statement creates the two result sets, it joins them based on the 
columns in each table that contain the state and the total invoice amount.

### Key Points
- However, these types of queries can get complicated in a hurry, 
particularly if the subqueries are nested.
- Because of that, you'll want to be st1re 
that you plan and test these queries carefully.
- In a moment, you'll learn how to 
do that.
- But first, this chapter presents an example of a complex query.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## INSERT Statement

**Definition:** More SQL skills cts you need them 
The date and time types 
Part 1 of figure 8-5 presents the five date and time types supported by 
MySQL.

### Explanation
More SQL skills cts you need them 
The date and time types 
Part 1 of figure 8-5 presents the five date and time types supported by 
MySQL. You can use the DATE type to store a date without a time. You can 
use the TIME type to store a time without a date. And you can use either the 
DATETIME or TIMESTAMP types to store both a date and a time. You typically use the TIMESTAMP type to keep track of when a row was 
inserted or last updated.

For example, you might use this type to keep track 
of the entries on a blog. MySQL makes that easy by automatically setting the 
TIMESTAMP column to the current date and time whenever a row is inserted or 
updated. If that's not what you want, you can use the DATETIME type instead. The problem with the TIMESTAMP type is that it can only store dates up 
to the year 2038. This is known as the yea,-2038 problem, the Y2K38 probleni, 
and the Unix Millennium bug.

As a result, if you want your database to be able 
to store dates that go beyond 2038, you should use the DATETIME type instead 
of the TIMESTAMP type. Otherwise, you can use the TIMESTAMP type since 
it only reqtrires 4 bytes to store a TIMESTAMP value, compared to 8 bytes for a 
DATETIME value. If you need to store a year without any other temporal data, you can use the 
YEAR type. With MySQL 5.7.5 and later, the YEAR type stores 4-digit years 
from 1901 to 2155.

### Key Points
- You can use the DATE type to store a date without a time.
- You can 
use the TIME type to store a time without a date.
- And you can use either the 
DATETIME or TIMESTAMP types to store both a date and a time.
- You typically use the TIMESTAMP type to keep track of when a row was 
inserted or last updated.
- For example, you might use this type to keep track 
of the entries on a blog.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## UPDATE Statement

**Definition:** More SQL skills cts you need them 
How to convert data 
As you work with the various data types, you'll find that you frequently 
need to convert data from one type to another.

### Explanation
More SQL skills cts you need them 
How to convert data 
As you work with the various data types, you'll find that you frequently 
need to convert data from one type to another. Although MySQL performs many 
conversions automatically, it doesn't always perform the conversion the way you 
want. Because of that, you need to be aware of how data conversion works, and 
you need to know when and how to specify the type of conversion you want.

How implicit data conversion works 
Before MySQL can operate on two values, it must convert those values to 
the same data type. To understand how this works, consider the three expressions 
shown in figu.re 8-8. In the first example, the second column joins a string literal of''$'' to the 
invoice_total column, which is defined with the DECIMAL type. As a result, 
MySQL converts the DECIMAL value to its corresponding characters, appends 
those characters to the $ character, and stores them as a CHAR type.

In the second example, the second column divides the INT literal of 989319 
by the VARCHAR type that's stored in the invoice_number column. As a result, 
MySQL attempts to convert the invoice_number column to an INT type before 
it perfor1ns the division operation. If the invoice_number column contains only 
numbers, this works as you would expect. However, if the invoice_number 
column contains letters or special characters, MySQL converts only the numeric 
characters that precede the letters or special characters.

### Key Points
- Although MySQL performs many 
conversions automatically, it doesn't always perform the conversion the way you 
want.
- Because of that, you need to be aware of how data conversion works, and 
you need to know when and how to specify the type of conversion you want.
- How implicit data conversion works 
Before MySQL can operate on two values, it must convert those values to 
the same data type.
- To understand how this works, consider the three expressions 
shown in figu.re 8-8.
- In the first example, the second column joins a string literal of''$'' to the 
invoice_total column, which is defined with the DECIMAL type.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## DELETE Statement

**Definition:** Clzapter 8 
How to work with data types 
Exercises 
1.

### Explanation
Clzapter 8 
How to work with data types 
Exercises 
1. Write a SELECT statement that returns these columns from the Invoices 
table: 
The invoice total column 
A column that t1ses the FORMAT function to return the invoice total 
column with 1 digit to the right of the decimal point 
A column that uses the CONVERT function to return the invoice total 
column as an integer 
A column that uses the CAST function to return the invoice total column 
as an integer 
2.

table: 
The invoice date column 
with its full date and time 
with just the year and the month

How to use functions 
In chapter 3, you we1·e introduced to some of the scalar functions that you 
can use in a SELECT statement. Now, this chapter expands on that coverage 
by presenting many more of the scalru: functions, as well as some specialized 
window functions. When you complete this chapter, you'll have a thorough 
understanding of the functions that you can use with MySQL.

How to work with string data ............................................. 258 
A sut11mary of the string functions .............................................................. 258 
Examples that use string functions ............................................................. 260 
How to sort by a string column that contains numbers ............................... 262 
How to parse a string ..................................................................................

### Key Points
- Now, this chapter expands on that coverage 
by presenting many more of the scalru: functions, as well as some specialized 
window functions.
- When you complete this chapter, you'll have a thorough 
understanding of the functions that you can use with MySQL.
- How to work with string data .............................................

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## SQL Views

**Definition:** How to use functions 
The EXTRACT function 
Function 
Description 
EXTRACT{unit FROM date) 
Returns an integer that corresponds with the 
specified unit for the specified date/time.

### Explanation
How to use functions 
The EXTRACT function 
Function 
Description 
EXTRACT{unit FROM date) 
Returns an integer that corresponds with the 
specified unit for the specified date/time. Date/time units 
Unit 
Description 
SECOND 
MINUTE 
HOUR 
DAY 
MONTH 
YEAR 
MINUTE_ SECOND 
HOUR_ Ml:NUTE 
DAY_ HOUR 
YEAR_ MONTH 
HOUR_ SECOND 
DAY_ MINUTE 
DAY_ SECOND 
Seconds 
Minutes 
Hours 
Day 
Month 
Year 
Minutes and seconds 
Hour and minutes 
Day and hours 
Year and mo11th 
Hours, min·utes, and seconds 
Day, hours, and minutes 
Day, hours, minutes, and seconds 
Examples that use the EXTRACT function 
Function 
Result 
EXTRACT{SECOND FROM '2018-12-03 11:35:00') 
EXTRACT(MINUTE FROM '2018-12-03 11:35:00') 
EXTRACT(HOUR FROM '2018-12-03 11:35:00') 
EXTRACT(DAY FROM '2018-12-03 11:35:00') 
EXTRACT(MONTH FROM ' 2018-12-03 11:35:00') 
EXTRACT(YEAR FROM '2018-12-03 11:35:00') 
EXTRACT(MINUTE_ SECOND FROM '2018-12-03 11:35:00') 
EXTRACT(HOUR_ Ml:NUTE FROM '2018-12-03 11:35:00' ) 
EXTRACT(DAY_ HOUR FROM '2018-12-03 11:35:00') 
EXTRACT(YEAR_ MONTH FROM '2018-12-03 11:35:00' ) 
EXTRACT(HOUR_ SECOND FROM '2018-12-03 11:35:00') 
EXTRACT(DAY_ MINUTE FROM '2018-12-03 11:35:00') 
EXTRACT(DAY_ SECOND FROM '2018-12-03 11:35:00') 
How to parse dates and times with the EXTRACT function

More SQL skills cts you need them 
How to format dates and times 
and times.

This function accepts two parameters. The first parameter speci-
fies the DATE or DATETIME value that you want to format. Then, the second 
parameter specifies a format string that includes special codes for formatting 
the various parts of the date or time. To use one of these codes within the format 
string, you code the percent sign (%) followed by a single case-sensitive letter. In this figure, for instance, the frrst example uses the %m code to get the 
numeric month, the %d code to get the nume1ic day, and the %y code to get the 
two-digit year.

This example also uses front slashes (/) to separate the month, 
day, and year. The next three examples use other formatting codes, but they work similarly 
to the frrst example. Namely, the for1nat string contains some date/time format-
ting codes to display the different parts of the date. In addition, it contains other 
characters such as spaces, commas, or dashes to separate the different parts of 
the date.

### Key Points
- The first parameter speci-
fies the DATE or DATETIME value that you want to format.
- Then, the second 
parameter specifies a format string that includes special codes for formatting 
the various parts of the date or time.
- To use one of these codes within the format 
string, you code the percent sign (%) followed by a single case-sensitive letter.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Database Normalization

**Definition:** How to design a database 
In this chapter, you'll learn how to design a new database.

### Explanation
How to design a database 
In this chapter, you'll learn how to design a new database. This is useful 
information whether or not you ever design a database on your own. To illus-
trate this process, I'll use the accounts payable (AP) database that you've seen 
throughout this book. How to design a data structure ......................................... 306 
The basic steps for designing a data structure ............................................

306 
How to identify the data elements .............................................................. 308 
How to subdivide the data elements ............................................................ 310 
How to identify the tables and assign columns ........................................... 312 
How to identify the primary and foreign keys ............................................ 314 
How to enforce the relationships between tables ........................................

316 
How nor1nal·ization works ........................................................................... 318 
How to identify the columns to be indexed ................................................. 320 
How to normalize a data structure .................................... 322 
The seven normal forms .............................................................................. 322 
How to apply the first normal form .............................................................

### Key Points
- This is useful 
information whether or not you ever design a database on your own.
- To illus-
trate this process, I'll use the accounts payable (AP) database that you've seen 
throughout this book.
- How to design a data structure .........................................
- 306 
The basic steps for designing a data structure ............................................
- 306 
How to identify the data elements ..............................................................

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## First Normal Form (1NF)

**Definition:** Database design and impleme11,tation, 
How to identify the data elements 
The first step for designing a data structure is to identify the data elements 
required by the system.

### Explanation
Database design and impleme11,tation, 
How to identify the data elements 
The first step for designing a data structure is to identify the data elements 
required by the system. You can use several techniques to do that, including 
analyzing the existing system if there is one, evaluating comparable systems, and 
interviewing anyone who will be using the system. One particularly good source 
of information is the documents used by an existing system.

In figure 10-2, for example, you can see an invoice that's used by an 
accounts payable system. We'll use this document as the main source of infor-
mation for the database design presented in this chapte1·. Keep in mind, though, 
that you'll want to use all available resources when you design your own 
database. If you study this document, you' 11 notice that it contains information about 
three different entities: vendors, invoices, and line items.

First, the form itself 
has preprinted info1mation about the vendor who issued the invoice, such as the 
vendor's name and address. If this vendor were to issue another invoice, this 
information wouldn't change. This document also contains specific information about the invoice. Some 
of this information, such as the invoice number, invoice date, and invoice total, 
is general in nature. Although the actL1al information will vary from one invoice 
to the next, each invoice will include this information.

### Key Points
- You can use several techniques to do that, including 
analyzing the existing system if there is one, evaluating comparable systems, and 
interviewing anyone who will be using the system.
- One particularly good source 
of information is the documents used by an existing system.
- In figure 10-2, for example, you can see an invoice that's used by an 
accounts payable system.
- We'll use this document as the main source of infor-
mation for the database design presented in this chapte1·.
- Keep in mind, though, 
that you'll want to use all available resources when you design your own 
database.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Second Normal Form (2NF)

**Definition:** If possible, 
you should use an existing column for the primary key.

### Explanation
Hovv to design a database 
The relationships between the tables in the accounts payable system 
vendors 
• 
• 
1nvo1ces 
invoice line items 
vendor id 
invoice id 
••----
◄ invoice id 
vendor name 
vendor address 
vendor_ city 
vendor state 
vendor_zip_code 
vendor_phone 
vendor contact first name 
vendor contact last name 
terms 
account no 
i.-..a vendor id 
invoice number 
invoice date 
invoice total 
payment_total 
credit total 
terms 
invoice due date 
payment_date 
account no 
Two tables with a many-to-many relationship 
employees 
memberships 
committees 
.

. 1nvo1ce_sequence 
account no 
line _item_ description 
item_quantity 
item_ unit_price 
line item amount 
employee_id ••----
◄ employee_id 
first name 
committee id 
committee id 
committee name 
last name 
Linking table 
Two tables with a one-to-one relationship 
employees 
employee _photos 
employee_id ••--• employee_id 
first_name 
employee_photo 
last name 
Description 
• 
Each table should have a primary key that uniquely identifies each row.

If possible, 
you should use an existing column for the primary key. • 
The values of the primary keys should seldom, if ever, change. The values should 
also be short and easy to enter correctly. • If a suitable column doesn't exist for a p1imary key, you can create an ID column 
that is incremented by one for each new row as the primary key. • If two tables have a one-to-many relationship, you may need to add a foreign key 
column to the table on the ''many'' side.

### Key Points
- If possible, 
you should use an existing column for the primary key.
- • 
The values of the primary keys should seldom, if ever, change.
- The values should 
also be short and easy to enter correctly.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Third Normal Form (3NF)

**Definition:** Database design and impleme11,tation, 
How to nor111alize a data structure 
The topics that follow describe the seven normal forms and teach you how to 
apply the first three.

### Explanation
Database design and impleme11,tation, 
How to nor111alize a data structure 
The topics that follow describe the seven normal forms and teach you how to 
apply the first three. As I said earlier, you apply these three forms to some extent 
in the first four database design steps, but these topics will give you more insight 
into the process. Then, the last topic explains when and how to denormalize 
a data structure.

When you finish these topics, you' 11 have the basic skills for 
designing databases that are efficient and easy to use. The seven normal forms 
that the previous forms have already been applied. Before you can apply the 
third normal form, for example, the design must already be in the second normal 
form. Strictly speaking, a data structure isn't normalized until it's in the fifth or 
sixth normal form.

However, the normal forms past the third normal form are 
applied infrequently. Because of that, I won't present those forms in detail here. Instead, I'll just describe them briefly so you'll have an idea of how to apply 
them if you need to. The Boyce-Codd normal form can be used to eliminate transitive 
dependencies. With this type of dependency, one column depends on another 
column, which depends on a third coltunn.

### Key Points
- As I said earlier, you apply these three forms to some extent 
in the first four database design steps, but these topics will give you more insight 
into the process.
- Then, the last topic explains when and how to denormalize 
a data structure.
- When you finish these topics, you' 11 have the basic skills for 
designing databases that are efficient and easy to use.
- The seven normal forms 
that the previous forms have already been applied.
- Before you can apply the 
third normal form, for example, the design must already be in the second normal 
form.

### Examples
**SQL Example 1:**
```sql
create a model from that script. To do that, you can click the 0 icon to the right of the Models heading and select the ''Create EER Model from Script'' iten1. Then, you can use the resulting dialog box to select the script file. Hovv to design a database The Models tab of the MySQL Workbench Home page ■ MySQl. Workbench D X File Edit View Database T DOis Scripting Help Models 0@ 0 om ap c::I C;
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Database Transactions

**Definition:** .-,, 
o Add Table 
~ 
tenns 
Views , " tems 
general_ledget _acco .•.

### Explanation
Hovv to design a database 
The EER model for the AP database 
■ 
MySQl Workbench 
D 
X 
MySOL Model" (ap.ln'Nb) "' 
EER Dai,am 
>< 
Rle 
Edit 
Vtf!Nf 
Arrange 
Model 
Database 
T cols 
Scripting 
Help 
IJ□ 
Descnllbot' Ea,toi 
vendcn: MySQL Table 
V 
Mooel C>,et111eA 
¢ 
--' 
Add Diagram 
EER CXagam 
Y Physical Schemas 
Tables ,.. .-,, 
o Add Table 
~ 
tenns 
Views , " tems 
general_ledget _acco .•.

J lnVOICe _archive 
vendor_cantac:ts 
::J vendm 
••• = 
::: = + -
G 
lnVOiee_lne_ilef!\$ 
:J Invoices 
V 
-----------------
Descnpbon 
!;-
TablcName: ~s 
Schema: 
ap 
ColurmNamc 
Datatype 
PK 
i'N 
UQ 
B 
l.l'l 
"ZF 
Al 
G 
OefaJ~ 
Type 
Oefmion 
Fla, 
< 
> 
User T ypn 
Hisll:lry 
Ready 
Description 
vcndor_td 
INT(ll) 
vendor_name 
VARCHAR(SO) 
vendor_addrcssl 
VARCHAR(SO) 
vendor _addri!5S2 
VARCHAR(SO) 
C-OlumName: 
Cllarsct/Colation: 
r 
O"aa!U!t 
!.'L~t t'"ol:3!!0<\ 
Comments: 
0 0 D D D D 0 
D 
□ 0 
□ D D □ □ 
□ D □ □ D □ D D 
NUU 
□ □ D □ □ □ □ D 
NULL 
-
-
Data Type: 
OefaJt: 
Stxnvc: 
Virtual 
Stored 
No-ttu 
l..hslQncd 
Pmwy~y 
£lirwy 
Auto lncrenent 
~ated 
Columns 
Indeces 
Forelgn Keys 
Triggers 
Part,tlomng 
Options 
Inserts 
Pnvilegcs 
• 
An EER model is a representation of the entities, or objects, of the database 
including the tables, views, and stored programs.

Unique 
Zero AI 
• 
To edit a table, double-click on it. Then, use the tabs that appear across the bottom 
of the window to modify the table's columns, indexes, and foreign keys. • 
To add a new table, double-click on the Add Table icon. Then, use the tab that 
appears to define the table. • 
To delete a table, right-click on it and select the Delete item. • 
The skills for working with tables also apply to other database objects such as 
views and stored programs.

### Key Points
- .-,, 
o Add Table 
~ 
tenns 
Views , " tems 
general_ledget _acco .•.
- Unique 
Zero AI 
• 
To edit a table, double-click on it.
- Then, use the tabs that appear across the bottom 
of the window to modify the table's columns, indexes, and foreign keys.
- • 
To add a new table, double-click on the Add Table icon.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## ACID Properties

**Definition:** .-,, 
o Add Table 
~ 
tenns 
Views , " tems 
general_ledget _acco .•.

### Explanation
Hovv to design a database 
The EER model for the AP database 
■ 
MySQl Workbench 
D 
X 
MySOL Model" (ap.ln'Nb) "' 
EER Dai,am 
>< 
Rle 
Edit 
Vtf!Nf 
Arrange 
Model 
Database 
T cols 
Scripting 
Help 
IJ□ 
Descnllbot' Ea,toi 
vendcn: MySQL Table 
V 
Mooel C>,et111eA 
¢ 
--' 
Add Diagram 
EER CXagam 
Y Physical Schemas 
Tables ,.. .-,, 
o Add Table 
~ 
tenns 
Views , " tems 
general_ledget _acco .•.

J lnVOICe _archive 
vendor_cantac:ts 
::J vendm 
••• = 
::: = + -
G 
lnVOiee_lne_ilef!\$ 
:J Invoices 
V 
-----------------
Descnpbon 
!;-
TablcName: ~s 
Schema: 
ap 
ColurmNamc 
Datatype 
PK 
i'N 
UQ 
B 
l.l'l 
"ZF 
Al 
G 
OefaJ~ 
Type 
Oefmion 
Fla, 
< 
> 
User T ypn 
Hisll:lry 
Ready 
Description 
vcndor_td 
INT(ll) 
vendor_name 
VARCHAR(SO) 
vendor_addrcssl 
VARCHAR(SO) 
vendor _addri!5S2 
VARCHAR(SO) 
C-OlumName: 
Cllarsct/Colation: 
r 
O"aa!U!t 
!.'L~t t'"ol:3!!0<\ 
Comments: 
0 0 D D D D 0 
D 
□ 0 
□ D D □ □ 
□ D □ □ D □ D D 
NUU 
□ □ D □ □ □ □ D 
NULL 
-
-
Data Type: 
OefaJt: 
Stxnvc: 
Virtual 
Stored 
No-ttu 
l..hslQncd 
Pmwy~y 
£lirwy 
Auto lncrenent 
~ated 
Columns 
Indeces 
Forelgn Keys 
Triggers 
Part,tlomng 
Options 
Inserts 
Pnvilegcs 
• 
An EER model is a representation of the entities, or objects, of the database 
including the tables, views, and stored programs.

Unique 
Zero AI 
• 
To edit a table, double-click on it. Then, use the tabs that appear across the bottom 
of the window to modify the table's columns, indexes, and foreign keys. • 
To add a new table, double-click on the Add Table icon. Then, use the tab that 
appears to define the table. • 
To delete a table, right-click on it and select the Delete item. • 
The skills for working with tables also apply to other database objects such as 
views and stored programs.

### Key Points
- .-,, 
o Add Table 
~ 
tenns 
Views , " tems 
general_ledget _acco .•.
- Unique 
Zero AI 
• 
To edit a table, double-click on it.
- Then, use the tabs that appear across the bottom 
of the window to modify the table's columns, indexes, and foreign keys.
- • 
To add a new table, double-click on the Add Table icon.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Transaction Isolation Levels

**Definition:** AUTO INCREMENT 
Identifies a column whose value is automatically incremented by 
MySQL when a new row is added.

### Explanation
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

### Key Points
- [, table_ level_ constraints] 
Common column attributes 
Attribute 
Description 
NOT NULL 
UNIQUE 
Indicates that the column doesn't accept null values.
- If ornitted, 
the column can accept null values.
- DEFAULT default_ value 
Specifies that each value stored in the column must be uajque.
- Specifies a default value for the column as a literal or as an 
• 
expression.
- AUTO INCREMENT 
Identifies a column whose value is automatically incremented by 
MySQL when a new row is added.

### Examples
**SQL Example 1:**
```sql
drop tables, you must drop the last table that was created first. Then, you can work back to the first table that was created. Otherwise, the foreign keys might not allow you to delete the tables. The SQL script that creates the AP database -- create the database DROP DATABASE IF EXISTS ap;
```
Example SQL query

**SQL Example 3:**
```sql
select the database USE ap;
```
Example SQL query

**SQL Example 4:**
```sql
create the tables CREATE TABLE general_ ledger_accounts { account_ number account_description ) ;
```
Example SQL query

**SQL Example 5:**
```sql
CREATE TABLE terms ( INT VARCHAR ( 5 0) PRIMARY KEY, UNIQUE terms id terms_description terms_due_days INT VARCHAR ( 5 0) INT PRIMARY KEY NOT NULL, NOT NULL AUTO_ INCREMENT, ) ;
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Database Indexes

**Definition:** How to create databases, tables, and indexes 
The indexes for the Invoices table 
■ 
MySQl.

### Explanation
How to create databases, tables, and indexes 
The indexes for the Invoices table 
■ 
MySQl. Workbench 
D 
X 
Local instance MySQLSO x 
File 
Edit 
Vtew 
Query 
Database 
Sefver 
Tools 
Scripting 
Help 
fjl 
&il lil &l Bi!l rai ~ 
SCHEMAS 
~ IRter ol)Jccn 
• U ap 
• 
Tables 
► II oenual_ledoer_accounts 
► i1 invoice_archive 
► iii ln,olce_hne_items 
► C Invoices 
► El turns 
► &l vendor_conta<ts 
► Cl vendors 
Views 
'cl'.l stored Procedures 
'cl Functions 
► 
ex 
► 
om 
..

=• 
Administration 
Schemas 
Information 
Columns: = ~ 
~~i~j Al PK 
nvoke_runber 
vardw(SO) 
invoic~ date. dare 
nvoice.Jiital 
drotN,1{9,2) 
payment_total 
deomal(9,2) 
aedit_total 
deomo1(9,2J 
te.rms_id 
nt(U) 
--- ~.., Aa ♦a .-.st. Ob)ea Info 
S5SIOO 
Description 
j 
,., 
V 
V 
Query 1 
il:1-:\i& 
Table Name: F 
I Schema: 
ap 
L-----------' 
Olarset/Collation: 
utfl!tnb4 
v lutf8mb4_0900_ v 
Engine: 
[ lmoOB 
Cooments: 
Index Name 
Tyi:,e 
tndexCoums--------
PRIMARY 
PRIMARY 
mvo,ces_l'k_vendors 
INDEX 
lnvoices_fk_terms 
INDEX 
mvo1cesjnvoice_~.

1NOEX 
Column 
;; 
0 ,nvoice_d 
0 veodor_ld 
0 lnvolce_number 
0 invoice_date 
l 
0 lnvoice_total 
0 payment_total 
0 credit_tota 
0 terms_ld 
0 involce_due_date 
D payment_date 
< 
Columns 
Ind~ 
Foreio11 Keys 
Tnogers 
Partrtionlng 
OptioM 
~ l~ 
ASC 
ASC 
ASC 
DESC 
ASC 
ASC 
ASC 
ASC 
ASC 
ASC 
> 
Index Opbons 
Storage Type: 
Key Block Sae: lo 
Parser: I 
V~: 1:21 
Index Comment 
• 
To view the indexes for a table, right-click on the table in the Navigator window, 
select the Alter Table item, and click on the Indexes tab.

### Key Points
- =• 
Administration 
Schemas 
Information 
Columns: = ~ 
~~i~j Al PK 
nvoke_runber 
vardw(SO) 
invoic~ date.
- dare 
nvoice.Jiital 
drotN,1{9,2) 
payment_total 
deomal(9,2) 
aedit_total 
deomo1(9,2J 
te.rms_id 
nt(U) 
--- ~.., Aa ♦a .-.st.

### Examples
**SQL Example 1:**
```sql
drop existing keys. The foreign keys for the Invoices table ■ MySQl. Workbench D X 1.oca1 IMlance MySOLSO x File Edit Vtew Query Database Server Tools Scripting Help ouerv 1 il:1·\Hftlffll,;
```
Example SQL query

**SQL Example 2:**
```sql
drop the tables if they already exist. 3. Write INSERT staten1ents that add rows to the tables that are created in exercise 2. Add two rows to the Members table for the first two member IDs. Add two rows to the Committees table for the first two committee IDs. Add three rows to the Members Committees table: one row for member 1 and committee 2;
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## SQL Authorization

**Definition:** That means that 
you can code views that join tables, summarize data, and use subqueries and 
functions.

### Explanation
How to create views 
Some of the benefits provided by views 
Benefit 
Description 
Design independence 
Data security 
Simplified queries 
Updatability 
Description 
Views can limit the exposure of tables to external users and applications. As a result, if the design of the tables changes, yo1.1 can modify the view 
as necessary so t1sers who query the view don't need to be aware of the 
change, and applications that use the view don't need to be modified.

Views can restrict access to the data in a table by using the SELECT 
clat1se to include only selected columns of a table or by using the 
WHERE clause to include 011ly selected rows in a table. Views can be used to hide the complexity of retrieval operations. Then, 
the data can be retrieved using simple SELECT statements that specify a 
view in the FROM clause. With certain restrictions, views can be used to update, insert, and delete 
data fron1 a base table.

• 
You can create a view based on almost any SELECT statement. That means that 
you can code views that join tables, summarize data, and use subqueries and 
functions. Benefits of using views

Database design and impleme11,tation, 
How to work with views 
Now that you have a general understanding of how views work and of the 
benefits that they provide, you 're ready to learn the details for working with 
them.

### Key Points
- Views can restrict access to the data in a table by using the SELECT 
clat1se to include only selected columns of a table or by using the 
WHERE clause to include 011ly selected rows in a table.
- Views can be used to hide the complexity of retrieval operations.
- Then, 
the data can be retrieved using simple SELECT statements that specify a 
view in the FROM clause.
- With certain restrictions, views can be used to update, insert, and delete 
data fron1 a base table.

### Examples
**SQL Example 1:**
```sql
WITH CHECK OPTION clause CREATE OR REPLACE VIEW vendor_payment AS SELECT vendor_name, invoice_ number, invoice_date, payment_date, invoice_ total, credit_total, payment_total WHERE invoice_total - payment_total - credit_total >= 0 WITH CHECK OPTION A SELECT statement that displays a row from the view SELECT* FROM vendor_payment WHERE invoice_ DtJmh~r = 'P-0608' The result set vendor _name ► MaDoy Lithographing Inc invoice _number P-0608 invoice date payment_date 2018-0 7 _23;
```
Example SQL query

**SQL Example 2:**
```sql
UPDATE statement that updates the view UPDATE vendor_payment SET payment_total = 400.00, payment_date = '2018-08-01' WHERE invoice_ numher = 'P-0608' The response from the system (1 row affected) The same row data after the update credit_total 1200.00 payment_total 0.00 invoice_number invoice_date 2018-07-23 2018-08-01 1200. 00 .WO. 00 An UPDATE statement that attempts to update the view SET payment_ total = 30000.00, WHERE invoice_number = 'P-0608';
```
Example SQL query

**SQL Example 3:**
```sql
delete or update a parent row: a foreign key constraint fails ('ap'.'invoice_line_items', CONSTRAINT 'line_ items_fk_invoices' FOREIGN KEY ( 'invoice_id' ) REFERENCES 'invoices' { ' invoice id• ) ) Two DELETE statements that succeed DELETE FROM invoice_ line_ items WHERE invoice_ id = (SELECT invoice_ id FROM WHERE invoice number= DELETE FROM ihm invoices WHERE invoice_n11mher = • QS45443';
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Introduction to MySQL

**Definition:** 4 
The hardware con1ponents of a client/server system ......................................................

### Explanation
, ___ _ 
. --· . . -
-.. .. -- . ,. -
MASTER THE SQL STATEMENTS 
tl1at every application developer needs 
for retrieving and updating the data 
in a MySQL database 
D SIGN DATABASES IKE A PRO 
and code tl1e SQL state1nents tl1at create 
databases, tables, indexes, and ,ie,vs 
GAIN PROFESSIONAL SKILLS 
like using transactions, stored procedures, 
functions, triggers, and events 
GET STARTED AS A DBA 
by learning l1ow to configure tl1e server, 
manage security, and create bacluips

3RD EDITION 
Joel Murach

TRAINING & REFERENCE 
3RD EDITION 
Joel Murach 
M IKE M URACH & A SSOCIATES, I NC.

4340 N. Knoll Ave. • Fresno, CA 93722 
www.murach.com • murachbooks@murach.com

Editorial team 
Author: 
Writer/Editor: 
Editorial Support: 
Production: 
Joel Murach 
Anne Boehm 
Steven Mannion 
Samantha Walker 
Books on general-purpose programming languages 
Murach's Python Programming 
Murach's Java Programming 
Murach's C++ Programming 
Murach's C# 
Murach 's Visual Basic 
Books for web developers 
Murach's HTML5 and CSS3 
Murach's JavaScript and)Query 
Murach's PHP and MySQL 
Murach.'s Java Servlets and JSP 
Murach's ASP.NET Web Progra11iming with C# 
Books for database programmers 
Murach 's MySQL 
Murach's SQL Server for Developers 
Murach's Oracle SQL and PLJSQL for Developers 
For more on Murach books, 
please visit us at www.murach.com 
© 2019, Mike Murach & Associates, Inc.

All rights reserved. Printed in the United States of America 
10 9 8 7 6 5 4 3 2 1 
ISBN: 978-1-943872-36-7

Content 
Introduction 
An introduction to relational databases 
How to use MySQL Workbench and other development tools 
How to retrieve data from a single table 
How to retrieve data from two or more tables 
How to insert, update, and delete data 
How to code summary queries 
How to code subqueries 
How to work with data types 
How to use functions 
How to design a database 
How to create databases, tables, and indexes 
How to create views 
Language skills for writing stored programs 
How to use transactions and locking 
How to create stored procedures and functions 
How to create triggers and events 
An introduction to database administration 
How to secure a database 
How to backup and restore a database 
Appendixes 
Appendix A 
Appendix B 
How to install the software for this book on Windows 
How to install the software for this book on macOS 
• •• 
Xlll

•• 
Expanded contents 
VI I 
Expanded contents 
============= 
An introduction to client/server systems .........................................

### Key Points
- Understanding Introduction to MySQL is essential for working with databases

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Relational Databases

**Definition:** An introduction to MySQL 
Before you begin to learn how to write SQL statements that work with 
MySQL, you need to understand some concepts and terms related to SQL 
and relational databases.

### Explanation
An introduction to MySQL 
Before you begin to learn how to write SQL statements that work with 
MySQL, you need to understand some concepts and terms related to SQL 
and relational databases. That's what you'll learn in chapter 1. In addition, 
you'll need to learn about some of the tools you can use to work with a 
MySQL database. That's what you'll learn in chapter 2. After that, you'll be ready to learn about the most important SQL 
statements.

In chapter 3, you'll learn how to use the SELECT statement 
to retrieve data from a single table. In chapter 4, you'll learn how to use 
the SELECT statement to retrieve data from two or more tables. And in 
statements to add, update, and delete rows. At that point, you'll have all of 
the background and skills that you need to work with the rest of this book. An introduction 
to relational databases 
This chapter presents the concepts and term.~ that you should understand 
before }rou begin learning how to \Vork \Vith a SQL database such as 1'1ySQL.

Although thi chapter doesn't present the coding details. it doe pre. ent an 
o~·en·ie"'' of the most importa.11t type ot· SQL staten1ents that are presented in 
this book. An introduction to client/server systems ·····~····················~·4 
·n1e l1ardware co1nponeru of a cl1entlser,er sy!den1 ...................................... 4 
·rhe .

### Key Points
- In addition, 
you'll need to learn about some of the tools you can use to work with a 
MySQL database.
- After that, you'll be ready to learn about the most important SQL 
statements.
- In chapter 3, you'll learn how to use the SELECT statement 
to retrieve data from a single table.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## SELECT Statement

**Definition:** Then, select the Columns 
tab at the bottom of the window that's displayed to view the column definitions for 
the table.

### Explanation
Cliapter 2 
How to use MySQL Workbench and other develop,nent tools 
The column definitions for the Vendors table 
8 MySQL Workbench 
Local insmnce MySQLSO X 
File 
Edit 
Vif!!N 
Query 
Database 
Senter 
Tools 
Scnptmo 
Help 
Que,y1 
SCHEMAS 
Table Name: lvendc.-s 
J Sdtema: ap 
q, I 
RI~ ob)ects 
T .J ap 
Owset/Colation: 
utfBni>'l 
v j utf8mb'1_0900_ v 
Engine: 
lmo06 
T'cl Tables 
► 
general_ledger_accounts 
► 
fnvo1ce_archlve 
► 
mvoice_lme_iteJT'6 
► 
Invokes 
► 
te_rms 
► II vendor_contacts 
T 
vendors 
►[;:) Co lumns 
► 
Ind!!RS 
► ~ 
Fore:ion Keys 
► 
Triggers 
Views 
storNI Procedures 
'i!5J Functions 
► 
ex 
► 
om 
► 
sys 
Administration ~as 
• for, 
uo 
Table: vendors 
Columns: 
lnt(ll) 
AIPK 
vardia 
va<cha 
varcha 
var cha 
char(2: 
Comments: 
CoumName 
vendor_id 
vendor_name 
J vendor _addressl 
; vie_ndor _address2 
vendor_dty 
vendor_sta2 
vendor_zip_codt 
vendor_phone 
vendor_contact_last_name 
vie_ndor _contact_firsLname 
~ ddault_terms_id 
~ ddauft_account_number 
< 
Colum Name.: 
Charset/Cola6on: 
Comments: 
Datatype 
INT(U) 
VARCHAA(SO} 
VAACHAA(SO) 
VARCHAA(SO) 
VAACHAA(SO} 
CHAR{2) 
VARCHAA(20) 
VARCHAA(SO) 
VARCHAR(SO) 
VARCHAA(SO} 
!Nl{l 1) 
!Nl{U) 
PK 
l'-N 
UQ 
B 
~ lF 
0 D D D D 
D 
E2l 
E2I D D D 
D D D D D D 
□ D □ D D □ 
□ E2I 
□ □ □ □ 
□ E2I 
□ □ D □ 
□ 0 
□ D D □ 
□ D D D D □ 
D D □ □ D □ 
□ D D □ D □ 
□ E2I 
□ □ D □ 
□ E2I 
□ D D □ 
Data Type: 
DefalJt: 
Starage: 
Virtual 
Primary Key 
Bnarv 
Autolncr~t 
vendor id 
vendor_naml!

veocb _address! vendor _address2 
vendc<_oty 
vendor _state 
vendor _zlp_code 
vendor _phone 
Vatchll 
varcha 
Colu111ns 
Indexes 
Foreign Keys 
Trfggers 
Partitioning 
Options 
varcha v 
Al 
E2l 
D 
D 
D 
D 
D 
D 
□ 
D 
D 
D 
D 
□ 
V 
.. G 
Oefault,bilresslon 
D 
D 
D 
D 
D 
□ 
□ 
D 
D 
D 
D 
D 
Sto,-ed 
NULL 
NULL 
NULL 
NULL 
NULL 
Notl'd 
Urtqie 
u~ 
aroMlf 
> 
ven<!or _contact_l!9!l'l_name 
Object Info 
Session 
Apply 
Revert 
Description 
• 
To view the column definitions for a table, right-click the table name in the 
Navigator window and select the Alter Table command.

Then, select the Columns 
tab at the bottom of the window that's displayed to view the column definitions for 
the table. • 
To edit the column definitions for a table, view the column definitions. Then, you 
can t1se the resulting window to add new columns and modify and delete existing 
columns. • 
For more information about creating and modifying tables, see chapter 11. How to view and edit the column definitions 
X 
V

An introduction to MySQL 
How to use MySQL Workbench 
to run SQL staten,ents 
Besides letting you review the design of a database, MySQL Workbench is a 
great tool for entering and running SQL statements.

### Key Points
- Then, select the Columns 
tab at the bottom of the window that's displayed to view the column definitions for 
the table.
- • 
To edit the column definitions for a table, view the column definitions.

### Examples
**SQL Example 1:**
```sql
SELECT vendor_natie, vcndor_city, vendor_strte fRc»1 vendors ORDER BY vendor name;
```
Example SQL query

**SQL Example 2:**
```sql
SELECT vendor_name, vendor_city FR<Y-1 vendors T Tables ► II gcneral_ledger_accounts ► 6J lnvoice_archlve ► invoiu_line_items l,lfERE vendor_id: ;
```
Example SQL query

**SQL Example 3:**
```sql
SELECT COUttT(*) AS number_of_invoices, SUM(invoice_total - payment_total - credit_total) AS total_due FRCJ1 invoices ► Invoice ► II terms i..HERE vendor id= ;
```
Example SQL query

**SQL Example 4:**
```sql
SELECT statement, the MySQL Command Line Client displays a message giving the nu1nber of rows that are included in the result set and the amount of time it took to run the query. In this case, it took less than 1/100 of a second to run the query. Cliapter 2 How to list the names of all databases managed by the server mysql> show databases;
```
Example SQL query

**SQL Example 5:**
```sql
select a database for use mysql> use ap;
```
Example SQL query

**SQL Example 6:**
```sql
select data from a database mysql> select vendor_name from vendors limit 5;
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## WHERE Clause

**Definition:** MYSQL.COM 
OOWNLO.-\DS 
DOCUMENTATION 
DEVELO?ER ZOl~E 
Q.

### Explanation
Cliapter 2 
How to use MySQL Workbench and other develop,nent tools 
The web address for the MySQL 8.0 Reference Manual 
https://dev.rrwsgl.com/doc/refman/8.0/en/ 
A web page from the MySQL Reference Manual 
B MySQL MySQL 8.0 'le!erence 
)( 
+ 
D 
C 
i 
hnps dev.mysql.com oc/refman/8.0/en/manual-1nfo.html 
* e 
= 
The v10rld s most popula Of)"'JI source database 0. Contact MySQL I Login I Register 
MyS~ .

MYSQL.COM 
OOWNLO.-\DS 
DOCUMENTATION 
DEVELO?ER ZOl~E 
Q. A Documentation Home 
MySQL 8.0 Reference Manual 
Preface and Legal Notices 
., General Information 
About This Manual 
Typographical and Syntax Convenoons 
> overview of the MY5QL Database 
Management System 
• What Is New In MySQL 8.0 
• Server and Status vanables and 
opoons Added, Deprecated, or 
Rem011ed jr) MY5QL 8.0 
Description 
MySQL 8.0 Reference Manual I General lnformaOOl'I I About Ths Manua 
version 8.0 
¥ 
1.1 About This Manual 
This 1s the Reference Manual for the MySQL Database System, version 8.0, 
through release 8.0.15.

Differences between minor versions of MySQL 8.0 are 
noted In the present text with reference to release numbers (8.0. x). For license 
1nformatlon, see the Legal Notices . This manual Is not intended for use with older versions of the MySQL software 
due to the many functional and other differences between MY5QL 8.0 and 
previous versions. If you are using an earlier release of the MySQL software, 
please refer to the appropnate manual.

### Key Points
- MYSQL.COM 
OOWNLO.-\DS 
DOCUMENTATION 
DEVELO?ER ZOl~E 
Q.
- Differences between minor versions of MySQL 8.0 are 
noted In the present text with reference to release numbers (8.0.

### Examples
**SQL Example 1:**
```sql
SELECT statement, the MySQL Command Line Client displays a message giving the nu1nber of rows that are included in the result set and the amount of time it took to run the query. In this case, it took less than 1/100 of a second to run the query. Cliapter 2 How to list the names of all databases managed by the server mysql> show databases;
```
Example SQL query

**SQL Example 2:**
```sql
select a database for use mysql> use ap;
```
Example SQL query

**SQL Example 3:**
```sql
select data from a database mysql> select vendor_name from vendors limit 5;
```
Example SQL query

**SQL Example 4:**
```sql
SELECT statement that retrieves three columns from each row, sorted in descending sequence by invoice total SELECT invoice_number, invoice_date, invoice_ total FROM invoices ORDER BY invoice_total DESC invoice number invoice date invoice total -;
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## ORDER BY Clause

**Definition:** 20 
0.00 
2018-04-13 
138.75 
0.00 
2-000-2993 
2018-04-16 
144.70 
0.00 
2018-04-16 
15.50 
0.00 
2018-04-16 
42.

### Explanation
How to retrieve datafrom a single table 
A SELECT statement that renames the columns in the result set 
SELECT invoice_number AS "Invoice Number", invoice_date AS Date, 
invoice total AS Total 
FROM invoices 
Invoice Number 
Date 
Total 
► 
989319-457 
2018-04-08 
3813.33 
2018-04-10 
-10.20 
2018-04-13 
138. 75 
2-000-2993 
2018-04-16 
144. 70 
2018-04-16 
15.50 
2018-04-16 
42.75 
(114 rows) 
A SELECT statement that doesn't name a calculated column 
SELECT invoice_number, invoice_date, invoice_total, 
invoice_total - payment_total - credit_total 
FROM invoices 
~ 
invoice_number 
invoice date 
invoice total 
invoice_tot.al - payment_total - credit_tot.al 
2018-04-08 
3813, 33 
0.00 
► 
989319-457 
2018-04-10 
"10.

20 
0.00 
2018-04-13 
138.75 
0.00 
2-000-2993 
2018-04-16 
144.70 
0.00 
2018-04-16 
15.50 
0.00 
2018-04-16 
42. 75 
0.00 
(114 rows) 
Description 
• 
By default, a column in the result set is given the same name as the column in 
the base table. If that's not what you want, you can specify a substitute name, or 
column alias, for the column. • 
To specify an alias for a column, use the AS phrase.

Although the AS keyword is 
optional, I recommend you code it for readability. • 
If you don't specify an alias for a column that's based on a calculated value, 
MySQL uses the expression for the calculated value as the column name. • 
To include spaces or special characters in an alias, enclose the alias in double 
quotes ( " ) or single quotes ( ' ). How to name the columns in a result set using aliases 
V 
An introduction to MySQL 
How to code arithmetic expressions 
the arithmetic operators you can use in this type of expression.

### Key Points
- 20 
0.00 
2018-04-13 
138.75 
0.00 
2-000-2993 
2018-04-16 
144.70 
0.00 
2018-04-16 
15.50 
0.00 
2018-04-16 
42.
- 75 
0.00 
(114 rows) 
Description 
• 
By default, a column in the result set is given the same name as the column in 
the base table.
- If that's not what you want, you can specify a substitute name, or 
column alias, for the column.

### Examples
**SQL Example 1:**
```sql
with literal values. The third example uses another function, CURRENT_DATE, to supply a date value in place of the invoice_date column that's coded in figure 3-7. Four SELECT statements without FROM clauses Example 1 : Testing a calculation SELECT 1000 * (1 + .1) AS 1110% More Than 1000" 10°/4 More Than 1000 ---I -- ► 1100.0 "'-~------;
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Joining Tables

**Definition:** Each of the expressions in the list is automatically converted to the 
same type of data as the test expression.

### Explanation
How to retrieve data from a sin.gle table 
The syntax of the WHERE clause with an IN phrase 
WHERE test_expression [NOT] IN 
({subquerylexpression_ l [, expression_2 ] ... }) 
Examples of the IN phrase 
An IN phrase with a list of numeric literals 
WHERE terms_ id IN (1, 3, 4) 
An IN phrase preceded by NOT 
WHERE vendor_ state NOT IN ('CA', 'NV', 'OR') 
An IN phrase with a subquery 
WHERE vendor id IN 
(SELECT vendor id 
FROM invoices 
WHERE invoice_date = 
1 2018-07-18 1
) 
Description 
• 
You can use the IN phrase to test whether an expression is equal to a value in a list 
of expressions.

Each of the expressions in the list is automatically converted to the 
same type of data as the test expression. • 
The list of expressions can be coded in any order without affecting the order of the 
rows in the result set. • 
You can use the NOT operator to test for an expression that's not in the list of 
• 
expressions. • 
You can also compare the test expression to the items in a list returned by a 
subquery.

You'll learn more about coding subqueries in chapter 7. How to use the IN operator

An introduction to MySQL 
How to use the BETWEEN operator 
When you use this operator, the value of a test expression is compared to the 
range of values specified in the BETWEEN phrase. If the value falls within this 
range, the row is included in the query results. The first example in this figure shows a simple WHERE clause that uses the 
BETWEEN operator.

### Key Points
- Each of the expressions in the list is automatically converted to the 
same type of data as the test expression.
- • 
The list of expressions can be coded in any order without affecting the order of the 
rows in the result set.
- • 
You can use the NOT operator to test for an expression that's not in the list of 
• 
expressions.
- • 
You can also compare the test expression to the items in a list returned by a 
subquery.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Inner Join

**Definition:** Each of the expressions in the list is automatically converted to the 
same type of data as the test expression.

### Explanation
How to retrieve data from a sin.gle table 
The syntax of the WHERE clause with an IN phrase 
WHERE test_expression [NOT] IN 
({subquerylexpression_ l [, expression_2 ] ... }) 
Examples of the IN phrase 
An IN phrase with a list of numeric literals 
WHERE terms_ id IN (1, 3, 4) 
An IN phrase preceded by NOT 
WHERE vendor_ state NOT IN ('CA', 'NV', 'OR') 
An IN phrase with a subquery 
WHERE vendor id IN 
(SELECT vendor id 
FROM invoices 
WHERE invoice_date = 
1 2018-07-18 1
) 
Description 
• 
You can use the IN phrase to test whether an expression is equal to a value in a list 
of expressions.

Each of the expressions in the list is automatically converted to the 
same type of data as the test expression. • 
The list of expressions can be coded in any order without affecting the order of the 
rows in the result set. • 
You can use the NOT operator to test for an expression that's not in the list of 
• 
expressions. • 
You can also compare the test expression to the items in a list returned by a 
subquery.

You'll learn more about coding subqueries in chapter 7. How to use the IN operator

An introduction to MySQL 
How to use the BETWEEN operator 
When you use this operator, the value of a test expression is compared to the 
range of values specified in the BETWEEN phrase. If the value falls within this 
range, the row is included in the query results. The first example in this figure shows a simple WHERE clause that uses the 
BETWEEN operator.

### Key Points
- Each of the expressions in the list is automatically converted to the 
same type of data as the test expression.
- • 
The list of expressions can be coded in any order without affecting the order of the 
rows in the result set.
- • 
You can use the NOT operator to test for an expression that's not in the list of 
• 
expressions.
- • 
You can also compare the test expression to the items in a list returned by a 
subquery.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Outer Join

**Definition:** • 
If you code a single argument, it specifies the maximum row count, beginning with 
the first row.

### Explanation
How to retrieve data from a sin.gle table 
The expanded syntax of the LIMIT clause 
LIMIT [offset,] row_count 
A SELECT statement with a LIMIT clause that starts with the first row 
SELECT vendor_ id, invoice_ total 
FROM invoices 
ORDER BY invoice_total DESC 
LIMIT 5 
vendorjd 
invoice_ total 
► 
37966.19 
26881 .40 
23517.58 
21842.00 
20551. 18 
SELECT invoice_ id, vendor_ id, invoice_ total 
FROM invoices 
ORDER BY invoice_ id 
LIMIT 2, 3 
invoice id -
vendor_id 
invoice total 
► 
138.75 
144.70 
15.50 
SELECT invoice_ id, vendor_ id, invoice_total 
FROM invoices 
ORDER BY invoice id 
LIMIT 100, 1000 
invoice id -
vendor_id 
invoice_total 
► 
30.75 
20551.18 
2051.59 
44.44 
(14 rows ) 
Description 
• 
You can use the LIMIT clause to limit the number of rows returned by the SELECT 
statement.

This clause takes one or two intege1· arguments. • 
If you code a single argument, it specifies the maximum row count, beginning with 
the first row. If you code both arguments, the offset specifies the first row to return, 
where the offset of the first row is 0. • If you want to retrieve all of the rows from a certain offset to the end of the result 
set, code -1 for the row count. • 
Typically, you'll use an ORDER BY clause whenever you use the LIMIT clause.

How to code the LIMIT clause 
'

An introduction to MySQL 
Perspective 
The goal of this chapter has been to teach you the basic skills for coding 
SELECT statements. As a result, you'll use these skills in almost every 
SELECT statement you code. As you'll see in the next chapter and in chapters 6 and 7, though, there's 
a lot more to coding SELECT statements than what's presented here. In these 
chapters, then, you'll learn additional skills for coding SELECT statements.

### Key Points
- This clause takes one or two intege1· arguments.
- • 
If you code a single argument, it specifies the maximum row count, beginning with 
the first row.
- If you code both arguments, the offset specifies the first row to return, 
where the offset of the first row is 0.
- • If you want to retrieve all of the rows from a certain offset to the end of the result 
set, code -1 for the row count.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## INSERT Statement

**Definition:** How to retrieve data f rom two or m.ore tables 
The explicit syntax for an outer join 
SELECT select_ list 
FROM table_ l 
{LEFTIRIGHT} [OUTER] JOIN table_ 2 
ON join_condition_ l 
[{LEFTIRIGHT} [OUTER] JOIN table_ 3 
ON join_condition_ 2] ...

### Explanation
How to retrieve data f rom two or m.ore tables 
The explicit syntax for an outer join 
SELECT select_ list 
FROM table_ l 
{LEFTIRIGHT} [OUTER] JOIN table_ 2 
ON join_condition_ l 
[{LEFTIRIGHT} [OUTER] JOIN table_ 3 
ON join_condition_ 2] ... What outer joins do 
Joins of this type 
Retrieve unmatched rows from 
Left outer join 
Right outer join 
A left outer join 
The first (left) table 
The second (right) table 
SELECT vendor_ name, invoice_number, invoice_total 
FROM vendors LEFT JOIN invoices 
ON vendors.vendor_ id = invoices.vendor_id 
ORDER BY vendor_name 
_J vendor _name 
► 
Abbey Office Furnishings 
American Booksellers Assoc 
American Express 
ASCSigns 
I 
Ase.om Hasler Mailing Systems 
(202 rows) 
Description 
invoice_number 
nvoice_total 
203339-13 
17.50 
l)QJ!t 
'®'' 
HWSI 
UPJII 
OPill 
Ul9!1 
l:tt!I 
• 
An outer join 1·etrieves all rows that satisfy the join condition, plus unmatched rows 
in the left or right table.

• 
In most cases, you use the equal operator to retrieve rows with matching columns. However, you can also use any of the other comparison operators. • 
When a row with unmatched columns is retrieved, any columns from the other 
table that are included in the result set are given null values. Note 
• 
The OUTER keyword is optional and typically omitted. How to code an outer join

An introduction to MySQL 
Outer join examples 
To give yot1 a better understanding of how outer joins work, figure 4-9 
shows four more examples.

To start, part 1 of this figure shows the Departments 
table, the Employees table, and the Projects table from the EX database. These 
tables are used by the examples shown in parts 2 and 3 of this figure. In addition, 
they're used in other examples later in this chapter. The first example performs a left outer join on the Departments and 
Employees tables. Here, the join condition joins the tables based on the values in 
their department_number columns.

### Key Points
- • 
In most cases, you use the equal operator to retrieve rows with matching columns.
- However, you can also use any of the other comparison operators.
- • 
When a row with unmatched columns is retrieved, any columns from the other 
table that are included in the result set are given null values.
- Note 
• 
The OUTER keyword is optional and typically omitted.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## UPDATE Statement

**Definition:** • 
MySQL doesn't provide language keywords for full outer joins, but you can 
simulate a full outer join by using the UNION keyword to combine the result sets 
from a left outer join and a right outer join.

### Explanation
How to retrieve data from two or m.ore tables 
A union that simulates a full outer join 
SELECT department_name AS dept_name, d.department_ n11mber AS d_ dept_no, 
e.department_number AS e _dept_no, last_ name 
FROM departments d 
LEFT JOIN employees e 
ON d. department_number = e. department_ n11mber 
UNION 
SELECT department_ name AS dept_name, d.department_number AS d_ dept_ no, 
FROM departments d 
RIGHT JOIN employees e 
ORDER BY dept_name 
► 
dept_name 
Accounting 
Maintenance 
Operations 
Payroll 
Payroll 
Payroll 
I 
Personnel 
Personnel 
(10 rows ) 
Description 
d_dept_no 
ffi991 
e_dept_no 
last_name 
Watson 
locario 
Hernandez 
Hardy 
001!1 
lit!lil 
Smith 
Simonian 
Aaronsen 
Jones 
Oleary 
• 
When you use afull outer join, the result set includes all the 1·ows from both tables.

• 
MySQL doesn't provide language keywords for full outer joins, but you can 
simulate a full outer join by using the UNION keyword to combine the result sets 
from a left outer join and a right outer join. How to simulate a full outer join

An introduction to MySQL 
Perspective 
In this chapter, you learned a variety of techniques for combining data 
from two or more tables into a single result set.

In particular, you learned how 
to use the explicit syntax to code inner joins. Of all the techniques presented in 
this chapter, this is the one you'll use most often. So you'll want to be sure you 
understand it thorough! y before you go on. Terms 
• 
• 
JOin 
join condition 
• 
• 
• 
mner JOtn 
ad hoc relationship 
qualified column name 
explicit syntax 
SQL-92 syntax 
table alias 
schema 
self-join 
Exercises 
implicit syntax 
outer join 
left outer join 
right outer join 
• • 
• 
eqUIJOlll 
natural join 
• 
• 
cross JOtn 
Ca1tesian product 
• 
union 
full outer join 
1.

### Key Points
- How to simulate a full outer join

An introduction to MySQL 
Perspective 
In this chapter, you learned a variety of techniques for combining data 
from two or more tables into a single result set.
- In particular, you learned how 
to use the explicit syntax to code inner joins.

### Examples
**SQL Example 1:**
```sql
SELECT clause. Sort the final result set by the account_number column. 7. Use the UNION operator to generate a result set consisting of two columns from the Vendors table: vendor_name and vendor_state. If the vendor is in California, the vendor_state value should be ''CA'';
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## DELETE Statement

**Definition:** • 
To insert rows selected from one or more tables into another table, you can code a 
subquery in place of the VALUES clause.

### Explanation
Clzapter 5 
How to insert, update, and delete data 
The syntax for using a subquery to insert one or more rows 
INSERT [INTO] table_ name [(column_ list)] select_statement 
Insert paid invoices into the lnvoice_Archive table 
INSERT INTO invoice_archive 
SELECT* 
FROM invoices 
WHERE invoice_ total - payment_total - credit_total = 0 
(103 rows affected) 
The same statement with a column list 
INSERT INTO invoice archive 
(invoice_id, vendor_ id, invoice_number, invoice_total, credit_ total, 
payment_total, terms_id, invoice_date, invoice_due_date) 
SELECT 
invoice_ id, vendor_ id, invoice_number, invoice_ total, credit_ total, 
payment_total, terms_ id, invoice_date, invoice_due_date 
FROM invoices 
WHERE invoice total - payment_total - credit_total = 0 
(103 rows affected) 
Description 
• 
A subquery is a SELECT statement that's coded within another SQL statement.

• 
To insert rows selected from one or more tables into another table, you can code a 
subquery in place of the VALUES clause. Then, MySQL inserts the rows returned 
by the subquery into the target table. For this to work, the target table must already 
. exist. • 
The rules for working with a column list are the same as they are for any INSERT 
statement. How to use a subquery in an INSERT statement

An introduction to MySQL 
How to update existing rows 
To modify the data in one or 1nore rows of a table, you use the UPDATE 
statement.

Although most of the UPDATE statements you code will perform 
simple updates, you can also code more complex UPDATE statements that 
include subqueries if necessary. How to update rows 
statements include all three of the clauses shown here. The UPDATE clause 
names the table to be updated. The SET clause names the columns to be updated 
and the values to be assigned to those columns. And the WHERE clause speci-
fies the condition a row must meet to be updated.

### Key Points
- • 
To insert rows selected from one or more tables into another table, you can code a 
subquery in place of the VALUES clause.
- Then, MySQL inserts the rows returned 
by the subquery into the target table.
- For this to work, the target table must already 
.
- • 
The rules for working with a column list are the same as they are for any INSERT 
statement.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## MySQL Data Types

**Definition:** That makes sense because the WHERE clause is applied 
before the rows are grouped, and the ORDER BY clause is applied after the rows 
are grouped.

### Explanation
How to code sum1n.ary queries 
A summary query that uses the COUNT(*), AVG, and SUM functions 
SELECT 'After 1/1/2018' AS selection_date, 
COUNT(*) AS number_of_ invoices, 
ROUND{AVG{invoice_total), 2) AS avg_ invoice_amt, 
SUM{invoice_total) AS total_ invoice_amt 
FROM invoices 
WHERE invoice_date > '2018-01-01' 
selection_date 
number _of _lnvOJces 
avg_ilvoice_amt 
total_invoice_amt 
► 
After 1/1/2018 
1879.74 
214290.51 
A summary query that uses the MIN and MAX functions 
COUNT { *) AS n11mh~r_of_ invoices, 
MAX{invoice_total) AS highest_ invoice_ total, 
MIN(invoice_total) AS lowest_ invoice_total 
WHERE invoice date> '2018-01-01' 
seJection_date 
number _of Jnvoices 
highest_invoice_total 
lowest_invoice_total 
37966.19 
6.00 
A summary query that works on non-numeric columns 
SELECT MIN{vendor_name) AS first_vendor, 
MAX{vendor_name) AS last_vendor, 
COUNT(vendor_name) AS number_of_vendors 
FROM vendors 
I flrst_vendor 
► I Abbey Office Furnishings 
last_vendor 
Zylka Design 
number _of _vendors 
A summary query that uses the DISTINCT keyword 
SELECT COUNT(DISTINCT vendor_ id) AS number_of_vendors, 
COUNT{vendor_ id) AS number_of_ invoices, 
ROUND(AVG(invoice_ total), 2) AS avg_ invoice_amt, 
SUM(invoice_total) AS total_ invoice_ amt 
number _of_vendors 
number _of_involces 
avg_invoic:e_amt 
Description 
• 
To cot1nt all of the selected 1·ows, you typically use the COUNT(*) function.

Alternately, you can use the COUNT function with the name of any column that 
can't contain null values. To cot1nt only the rows with unique values in a specified column, you can code 
the COUNT function with the DISTINCT keyword followed by the name of the 
column. Queries that use aggregate functions

17 4 
More SQL skills cts you need them 
How to group and summarize data 
Now that you understand how aggregate functions work, you're ready to 
learn how to group data and use aggregate functions to summarize the data in 
each group.

To do that, you can use two new clauses of the SELECT statement: 
GROUP BY and HAVING. How to code the GROUP BY and HAVING clauses 
and HAVING clauses. The GROUP BY clause determines how the selected rows 
are grouped, and the HAVING clause determines which groups are included in 
the final results. These clauses are coded after the WHERE clause but before the 
ORDER BY clause. That makes sense because the WHERE clause is applied 
before the rows are grouped, and the ORDER BY clause is applied after the rows 
are grouped.

### Key Points
- Alternately, you can use the COUNT function with the name of any column that 
can't contain null values.
- To cot1nt only the rows with unique values in a specified column, you can code 
the COUNT function with the DISTINCT keyword followed by the name of the 
column.
- To do that, you can use two new clauses of the SELECT statement: 
GROUP BY and HAVING.
- How to code the GROUP BY and HAVING clauses 
and HAVING clauses.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## MySQL Functions

**Definition:** How to code sum1ncary queries 
The sum of the line item amount columns in the Invoice Line Items table 
that have the same account_nu1nber 
Return only those rows where the count of line items is greater than 1.

### Explanation
How to code sum1ncary queries 
The sum of the line item amount columns in the Invoice Line Items table 
that have the same account_nu1nber 
Return only those rows where the count of line items is greater than 1. This 
sl1ould return 10 rows. Group the result set by the account_description column. Sort the resL1lt set in descending sequence by the sum of the line item 
a1nounts. 5. Modify the solution to exercise 4 so it returns only invoices dated in the 
second quarter of 2018 (April 1, 2018 to June 30, 2018).

This should still 
return 10 rows but with some different line item counts for each vendor. Hint: 
Join to tlie Invoices table to code a secirch condition based on invoice_date. 6. Write a SELECT statement that answers this question: What is the total 
amount invoiced for each general ledger account nt1mber? Return these 
columns: 
The account number column fro1n the Invoice Line Items table 
The sum of the line_item_amount columns from the Invoice_Line_Items 
table 
Use the WITH ROLLUP operator to include a row that gives the grand total.

This should return 22 rows. 7. being paid from more than one account? Return these columns: 
The vendor name colL1mn from the Vendors table 
The count of distinct general ledger accounts that apply to that vendor's 
• 
• 
1nvo1ces 
This should return 2 rows.

### Key Points
- Group the result set by the account_description column.
- Sort the resL1lt set in descending sequence by the sum of the line item 
a1nounts.
- Modify the solution to exercise 4 so it returns only invoices dated in the 
second quarter of 2018 (April 1, 2018 to June 30, 2018).

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## String Functions

**Definition:** Write a SELECT statement that uses aggregate window functions to calculate 
the total due for all vendors and the total due for each vendor.

### Explanation
More SQL skills cts you need them 
9. Write a SELECT statement that uses aggregate window functions to calculate 
the total due for all vendors and the total due for each vendor. Return these 
columns: 
The vendor id from the Invoices table 
The balance due (invoice_total - payment_total - credit_total) for each 
invoice in the Invoices table with a balance due greater than 0 
The total balance due for all vendors in the Invoices table 
The total balance due for each vendor in the Invoices table 
Modify the column that contains the balance due £01· each vendor so it 
contains a cumulative total by balance due.

This should return 11 rows. average balance due for each vendor in the Invoices table. This column should 
contain a cumulative average by balance due. Modify the SELECT statement so it uses a named window for the last two 
aggregate window functions. late a moving average of the sum of invoice totals. Return these columns: 
The month of the invoice date from the Invoices table 
The sum of the invoice totals from the Invoices table 
The moving average of the invoice totals sorted by invoice month 
The result set should be grouped by invoice month and the frame for the 
moving average should include the current row plus tlu·ee rows before the 
current row.

How to code subqueries 
Subqueries allow you to build queries that would be difficult or impossible 
to build otherwise. In chapter 5, you learned how to use them in INSERT, 
UPDATE, and DELETE statements. In this chapter, you'll learn how to use 
subqueries in SELECT statements. An introduction to subqueries .......................................... 200 
Where to code subqueries ...........................................................................

### Key Points
- Write a SELECT statement that uses aggregate window functions to calculate 
the total due for all vendors and the total due for each vendor.
- average balance due for each vendor in the Invoices table.
- This column should 
contain a cumulative average by balance due.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Date and Time Functions

**Definition:** More SQL skills cts you need them 
How to use the ALL keyword 
operator so the condition must be true for all the values returned by a subquery.

### Explanation
More SQL skills cts you need them 
How to use the ALL keyword 
operator so the condition must be true for all the values returned by a subquery. The table at the top of this figure shows how this works. Here, the values in 
parentheses 1·epresent the values returned by the query. If you use the greater than operator(>), the expression must be greater than 
the maximum value returned by the subquery.

Conversely, if you use the less 
than operator ( < ), the expression must be less than the minimum value returned 
by the subquery. If you use the equal operator ( = ), all of the values returned by 
the subquery must be the same and the expression must be equal to that value. And if you use the not equal operator ( <>), the expression must not equal any 
of the values returned by the subquery. However, a not equal condition can be 
restated using the NOT IN operator, which is easier to read.

As a result, it's a 
better practice to use the NOT IN operator for this type of condition. The query in this figure shows how to use the greater than operator with the 
ALL keyword. Here, the subquery selects the invoice_total column for all the 
invoices with a vendor_id value of 34. This results in a list of two values. Then, 
the main query retrieves the rows from the Invoices table that have invoice totals 
greater than both of the values returned by the subquery.

### Key Points
- The table at the top of this figure shows how this works.
- Here, the values in 
parentheses 1·epresent the values returned by the query.
- If you use the greater than operator(>), the expression must be greater than 
the maximum value returned by the subquery.
- Conversely, if you use the less 
than operator ( < ), the expression must be less than the minimum value returned 
by the subquery.
- If you use the equal operator ( = ), all of the values returned by 
the subquery must be the same and the expression must be equal to that value.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Aggregate Functions

**Definition:** • 
This query uses comments to clearly identify its three queries.

### Explanation
How to l·ode subqueries 
A complex query that uses three subqueries 
SELECT tl.vendor_ state, vendor_name, tl.sum of invoices 
FROM 
( 
) tl 
-- invoice totals by vendor 
SELECT vendor_ state, vendor_name, 
SUM(invoice_total) AS sum_of_ invoices 
FROM vendors v JOIN invoices i 
ON v.vendor_ id = i.vendor_ id 
GROUP BY vendor_ state, vendor_ name 
JOIN 
( 
-- top invoice totals by state 
SELECT vendor_ state, 
MAX(sum_of_ invoices) AS sum_of_ invoices 
FROM 
( 
) t2 
-- invoice totals by vendor 
FROM vendors v JOIN invoices i 
ON v.vendor id= i.vendor id 
GROUP BY vendor_ state, vendor_name 
GROUP BY vendor_state 
) t3 
ON tl.vendor_ state = t3.vendor_ state AND 
tl.sum of invoices= t3.sum of invoices 
ORDER BY vendor_ state 
The result set 
I vendor _state 
► 
AZ 
CA 
I~ 
(10 rows) 
Description 
vendor _name 
\ft/eDs Fargo Bank 
Digital Dreamworks 
Reiter's Scientific &.Pro Books 
Dean \!'Jitter Reynolds 
sum_of _invoices 
662.00 
7125.34 
600.00 
1367.50 
• 
This query retrieves the vendor from each state that has the largest invoice total.

To 
do that, it uses three subqueries. • 
This query uses comments to clearly identify its three queries. • 
The subqueries named tl and t2 return the same result set. This result set includes 
the vendor state, name, and sum of invoices. • 
The subquery named t3 returns a result set that includes the vendor state and the 
largest sum of invoices for any vendor in that state. To do that, this subquery uses a 
nested subquery named t2.

• 
The subqueries named tl and t3 are joined on both the vendor_state and st1m_of_invoices 
columns. A complex query that uses subqueries

More SQL skills cts you need them 
A procedure for building complex queries 
To build a complex query like the one in the previous figure, you can use a 
procedure like the one in figure 7-12. To sta1t, you should state the question in 
English so you're clear about what you want the query to answer.

### Key Points
- • 
This query uses comments to clearly identify its three queries.
- • 
The subqueries named tl and t2 return the same result set.
- This result set includes 
the vendor state, name, and sum of invoices.
- • 
The subquery named t3 returns a result set that includes the vendor state and the 
largest sum of invoices for any vendor in that state.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## GROUP BY Clause

**Definition:** • 
Numbers that don't include a decimal point are known as integers.

### Explanation
Clzapter 8 
How to work with data types 
Data types 
Category 
Description 
Character 
Numeric 
Date and time 
Large Object (LOB) 
Spatial 
JSON 
Description 
Strings of character data 
Numbers that don't include a decimal point (integers) and 
numbers that include a decimal point (real numbers) 
Dates, times, or both 
Large strings of character or binary data 
Geographical values 
JSON documents 
• 
MySQL provides data types for storing many types of data.

• 
Numbers that don't include a decimal point are known as integers. • 
Numbers that include a decimal point are known as real numbers. • 
The date and time data. types are often referred to as the date/time or temporal data 
type.';. • 
The large object (LOB) data types are ·useful for storing images, sound, video, and 
large amounts of text. • 
The spatial data types are useful for storing geometric or geographical values 
such as global positioning system (GPS) data.

These data types are referred to as 
geometry types. • 
The ISON data type is used for storing JavaScript Object Notation (ISON) 
documents. Data type overview

More SQL skills cts you need them 
The character types 
MySQL: CHAR and VARCHAR. These data types store strings of characters. You use the CHAR type to store fixed-length st1·ings. Data stored using this 
data type always occupies the same number of bytes regardless of the actual 
le·ngth of the string.

### Key Points
- • 
Numbers that don't include a decimal point are known as integers.
- • 
Numbers that include a decimal point are known as real numbers.
- types are often referred to as the date/time or temporal data 
type.';.
- • 
The large object (LOB) data types are ·useful for storing images, sound, video, and 
large amounts of text.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## HAVING Clause

**Definition:** Otherwise, the 
column is assigned an empty string.

### Explanation
Clzapter 8 
How to work with data types 
The ENUM and SET types 
Type 
Bytes 
Description 
ENUM 
SET 
1-2 
1-8 
Stores one value selected from a list of acceptable values. Stores zero or more values selected from a list of acceptable values. How values are stored in ENUM columns 
Stored in column 
Value 
ENUM ('Yes', 'No', 'Maybe') 
'Yes' 
'No' 
'Maybe' 
'Possibly' 
'Yes' 
'No' 
'Maybe' 
I 
I 
How values are stored in SET columns 
Value 
'Pepperoni• 
'Mushrooms' 
'Pepperoni, Bacon• 
'Olives, Pepperoni' 
Description 
Stored in column 
SET ('Pepperoni', 'Mushrooms', 'Olives') 
'Pepperoni' 
'Mushrooms' 
'Pepperoni' 
'Pepperoni, Olives' 
• 
The ENUM and SET types can be used to restrict the values that you store to a 
li1nited set of values.

Tl1e ENUM column can take on exactly one value, but a SET 
colt1mn can take on zero, one, or up to 64 different values. • 
You can defme the set of acceptable values for an ENUM or SET column when you 
create a table. An ENUM column can have up to 65,535 acceptable values, but a 
SET column is limited to 64 acceptable values. • 
To specify a value for· an ENUM column, you code a single text string.

If the string 
contains an acceptable value, that value is stored in the column. Otherwise, the 
column is assigned an empty string. • If you don't specify a value for an ENUM column when you insert a row, MySQL 
assigns a default value that depends on whether the column allows null values. If 
the column allows null values, MySQL assigns a null value to the column. If it 
doesn't allow null values, MySQL assigns the first value in the set of acceptable 
values to the column.

### Key Points
- Stores zero or more values selected from a list of acceptable values.
- Tl1e ENUM column can take on exactly one value, but a SET 
colt1mn can take on zero, one, or up to 64 different values.
- • 
You can defme the set of acceptable values for an ENUM or SET column when you 
create a table.
- An ENUM column can have up to 65,535 acceptable values, but a 
SET column is limited to 64 acceptable values.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Subqueries

**Definition:** How to use functions 
In chapter 3, you we1·e introduced to some of the scalar functions that you 
can use in a SELECT statement.

### Explanation
How to use functions 
In chapter 3, you we1·e introduced to some of the scalar functions that you 
can use in a SELECT statement. Now, this chapter expands on that coverage 
by presenting many more of the scalru: functions, as well as some specialized 
window functions. When you complete this chapter, you'll have a thorough 
understanding of the functions that you can use with MySQL. How to work with string data .............................................

258 
A sut11mary of the string functions .............................................................. 258 
Examples that use string functions ............................................................. 260 
How to sort by a string column that contains numbers ............................... 262 
How to parse a string ..................................................................................

264 
How to work with numeric data ......................................... 266 
How to use the numeric fu nctions .............................................................. 266 
How to searcl1 for floating-point nu111bers ................................................... 268 
How to work with date/time data ...................................... 270 
How to get the current date and time ..........................................................

### Key Points
- Now, this chapter expands on that coverage 
by presenting many more of the scalru: functions, as well as some specialized 
window functions.
- When you complete this chapter, you'll have a thorough 
understanding of the functions that you can use with MySQL.
- How to work with string data .............................................
- 258 
A sut11mary of the string functions ..............................................................
- 258 
Examples that use string functions .............................................................

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Correlated Subqueries

**Definition:** 00000000000000 l 
Description 
• 
Becat1se floating-point values are approximate, you'll want to search for approximate 
values when working with floating-point data types such as the DOUBLE and FLOAT 
types.

### Explanation
How to use functions 
The Float_ Sample table 
float_id 
Roat_value 
► 
o. 999999999999999 
1.000000000000001 
1234.56789012345 
999.0'l'l,qQ209348 
I 
24.04849 
.I 
... A search for an exact value that doesn't include two approximate values 
SELECT* 
FROM float_sample 
WHERE float_value = 1 
I float_id 
float_value 
► r 2 
How to search for approximate values 
Search for a range of values 
SELECT* 
FROM float_ sample 
WHERE float_value BETWEEN 0.99 AND 1.01 
float id -
float_value 
► 
0.999999999999999 
LOOOOOOOOOOOOOO 1 
Search for rounded values 
SELECT* 
FROM float_ sample 
WHERE ROUND(float_value, 2) = 1.00 
float_id 
float_value 
► 
0.

999999999999999 
1. 00000000000000 l 
Description 
• 
Becat1se floating-point values are approximate, you'll want to search for approximate 
values when working with floating-point data types such as the DOUBLE and FLOAT 
types. How to search for floating-point numbers

More SQL skills cts you need them 
How to work with date/time data 
In the topics that follow, you'll learn how to use some of the functions that 
MySQL provides for working with dates and times.

As you'll see, these include 
functions for extracting different parts of a date/time value and for performing 
operations on dates and times. In addition, you '11 learn how to perfor1n different 
types of searches on date/time values. How to get the current date and time 
work. The NOW, CURDATE, and CURTIME functions return the local dates 
and/or times based on your system's clock. However, if a session time zone 
has been set, the value returned by the CURDATE and CURTIME functions is 
adjusted to accommodate that time zone.

### Key Points
- 999999999999999 
1.000000000000001 
1234.56789012345 
999.0'l'l,qQ209348 
I 
24.04849 
.I 
...

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## UNION and UNION ALL

**Definition:** How to use functions 
The contents of the Date_Sample table 
date_id 
start date 
► 
1986-03-0100:00:00 
2006-02-28 00:00:00 
2010-10-3100:00:00 
2018-02-28 10:00:00 
2019-02-28 13:58:32 
2019-03-0109:02:25 
-...

### Explanation
How to use functions 
The contents of the Date_Sample table 
date_id 
start date 
► 
1986-03-0100:00:00 
2006-02-28 00:00:00 
2010-10-3100:00:00 
2018-02-28 10:00:00 
2019-02-28 13:58:32 
2019-03-0109:02:25 
-... A SELECT statement that fails to return a row 
SELECT* 
FROM date_ sample 
WHERE start_date = '2018-02-28' 
L 
date_id 
start_date 
Three techniques for ignoring time values 
Search for a range of dates 
SELECT* 
FROM date_ sample 
WHERE start date >= '2018-02 -28' AND start date < '2018-03- 01' 
date_id 
start_date 
► 
2018-02-28 10:00:00 
Search for month, day, and year integers 
SELECT* 
FROM date_ sample 
WHERE MONTH(start_date } = 2 AND 
DAYOFMONTH(start_ date) = 2 8 AND 
YEAR {start_date} = 2018 
date id -
start_date 
► 
2018-02-28 10:00:00 
Search for a formatted date 
SELECT* 
FROM date_ sample 
WHERE DATE_ FORMAT (start_date, •~a111-%d -%Y' ) = '02 - 28- 2018' 
f 
date ,d 
start date 
► 
2018~2-28 10:00:00 
Description 
• 
You can search for a date in a DATETIME column by searching for a range of 
dates, by using functions to specify the month, day, and year of the date, or by 
searching for a formatted date.

Of these techniques, searching for a range of dates 
is the most efficient. How to search for a date 
I 
.I

More SQL skills cts you need them 
How to search for a time 
When you search for a time value in a DATETIME column without speci-
fying a date component, MySQL automatically uses the default date of January 
1, 1900. That's why the first SELECT statement in figure 9-13 doesn't return a 
row even though one row matches the specified time.

The second SELECT statement shows one way to solve this problem. Here, 
the WHERE clause uses the DATE_FORMAT function to return a string for the 
start_date column in the hh:mm:ss format. Then, the WHERE clause compares 
this string to a literal string of 10:00:00. The third SELECT statement in this figure shows another way to solve this 
problem. This statement works similarly to the second statement, but it uses 
the EXTRACT function to extract an integer that represents the ho1rrs, minutes, 
and seconds in the start_date column.

### Key Points
- Of these techniques, searching for a range of dates 
is the most efficient.
- That's why the first SELECT statement in figure 9-13 doesn't return a 
row even though one row matches the specified time.
- The second SELECT statement shows one way to solve this problem.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Creating Tables

**Definition:** Since the rows are sorted by year for each sales rep, that means that the function 
retrieves the sales rep's sales for the previous year.

### Explanation
How to use functions 
The syntax of the analytic functions 
{FIRST_VALUEILAST_ VALUEINTH_VALUE}(scalar_expression[, numeric_ literal]) 
OVER ([partition_clause) order_clause [frame_ clause)) 
{LEADILAG}{scalar_expression [, offset [, default]]) 
OVER ([partition_clause) order_clause) 
{PERCENT_RANK() ICUME_DIST()} OVER ([partition_clause] order_ clause) 
The columns in the Sales_Reps and Sales_Totals tables 
Column name 
Data type 
rep_id 
rep_first_name 
rep_last_name 
INT 
VARCHAR(50) 
rep_1d 
sales_year 
sales_total 
YEAR 
DECIMAL(9,2) 
A query that uses the FIRST_VALUE, NTH_VALUE, and 
LAST VALUE functions 
SELECT sales__year, CONCAT(rep_ first_name, ' ', rep_ last_ name) AS rep_name, 
sales_total, 
FIRST_VALUE(CONCAT(rep_ first_ name, 
I 
', rep_ last_ name)) 
OVER (PARTITION BY sales__year ORDER BY sales_total DESC) 
AS highest_ sales, 
NTH_VALUE(CONCAT(rep_ first_namA, ' ', rep_ last_~arne), 2) 
RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) 
AS second_highest_ sales, 
LAST_VALUE(CONCAT(rep_ first_ name, ' ', rep_ last_name)) 
AS lowest sales 
FROM sales totals JOIN sales_ reps ON sales_totals.rep_ id = sales_ reps.rep_ id 
rep_name 
highest_sales 
second _highes t_sales 
lowest_sales 
► 
Jonathon lhomas 
1274856.38 
Jonathon Thomas 
Andrew Markasian 
Sonja Martinez 
1032875.48 
978'165.99 
AndrewMarkasian 
1132744.56 
Lydia Kramer 
974853.81 
Andrew Markaslan 
9237'16.85 
L ydla Kramer 
Phillip Winters 
655786.92 
422847,86 
998337.46 
887695.75 
Lydia Kr-amer 
Phiffip Winters 
n443.37 
45182.44 
Description 
• 
The FIRST_ VALUE, LAST_ VALUE, NTH VALUE, LEAD, LAG, PERCENT_RANK, 
and CUME_DIST functions are sometimes referred to as analytic functions.

They were 
introduced with MySQL 8.0. The FIRST_ VALUE, LAST_VALUE, and NTH_ VALUE functions return the first, 
last, and nth value in a sorted set of values. When you use the PARTITION BY 
clause with LAST_ VALUE or NTH_VALUE, you typically include the ROWS or 
RANGE clause as well to defme a subset of the current partition. How to use the analytic functions (part 1 of 2)

More SQL skills cts you need them 
The LEAD and LAG functions let you refer to values in other rows of the 
result set.

The LAG function is illustrated by the first exa1nple in part 2 of figure 
9-18. Here, the OVER clause is used to group the result set by the rep_id column 
and sort it by the sales_year column. Then, the LAG function in the fourth 
column gets the sales total from one row prior to the current row (the offset). Since the rows are sorted by year for each sales rep, that means that the function 
retrieves the sales rep's sales for the previous year.

### Key Points
- The FIRST_ VALUE, LAST_VALUE, and NTH_ VALUE functions return the first, 
last, and nth value in a sorted set of values.
- When you use the PARTITION BY 
clause with LAST_ VALUE or NTH_VALUE, you typically include the ROWS or 
RANGE clause as well to defme a subset of the current partition.
- How to use the analytic functions (part 1 of 2)

More SQL skills cts you need them 
The LEAD and LAG functions let you refer to values in other rows of the 
result set.
- The LAG function is illustrated by the first exa1nple in part 2 of figure 
9-18.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Altering Tables

**Definition:** You can also use a 
CASE ( computer-aided software engineering) tool if one is available to you.

### Explanation
Hovv to design a database 
Possible tables and columns for an accounts payable system 
Vendors 
Invoices 
Invoice line items 
Vendor name 
Vendor address 
Vendor city 
Vendor state 
Vendor zip code 
Vendor phone number 
Vendor fax nutuber 
Vendor web address 
Vendor contact first name 
Vendor contact last name 
'Vendor contact phone 
Vendor AR first name 
Vendor AR last name 
Vendor AR phone 
Terms* 
Account number* 
Description 
Invoice number* 
Invoice number* 
Invoice date 
Item part number 
Terms* 
Item quantity 
Invoice total 
Item description 
Payment date 
Item unit price 
Paymerit total 
Item extension 
Invoice due date 
Accoun.t nu,nber* 
Credit total 
Sequence number 
Accoi,nt number* 
• 
After you identify and subdivide all of the data elements for a database, you should 
group them by the entities with which they're associated.

These entities will later 
become the tables of the database, and the elements will become the columns. • 
If a data element relates to more than one entity, you can include it under all of the 
entities it relates to. Then, when you normalize the database, you may be able to 
remove the duplicate elements. • 
As you assign the elements to entities, you should omit elements that aren't needed, 
and you should add any additional elements that are needed.

The notation used in this figure 
• 
Data elements that were previously identified but aren't needed are crossed out. • 
Data elements that were added are displayed in italics. • 
Data elements that are related to two or more entities are followed by an asterisk. • 
You can use a similar notation or develop one of your own. You can also use a 
CASE ( computer-aided software engineering) tool if one is available to you.

### Key Points
- These entities will later 
become the tables of the database, and the elements will become the columns.
- • 
If a data element relates to more than one entity, you can include it under all of the 
entities it relates to.
- Then, when you normalize the database, you may be able to 
remove the duplicate elements.
- • 
As you assign the elements to entities, you should omit elements that aren't needed, 
and you should add any additional elements that are needed.
- The notation used in this figure 
• 
Data elements that were previously identified but aren't needed are crossed out.

### Examples
**Example:**
```sql
-- See textbook for complete examples
```
Code examples available in the source material

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Constraints

**Definition:** Instead, each column must contain a single, scalar value.

### Explanation
Hovv to design a database 
The invoice data with a column that contains repeating values 
vendor _name 
lnvoice_number 
it:em_desaipbon 
► 
Cahners Publishing 
Android ad, MySQL ad, Library directory 
Zylka Design 
97/522 
Catalogs, MySQL Flyer 
Zylka Design 
97/ 5-n:3 
Card revision 
The invoice data with repeating columns 
vendor_name 
invotce number 
item_c:lesaiption_l 
item_desaiption_2 
ltem_c:lescription_ 3 
► Cahners Pubfishing 
Android ad 
MySQLad 
Library directory 
Zylka Design 
97/552 
Catalogs 
MySQL flyer 
cm,, 
Zyfka Design 
97/ SSE 
Card revision 
IH~!I 
w•l!I 
= 
= 
The invoice data in first normal form 
vendor _name 
invoice_number 
,tern_ descnption 
► 
Cahners Publishing 
Android ad 
Cahners Publishlng 
MySQLad 
Cahners Publishing 
Library directory 
Zylka Design 
97/5-22 
Catalogs 
Zylka Design 
97/522 
MySQL flyer 
ZyikaDeslgn 
97/5338 
Card revision 
= 
Description 
• 
For a table to be in first normal for1n, its columns must not contain repeating 
values.

Instead, each column must contain a single, scalar value. In addition, the 
table must not contain repeating columns that represent a set of values. • 
A table in first normal form often bas repeating valt1es in its rows. This can be 
resolved by applying the second normal form. Database design and impleme11,tation, 
How to apply the second normal form 
normal form, every column in a table that isn't a key column must be dependent 
on the entire primary key.

This form only applies to tables that have composite 
primary keys, which is often the case when you start with data that is completely 
unnormalized. The table at the top of this figure, for example, shows the invoice 
data in first normal form after key columns have been added. In this case, the 
primary key consists of the invoice_id and invoice_sequence columns. The 
invoice_sequence column is needed to uniquely identify each line item for an 
• 
• 
1nvo1ce.

### Key Points
- Instead, each column must contain a single, scalar value.
- In addition, the 
table must not contain repeating columns that represent a set of values.
- • 
A table in first normal form often bas repeating valt1es in its rows.
- This can be 
resolved by applying the second normal form.
- Database design and impleme11,tation, 
How to apply the second normal form 
normal form, every column in a table that isn't a key column must be dependent 
on the entire primary key.

### Examples
**SQL Example 1:**
```sql
create a model from that script. To do that, you can click the 0 icon to the right of the Models heading and select the ''Create EER Model from Script'' iten1. Then, you can use the resulting dialog box to select the script file. Hovv to design a database The Models tab of the MySQL Workbench Home page ■ MySQl. Workbench D X File Edit View Database T DOis Scripting Help Models 0@ 0 om ap c::I C;
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Views

**Definition:** Once you 
understand these skills, it's easy to learn how to use a graphical user interface 
such as MySQL Workbench to work with database objects such as tables and 
indexes.

### Explanation
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

### Key Points
- Once you 
understand these skills, it's easy to learn how to use a graphical user interface 
such as MySQL Workbench to work with database objects such as tables and 
indexes.
- For example, it's often useful to view these database objects before 
writing the SELECT, INSERT, UPDATE, or DELETE statements that use them.
- Then, click on the Columns tab at the bottom of the window.
- For example, this figure shows the columns for the Invoices table.

### Examples
**SQL Example 1:**
```sql
create databases, tables, and indexes The SQL script that creates the AP database CREATE TABLE ( • • invoices invoice_ id vendor_ id invoice_number invoice_date invoice_ total payment_ total credit_ total INT PRIMARY KEY ) ;
```
Example SQL query

**SQL Example 2:**
```sql
create an index CREATE INDEX invoices_ invoice date ix ON invoices (invoice_date DESC);
```
Example SQL query

**SQL Example 3:**
```sql
drop existing keys. The foreign keys for the Invoices table ■ MySQl. Workbench D X 1.oca1 IMlance MySOLSO x File Edit Vtew Query Database Server Tools Scripting Help ouerv 1 il:1·\Hftlffll,;
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Stored Procedures

**Definition:** How to create views 
As you've seen throughout this book, SELECT queries can be complicated, 
particularly if they use multiple joins, subqueries, or complex functions.

### Explanation
How to create views 
As you've seen throughout this book, SELECT queries can be complicated, 
particularly if they use multiple joins, subqueries, or complex functions. Because of that, you may want to save the queries you use regularly. One way 
to do that is to store the statement in a script. Another way is to create a view. Unlike scripts, which are stored in files, views are stored as part of the 
database.

As a result, they can be used by SQL programmers and by custom 
applications that have access to the database. This provides some advantages 
over using tables directly. An introduction to views .................................................... 382 
How views work ........................................................................................... 382 
Benefits of using views .................................................................................

384 
How to work with views ..................................................... 386 
How to c·reate a view .................................................................................... 386 
How to create an updatable view ................................................................. 390 
How to use the WITH CHECK OPTION clause ........................................ 392 
How to insert or delete rows through a view ...............................................

### Key Points
- Because of that, you may want to save the queries you use regularly.
- One way 
to do that is to store the statement in a script.
- Unlike scripts, which are stored in files, views are stored as part of the 
database.
- As a result, they can be used by SQL programmers and by custom 
applications that have access to the database.

### Examples
**SQL Example 1:**
```sql
WITH CHECK OPTION clause CREATE OR REPLACE VIEW vendor_payment AS SELECT vendor_name, invoice_ number, invoice_date, payment_date, invoice_ total, credit_total, payment_total WHERE invoice_total - payment_total - credit_total >= 0 WITH CHECK OPTION A SELECT statement that displays a row from the view SELECT* FROM vendor_payment WHERE invoice_ DtJmh~r = 'P-0608' The result set vendor _name ► MaDoy Lithographing Inc invoice _number P-0608 invoice date payment_date 2018-0 7 _23;
```
Example SQL query

**SQL Example 2:**
```sql
UPDATE statement that updates the view UPDATE vendor_payment SET payment_total = 400.00, payment_date = '2018-08-01' WHERE invoice_ numher = 'P-0608' The response from the system (1 row affected) The same row data after the update credit_total 1200.00 payment_total 0.00 invoice_number invoice_date 2018-07-23 2018-08-01 1200. 00 .WO. 00 An UPDATE statement that attempts to update the view SET payment_ total = 30000.00, WHERE invoice_number = 'P-0608';
```
Example SQL query

**SQL Example 3:**
```sql
delete or update a parent row: a foreign key constraint fails ('ap'.'invoice_line_items', CONSTRAINT 'line_ items_fk_invoices' FOREIGN KEY ( 'invoice_id' ) REFERENCES 'invoices' { ' invoice id• ) ) Two DELETE statements that succeed DELETE FROM invoice_ line_ items WHERE invoice_ id = (SELECT invoice_ id FROM WHERE invoice number= DELETE FROM ihm invoices WHERE invoice_n11mher = • QS45443';
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Stored Functions

**Definition:** • 
To delete a view from the database, use the DROP VIEW statement.

### Explanation
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

### Key Points
- • 
To delete a view from the database, use the DROP VIEW statement.
- How to alter or drop a view

Database design and impleme11,tation, 
Perspective 
In this chapter, you learned how to create and use views.
- As you've seen, 
views provide a powerful and flexible way to predefine the data that can be 
retrieved from a database.
- By using them, you can restJ.ict the access to a 
database while providing a consistent and simplified way for end t1sers and 
application programs to access that data.
- Terms 
• 
view 
nested view 
updatable view 
read-only view 
base table 
viewed table 
Exercises 
1.

### Examples
**SQL Example 1:**
```sql
with the USE statement, which selects the AP database. Then, the DROP PROCEDURE IF EXISTS command drops the procedure named test if it already exists. This suppresses any error messages that would be displayed if you attempted to drop a procedure that didn't exist. The DELIMITER statement changes the delimiter from the default delimiter of the semicolon(;
```
Example SQL query

**SQL Example 2:**
```sql
CREATE PROCEDURE statement, and it allows you to use two front slashes(//) to identify the end of the CREATE PROCEDURE state- ment. Although we use two front slashes as the delimiter in this book, it's also common to see two dollar signs ($$) or two semicolons (;
```
Example SQL query

**SQL Example 3:**
```sql
DELETE state- ment on a specified table. ls executed at a scbeduJed time. USE ap;
```
Example SQL query

**SQL Example 4:**
```sql
DROP PROCEDURE IF EXISTS test;
```
Example SQL query

**SQL Example 5:**
```sql
CREATE PROCEDURE test() BEGIN DECLARE sum_balance_ due_var DECIMAL (9, 2);
```
Example SQL query

**SQL Example 6:**
```sql
SELECT SUM(invoice_total - payment_total - credit_total ) INTO sum_balance_ due_var FROM invoices WHERE vendor_id = 95;
```
Example SQL query

**SQL Example 7:**
```sql
SELECT CONCAT('Balance due: $', sum_balance_due_var) AS message;
```
Example SQL query

**SQL Example 8:**
```sql
SELECT 'Balance paid in full' AS message;
```
Example SQL query

**SQL Example 9:**
```sql
SELECT statement to return a result set that indicates the balance that is due. Otherwise, the statement in the ELSE clause uses a SELECT statement to return a result set that indicates that the balance is paid in full. After the stored procedure has been created, this script uses the DELIMTER state1nent to change the delimiter back to the default deli1niter of a se1nicolon (;
```
Example SQL query

**SQL Example 10:**
```sql
CREATE PROCEDURE statement that are necessary to create the stored procedure. Before you execute these statements, you may need to select the appropriate database and drop any procedures with the same name as shown in figure 13-1. Sitnilarly, after you execute these statements, the stored procedure isn't executed until you call it as shown in figure 13-1. A stored procedure that displays a message DELIMITER// CREATE PROCEDURE test() BEGIN SELECT 'This is a test.' AS message;
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Triggers

**Definition:** How to declare and set variables

Stored prvgram development 
How to code IF statements 
statements based on a value that's returned by a Boolean expression.

### Explanation
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

### Key Points
- .I 
• 
A variable must have a name that's different from the names of any columns used 
in any SELECT statement within the stored program.
- To distinguish a variable from 
a column, you can add a suffix like ''_ var'' to the variable name.
- How to declare and set variables

Stored prvgram development 
How to code IF statements 
statements based on a value that's returned by a Boolean expression.
- A Boolean 
expression is an expression that returns a true value or a false value.
- The script in this figure uses an IF statement to test the value of a variable.

### Examples
**SQL Example 1:**
```sql
SELECT column_ l[, column_ 2] ••• INTO variable_ name_ l[, variable_name_ 2] ••• A stored procedure that uses variables DELIMITER/ / CREATE PROCEDURE test() BEGIN DECLARE max_ invoice_total DECLARE min invoice total DECLARE percent_difference DECLARE count_ invoice id DECLARE vendor id var SET vendor_ id_var = 95;
```
Example SQL query

**SQL Example 2:**
```sql
SELECT MAX(invoice_total), MIN(invoice_total), COUNT(invoice_ id) INTO max_ invoice_total, min_ invoice_total, count_ invoice_ id FROM invoices WHERE vendor_ id = vendor_ id_var;
```
Example SQL query

**SQL Example 3:**
```sql
SELECT CONCAT('$', max_ invoice_total) AS 'Maximum invoice', CONCAT('$', min_ invoice_total) AS 'Minimum invoice•, CONCAT(' %', ROUND (percent_difference, 2 ) ) AS 'Percent difference', count invoice id AS 'Number of invoices';
```
Example SQL query

**SQL Example 4:**
```sql
SELECT 'Outstanding invoices are overdue!';
```
Example SQL query

**SQL Example 5:**
```sql
SELECT 'No invoices are overdue.';
```
Example SQL query

**SQL Example 7:**
```sql
CREATE PROCEDURE test() BEGIN DECLARE first invoice due date DATE;
```
Example SQL query

**SQL Example 8:**
```sql
SELECT MIN(invoice_ due_date) INTO first_ invoice_ due_date FROM invoices WHERE invoice_ total - payment_total - credit_total > O;
```
Example SQL query

**SQL Example 9:**
```sql
SELECT •outstanding invoices are overdue!';
```
Example SQL query

**SQL Example 10:**
```sql
SELECT •outstanding invoices are due today!';
```
Example SQL query

**SQL Example 11:**
```sql
SELECT (•outstanding invoices are overdue!');
```
Example SQL query

**SQL Example 12:**
```sql
SELECT ('Outstanding invoices are due today!');
```
Example SQL query

**SQL Example 13:**
```sql
SELECT ('No invoices are overdue.');
```
Example SQL query

**SQL Example 14:**
```sql
CREATE PROCEDURE test(} BEGIN DECLARE terms_ id_var INT;
```
Example SQL query

**SQL Example 15:**
```sql
SELECT terms_id INTO terms_ id_ var FROM invoices WHERE invoice_ id = 4;
```
Example SQL query

**SQL Example 16:**
```sql
SELECT 'Net due 10 days• AS Terms;
```
Example SQL query

**SQL Example 17:**
```sql
SELECT 'Net due 20 days• AS Terms;
```
Example SQL query

**SQL Example 18:**
```sql
SELECT 'Net due 30 days' AS Terms;
```
Example SQL query

**SQL Example 19:**
```sql
SELECT 'Net due more tha.n 3 0 days ' AS Terms;
```
Example SQL query

**SQL Example 20:**
```sql
CREATE PROCEDURE test( ) BEGIN DECLARE i INT DEFAULT 1;
```
Example SQL query

**SQL Example 21:**
```sql
SELECT s AS message;
```
Example SQL query

**SQL Example 22:**
```sql
update as the stored procedure in this figure with this UPDATE statement: UPDATE invoices SET credit_total = credit_total + (invoice_total * .1) WHERE invoice_total - payment_total - credit_total > 0 AND invoice_total > 1000 However, if you encounter a situation where it makes sense to use a cursor, the skills presented in this figure should help you do that. The syntax Declare a cursor DECLARE cursor_ name CURSOR FOR select_statement;
```
Example SQL query

**SQL Example 23:**
```sql
CREATE PROCEDURE test() BEGIN DECLARE invoice_ id_var DECLARE invoice total var DECLARE row_not_ found DECLARE update_count INT;
```
Example SQL query

**SQL Example 24:**
```sql
SELECT invoice_ id, invoice_total FROM invoices WHERE invoice_total - payment_total - credit total> O;
```
Example SQL query

**SQL Example 25:**
```sql
UPDATE invoices SET credit_total = credit_total + (invoice total* .1) WHERE invoice id= invoice_ id_var;
```
Example SQL query

**SQL Example 26:**
```sql
SELECT CONCAT{update_count, ' row(s) updated.');
```
Example SQL query

**SQL Example 27:**
```sql
SELECT statement to retrieve data and no data is found. Occurs when any error condition other than the NOT FOUND condition occtrrs. condition occurs or when any warning messages occur. The syntax for declaring a condition handler DECLARE {CONTINUE jEXIT} HANDLER FOR {mysql_error_ codelSQLSTATE sqlstate_ code lnamed_condition} handl er_ ac tions;
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Events

**Definition:** How to use a condition handler (part 1 of 2)

Stored prvgram development 
The first stored procedure in part 2 shows how to exit the current block 
of code as soon as an error occurs.

### Explanation
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

### Key Points
- How to use a condition handler (part 1 of 2)

Stored prvgram development 
The first stored procedure in part 2 shows how to exit the current block 
of code as soon as an error occurs.
- To start, this stored procedure begins by 
declaring a variable named duplicate_entry _for_key just like the stored proce-
dure in part 1.
- Then, it uses the BEGIN and END keywords to nest a block of 
code within the block of code for the procedu1·e.
- Within the nested block of code, 
the frrst statement declares a condition handler for the MySQL error with a code 
of 1062.

### Examples
**SQL Example 1:**
```sql
CREATE PROCEDURE test() BEGIN INSERT INTO general_ ledger_ accounts VALUES (130, 'Cash');
```
Example SQL query

**SQL Example 2:**
```sql
SELECT '1 row was inserted.';
```
Example SQL query

**SQL Example 3:**
```sql
CREATE PROCEDURE test() BEGIN DECLARE duplicate_entry_ for_key TINYINT DEFAULT FALSE;
```
Example SQL query

**SQL Example 4:**
```sql
INSERT INTO general_ ledger_accounts VALUES (130, 'Cash');
```
Example SQL query

**SQL Example 5:**
```sql
SELECT 'Row was not inserted - duplicate key encountered.' AS message;
```
Example SQL query

**SQL Example 6:**
```sql
SELECT '1 row was inserted.' AS message;
```
Example SQL query

**SQL Example 7:**
```sql
CREATE PROCEDURE test() BEGIN BEGIN DECLARE EXIT HANDLER FOR 1062 END;
```
Example SQL query

**SQL Example 8:**
```sql
CREATE PROCEDURE test() BEGIN DECLARE sql_ error TINYINT DEFAULT FALSE;
```
Example SQL query

**SQL Example 9:**
```sql
SELECT 1 1 row was inserted.' AS message;
```
Example SQL query

**SQL Example 10:**
```sql
SELECT 'Row was not inserted - SQL exception encountered.' AS message;
```
Example SQL query

**SQL Example 11:**
```sql
INSERT statement. For example, if you enter a third column with a value of 'xx', the stored procedure executes the condition handler for the SQLEXCEPTION condition. A stored procedure that uses multiple condition handlers DELIMITER// CREATE PROCEDURE test() BEGIN DECLARE colwnn_cannot_be_null TINYINT DEFAULT FALSE;
```
Example SQL query

**SQL Example 12:**
```sql
INSERT INTO general_ ledger_ accounts VALUES (NULL, 'Test');
```
Example SQL query

**SQL Example 13:**
```sql
SELECT 'Row was not inserted - colwnn cannot be null.' AS message;
```
Example SQL query

**SQL Example 14:**
```sql
SELECT 'Row was not inserted - END IF;
```
Example SQL query

**SQL Example 15:**
```sql
update increases the balance in the savings account. Then, if one of these updates fails, the customer either gains or loses the amount of the transaction. But here again, treating the two updates as a single transaction solves this problem. Usually, that's what you want. How to use transactions and locking A stored procedure that runs three INSERT statements as a transaction DELIMITER// CREATE PROCEDURE test(} BEGIN DECLARE CONTINUE HANDLER FOR SQLEXCEPTION SET sql_ error = TRUE;
```
Example SQL query

**SQL Example 16:**
```sql
INSERT INTO invoices VALUES ( 115, 34, • ZXA-080 •, • 2018-01-18', 14092. 59, 0, 0, 3, '2018-04-18', NULL};
```
Example SQL query

**SQL Example 17:**
```sql
INSERT INTO invoice_ line_ items VALUES (115, 1, 160, 4447.23, 'HW upgrade');
```
Example SQL query

**SQL Example 18:**
```sql
SELECT 'The transaction was committed.';
```
Example SQL query

**SQL Example 19:**
```sql
SELECT 'The transaction was rolled back.';
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Transactions

**Definition:** Since each transaction is unaware 
of the other, the later update overwrites the earlier update.

### Explanation
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

### Key Points
- Since each transaction is unaware 
of the other, the later update overwrites the earlier update.
- Occur when a transaction selects data that l1asn 't been committed by 
another transaction.
- For example, transaction A cha11ges a row.
- Tra11saction 
B then selects the changed row before transaction A commits the change.
- If transaction A then rolls back the change, transaction B has selected data 
that doesn't exist in the database.

### Examples
**SQL Example 1:**
```sql
SELECT statement in transaction B is executed. This returns four rows with rep_id values of 1, 2, 3, and 4. Four transactions that show how to work with locking reads Transaction A -- Execute each statement one at a time. - - Al tern.ate with Transactions B, C, and D as described. START TRANSACTION;
```
Example SQL query

**SQL Example 2:**
```sql
with rep_ id of 2 in parent table ---- SELECT* FROM sales_ reps WHERE rep_ id = 2 FOR SHARE;
```
Example SQL query

**SQL Example 3:**
```sql
insert row with rep_ id of 2 into child table INSERT INTO sales_ totals (rep_ id, sales_year, sales_ total) VALUES (2, 2019, 138193.69);
```
Example SQL query

**SQL Example 4:**
```sql
SELECT * FROM sales_reps WHERE rep_id < 5 FOR UPDATE';
```
Example SQL query

**SQL Example 6:**
```sql
update the same resources, code the updates in the same order in each transaction. UPDATE statements that illustrate deadlocking Transaction A START TRANSACTION;
```
Example SQL query

**SQL Example 7:**
```sql
UPDATE savings SET balance= balance - transfer_amount;
```
Example SQL query

**SQL Example 8:**
```sql
UPDATE checking SET balance= balance + transfer_amount ;
```
Example SQL query

**SQL Example 9:**
```sql
UPDATE checking SET balance = balance - t r ansf er_ amount ;
```
Example SQL query

**SQL Example 10:**
```sql
UPDATE savings SET balance= balance+ transfer_ amount;
```
Example SQL query

**SQL Example 11:**
```sql
UPDATE savings SET balance = balance+ transfer_ amount;
```
Example SQL query

**SQL Example 12:**
```sql
create stored proce- How to create stored prvcedures and functions The syntax of the CREATE PROCEDURE statement CREATE PROCEDURE procedure_ name ( [parameter_name_ l data_type] [, parameter_name_ 2 data_type] ... ) sql_block A script that creates a stored procedure that updates a table DELIMITER / / CREATE PROCEDURE update_ invoices_credit_total ( invoice_ id_param credit_total_param ) BEGIN INT, DECIMAL(9,2) DECLARE sql_ error TINYINT DEFAULT FALSE;
```
Example SQL query

**SQL Example 13:**
```sql
UPDATE invoices SET credit_total = credit_total_param WHERE invoice id= invoice_ id_param;
```
Example SQL query

**SQL Example 14:**
```sql
CREATE PROCEDURE update_ invoices_credit_ total ( IN invoice_ id_param IN credit_ total_param OUT update_ count ) BEGIN INT, DECIMAL(9,2}, INT SET sql_ error = TRUE;
```
Example SQL query

**SQL Example 15:**
```sql
UPDATE invoices SET credit total= credit_ total_param IF sql_ error = FALSE THEN SET update_count = 1;
```
Example SQL query

**SQL Example 16:**
```sql
SELECT CONCAT('row count: ', @row_ count} AS update_ count;
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Transaction Isolation Levels

**Definition:** • 
To set a default value for a parameter, you can use an IF statement to check if the 
parameter contains a null value.

### Explanation
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

### Key Points
- • 
To set a default value for a parameter, you can use an IF statement to check if the 
parameter contains a null value.
- If it does, you can assign a default value to the 
parameter.
- • 
It's a good programming practice to code your CREATE PROCEDURE statements 
so they list parameters that require values first, fallowed by parameters that allow 
null values.
- This is often refe1Ted to as data validation.

### Examples
**SQL Example 1:**
```sql
create stored prvcedures and functions A CREATE PROCEDURE statement that provides a default value DELIMITER// CREATE PROCEDURE update_ invoices_credit_total ( invoice_ id_param INT, credit_ total_param DECIMAL(9,2) ) BEGIN DECLARE sql_error TINYINT DEFAULT FALSE;
```
Example SQL query

**SQL Example 2:**
```sql
UPDATE invoices SET credit_total = credit_ total_param WHERE invoice id= invoice_ id_param;
```
Example SQL query

**SQL Example 3:**
```sql
UPDATE invoices WHERE invoice_ id = invoice_ id__param;
```
Example SQL query

**SQL Example 4:**
```sql
CREATE PROCEDURE insert_ invoice ( vendor_id_param invoice_ number_param invoice_date_param invoice_ total_param terms_id_param invoice_due_date_param INT, VARCHAR(SO), DATE, DECIMAL(9,2), INT, ) BEGIN DECLARE terms id var DATE DECLARE invoice_due_date_var DECLARE terms_due_days_var -- Validate paramater values INT;
```
Example SQL query

**SQL Example 5:**
```sql
SELECT default_ terms_ id INTO terms id var FROM vendors WHERE vendor_ id = vendor_ id_param;
```
Example SQL query

**SQL Example 6:**
```sql
SELECT terms_due_days INTO terms_due_days_var FROM terms WHERE terms_ id = terms_ id_var;
```
Example SQL query

**SQL Example 7:**
```sql
SELECT DATE_ADD(invoice_ date_param, INTERVAL terms_due_days_var DAY) INTO invoice_due_date_var;
```
Example SQL query

**SQL Example 8:**
```sql
INSERT INTO invoices (vendor_ id, invoice_nwnber, invoice_date, invoice_ total, terms_id, invoice_due_date) VALUES (vendor_ id_param, invoice_number_param, invoice_date_param, invoice_total_param, terms_ id_var, invoice_due_date_var);
```
Example SQL query

**SQL Example 9:**
```sql
insert 1 row(s) affected A statement that raises an error CALL insert_ invoice(34, 'ZXA-080', '2018-01-18', -14092.59, NULL, NULL) ;
```
Example SQL query

**SQL Example 10:**
```sql
SELECT statement displays the value of the @count variable a.fter it has been set and incremented by the two CALL statements. You can also use the SET statement outside of a stored program to set the value of a user variable. The syntax for setting a user variable SET @variable_name = expression Two stored procedures that work with the same user variable DELIMITER // CREATE PROCEDURE set_global_ count ( count var :INT ) BEGIN SET @count= count_var;
```
Example SQL query

**SQL Example 11:**
```sql
CREATE PROCEDURE increment_ global_ count( ) BEGIN SET @count= @count+ 1;
```
Example SQL query

**SQL Example 12:**
```sql
SELECT statement to the user. Finally, the DEALLOCATE PREPARE state- ment releases the prepared statement. Once a prepared statement is released, it can no longer be executed. A stored procedure that uses dynamic SQL DELIMITER// CREATE PROCEDURE select_ invoices ( min_ invoice_date_param min_ invoice_total_param ) BEGIN DATE, DECIMAL(9,2) DECLARE select clause VARCHAR(200);
```
Example SQL query

**SQL Example 13:**
```sql
SELECT invoice_ id, invoice_ nwnber, invoice_date, invoice total FROM invoices 11 ;
```
Example SQL query

**SQL Example 14:**
```sql
select invoices statement FROM @dynamic_ sql;
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## User Management

**Definition:** Indicates that the function does not produce the same results given 
the same inpt1t values.

### Explanation
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

### Key Points
- Indicates that the function does not produce the same results given 
the same inpt1t values.
- Indicates that the function contains one or more SQL statem.ents 
st1ch as SELECT statements that read data from a database but no 
statements that write data.
- Indicates that the function contains SQL statements such as INSERT, 
UPDATE, and DELETE statements tl1at write data to a database.
- such as SET statements that don't read from or write to a database.

### Examples
**SQL Example 1:**
```sql
DELETE statements tl1at write data to a database. such as SET statements that don't read from or write to a database. This is the default. Indicates that the function doesn't contain SQL statements. A function that gets a random number DELIMITER // CREATE FUNCTION rand_ i nt () RETURNS INT NOT DETERMINISTIC NO SQL BEGIN RETURN ROUND (RAND () * 1000);
```
Example SQL query

**SQL Example 2:**
```sql
SELECT statement that uses the function SELECT rand_ int () AS random_number;
```
Example SQL query

**SQL Example 3:**
```sql
CREATE FUNCTION get_balance_ due ( invoice_id_pararn INT ) RETURNS DECIMAL(9,2 ) DETERMINISTIC READS SQL DATA BEGIN DECLARE balance_ due_var DECIMAL(9,2);
```
Example SQL query

**SQL Example 4:**
```sql
SELECT invoice_total - payment_total - credit_total INTO balance_ due_var FROM invoices WHERE invoice_ id = invoice_ id_param;
```
Example SQL query

**SQL Example 5:**
```sql
drop the get_balance_due function, the get_sum_balance_due function won't work. As a result, yo11 should avoid dropping any database objects that other database objects depend on. The syntax of the DROP FUNCTION statement DROP FUNCTION [IF EXISTS] function_name A statement that creates a function DELIMITER // CREATE FUNCTION get_ swn_balance_due ( vendor_ id_pararn INT ) RETURNS DECIMAL(9,2) DETERMINISTIC READS SQL DATA BEGIN DECLARE swn_ balance_ due_var DECIMAL(9,2);
```
Example SQL query

**SQL Example 6:**
```sql
SELECT SUM(get_balance_due(invoice_ id}) INTO swn_balance_due_var FROM invoices WHERE vendor_ id = vendor_ id_param;
```
Example SQL query

**SQL Example 7:**
```sql
SELECT vendor_ id, invoice_ nwnber, get_balance_due (invoice_ id) AS balance_ due, get_ swn_balance_ due (vendor_ id) AS swn_bala.nce_due FROM invoices WHERE vendor_ id = 37;
```
Example SQL query

**SQL Example 8:**
```sql
DROP FUNCTION get_ swn_ balance_ due;
```
Example SQL query

**SQL Example 9:**
```sql
DROP FUNCTION IF EXISTS get_ swn_balance_ due;
```
Example SQL query

**SQL Example 10:**
```sql
Alter S!ored Procedure. [)fop Stored Procedure. Refresh All SET MESSAGE_TEXT = The invoice_total col~ 111Jst ~ a posi1 Wormatton Procedure: test MYSQL_ERRNO = ;
```
Example SQL query

**SQL Example 11:**
```sql
create triggers and events The syntax of the CREATE TRIGGER statement CREATE TRIGGER trigger_name {BEFOREIAFTER} {INSERTjUPDATEIDELETE} ON table_ name FOR EACH ROW trigger_body A CREATE TRIGGER statement that corrects mixed-case state names DELIMITER// CREATE TRIGGER vendors_before_ update BEFORE UPDATE ON vendors FOR EACH ROW BEGIN SET NEW.vendor_ state = UPPER(NEW.vendor_ state);
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

## Backup and Restore

**Definition:** How to view or drop triggers 
>

Stored prvgram development 
How to work with events 
An event, or scheduled event, is a named database object that executes, or 
fires, according to the event scheduler.

### Explanation
How to create triggers and events 
A statement that lists all triggers in the current database 
SHOW TRIGGERS 
A statement that lists all triggers in the specified database 
SHOW TRIGGERS IN ap 
J Tr19ger 
Event 
Table 
Statement 
Ttming 
Created 
► j involces_after _insert 
INSERT 
invoices 
BEGIN 
INSERT INTO invoices_audit VALUES ... BEGIN DEa.ARE sum_line_jtem_amou,t DEO ... BEGIN 
INSERT INTO invoices_audlt VALUES •.• 
BEGIN SET NEW.

vendor _state = UPPER{NEW •... AFTER 
2018-12-28 ll: 
invoices _befure_upda te 
UPDATE 
Invoices 
BEFORE 
2018-12-28 11: 
involces_after _delete 
DaETE 
Invoices 
AFTER 
2018-12-28 11: 
vendors _before _update 
UPDATE 
vendors 
BEFORE 
2018-12-28 11: 
< 
> 
A statement that lists all triggers in a database that begin with ''ven'' 
SHOW TRIGGERS IN ap LIKE 'ven%' 
Trigger 
Event 
Table 
Statement 
Tuning 
Created 
► 
vendors_before_update 
UPDATE 
vendors 
BEGIN SET NE¥J.vendor_state = UPPER{NEW ....

BEFORE 
2018-12-28 11: 
A statement that drops a trigger 
DROP TRIGGER vendors_before_update 
A statement that drops a trigger only if it exists 
DROP TRIGGER IF EXISTS vendors_before_update 
Description 
• 
To view triggers, use the SHOW TRIGGERS statement. To filter the result set 
that's returned, include an IN clause or a LIKE clat1se. • 
To drop a trigger, use the DROP TRIGGER statement. To be sure a trigger exists 
before it's dropped, include the IF EXISTS keywords.

### Key Points
- BEGIN DEa.ARE sum_line_jtem_amou,t DEO ...
- BEGIN 
INSERT INTO invoices_audlt VALUES •.• 
BEGIN SET NEW.

### Examples
**SQL Example 1:**
```sql
DELETE statement deletes all rows from the Invoices_Audit table that are more than one month old. Like the code for a trigger, the code for an event doesn't have to be coded within a block if it consists of a single statement. In this case, then, the event could have been coded like this: CREATE EVENT one_time_delete_audit_rows ON SCHEDULE AT NOW () + INTERVAL 1 MONTH DO DELETE FROM invoices_audit WHERE action_date < NOW{) - INTERVAL 1 MONTH;
```
Example SQL query

**SQL Example 2:**
```sql
CREATE EVENT statement CREATE EVENT event_name ON SCHEDULE {AT timestamp I EVERY interval [STARTS timestamp] [ENDS timestamp]} DO event_body A CREATE EVENT statement that executes only once DELIMITER// CREATE EVENT one time_delete_audit_rows ON SC.HEDULE AT NOW ( ) + INTERVAL 1 MONTH DO BEGIN DELETE FROM invoices_audit WHERE action_date < NOW() - INTERVAL 1 MONTH;
```
Example SQL query

**SQL Example 3:**
```sql
CREATE EVENT statement that executes every month CREATE EVENT monthly_delete_audit_ rows ON SCHEDULE EVERY 1 MONTH STARTS '2018-06-01' DO BEGIN INTERVAL 1 MONTH;
```
Example SQL query

### Common Mistakes
**❌ Not understanding the concept fully**
**✅ **

---

