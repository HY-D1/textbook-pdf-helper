# OUTER JOIN

## Definition

An introduction to MySQL 
How to work with outer joins 
Although inner joins are the most common type of join, MySQL also 
supports outer joins.

## Explanation

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

**Question:** Practice using OUTER JOIN in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
