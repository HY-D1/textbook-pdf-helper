# SQL Joins

## Definition

An introduction to MySQL 
How to use compound join conditions 
Although a join condition typically consists of a single comparison, you can 
include two or more co1nparisons in a join condition using the AND and OR 
operators.

## Explanation

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

**Question:** Practice using SQL Joins in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
