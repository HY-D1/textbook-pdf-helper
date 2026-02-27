# Relational Algebra

## Definition

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
FortWashi...

## Explanation

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

**Question:** Practice using Relational Algebra in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
