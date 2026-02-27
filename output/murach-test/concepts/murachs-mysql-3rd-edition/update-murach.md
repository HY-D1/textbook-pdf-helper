# UPDATE Statement

## Definition

• 
MySQL doesn't provide language keywords for full outer joins, but you can 
simulate a full outer join by using the UNION keyword to combine the result sets 
from a left outer join and a right outer join.

## Explanation

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

## Examples

### SQL Example 1

```sql
SELECT clause. Sort the final result set by the account_number column. 7. Use the UNION operator to generate a result set consisting of two columns from the Vendors table: vendor_name and vendor_state. If the vendor is in California, the vendor_state value should be ''CA'';
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

**Question:** Practice using UPDATE Statement in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
