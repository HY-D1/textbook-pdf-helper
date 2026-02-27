# Database Indexes

## Definition

How to create databases, tables, and indexes 
The indexes for the Invoices table 
■ 
MySQl.

## Explanation

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

## Examples

### SQL Example 1

```sql
drop existing keys. The foreign keys for the Invoices table ■ MySQl. Workbench D X 1.oca1 IMlance MySOLSO x File Edit Vtew Query Database Server Tools Scripting Help ouerv 1 il:1·\Hftlffll,;
```

Example SQL query

### SQL Example 2

```sql
drop the tables if they already exist. 3. Write INSERT staten1ents that add rows to the tables that are created in exercise 2. Add two rows to the Members table for the first two member IDs. Add two rows to the Committees table for the first two committee IDs. Add three rows to the Members Committees table: one row for member 1 and committee 2;
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

**Question:** Practice using Database Indexes in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
