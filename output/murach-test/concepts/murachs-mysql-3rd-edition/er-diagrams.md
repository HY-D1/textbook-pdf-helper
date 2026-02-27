# ER Diagrams

## Definition

• 
Each column definition also indicates whether or not it can contain null values.

## Explanation

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

## Examples

### Example

```sql
-- See textbook for complete examples
```

Code examples available in the source material

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

**Question:** Practice using ER Diagrams in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
