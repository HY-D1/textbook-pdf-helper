# INSERT Statement

## Definition

How to retrieve data f rom two or m.ore tables 
The explicit syntax for an outer join 
SELECT select_ list 
FROM table_ l 
{LEFTIRIGHT} [OUTER] JOIN table_ 2 
ON join_condition_ l 
[{LEFTIRIGHT} [OUTER] JOIN table_ 3 
ON join_condition_ 2] ...

## Explanation

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

**Question:** Practice using INSERT Statement in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
