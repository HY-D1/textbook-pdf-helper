# Constraints

## Definition

Instead, each column must contain a single, scalar value.

## Explanation

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

## Examples

### SQL Example 1

```sql
create a model from that script. To do that, you can click the 0 icon to the right of the Models heading and select the ''Create EER Model from Script'' iten1. Then, you can use the resulting dialog box to select the script file. Hovv to design a database The Models tab of the MySQL Workbench Home page ■ MySQl. Workbench D X File Edit View Database T DOis Scripting Help Models 0@ 0 om ap c::I C;
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

**Question:** Practice using Constraints in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
