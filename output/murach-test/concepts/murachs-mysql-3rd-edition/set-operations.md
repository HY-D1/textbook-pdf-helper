# Set Operations in SQL

## Definition

How to retrieve data 
from a single table 
In this chapter, you'll learn how to code SELECT statements that 1·etrieve data 
from a single table.

## Explanation

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

## Examples

### SQL Example 1

```sql
SELECT statement that retrieves three columns from each row, sorted in descending sequence by invoice total SELECT invoice_number, invoice_date, invoice_ total FROM invoices ORDER BY invoice_total DESC invoice number invoice date invoice total -;
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

**Question:** Practice using Set Operations in SQL in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
