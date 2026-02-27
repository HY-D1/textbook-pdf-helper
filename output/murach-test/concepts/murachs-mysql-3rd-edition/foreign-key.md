# Foreign Key Constraint

## Definition

The seco11d subquery is also used in the FROM clause of the outer query to 
create a result set that's joined with the first result set.

## Explanation

More SQL skills cts you need them 
How to work with complex queries 
So far, the examples you've seen of queries that use subqueries have been 
relatively simple. However, these types of queries can get complicated in a hurry, 
particularly if the subqueries are nested. Because of that, you'll want to be st1re 
that you plan and test these queries carefully. In a moment, you'll learn how to 
do that.

But first, this chapter presents an example of a complex query. A complex query that uses subqueries 
subquery is used in the FROM clause of the outer query to create a result set that 
contains the state, name, and total invoice amount for each vendor in the Vendors 
table. This is the same subquery that was described in figure 7-10. As a result, 
you should already understand how it works. The seco11d subquery is also used in the FROM clause of the outer query to 
create a result set that's joined with the first result set.

This result set contains 
the state and total invoice amount for the vendor in each state that has the largest 
invoice total. To create this result set, a third subquery is nested within the 
FROM clause of the subquery. This subquery is identical to the frrst subquery. After this statement creates the two result sets, it joins them based on the 
columns in each table that contain the state and the total invoice amount.

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

**Question:** Practice using Foreign Key Constraint in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
