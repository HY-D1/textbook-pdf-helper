# SELECT Statement

## Definition

Then, select the Columns 
tab at the bottom of the window that's displayed to view the column definitions for 
the table.

## Explanation

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

**Question:** Practice using SELECT Statement in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
