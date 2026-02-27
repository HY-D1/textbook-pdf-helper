# Creating Tables

## Definition

Since the rows are sorted by year for each sales rep, that means that the function 
retrieves the sales rep's sales for the previous year.

## Explanation

How to use functions 
The syntax of the analytic functions 
{FIRST_VALUEILAST_ VALUEINTH_VALUE}(scalar_expression[, numeric_ literal]) 
OVER ([partition_clause) order_clause [frame_ clause)) 
{LEADILAG}{scalar_expression [, offset [, default]]) 
OVER ([partition_clause) order_clause) 
{PERCENT_RANK() ICUME_DIST()} OVER ([partition_clause] order_ clause) 
The columns in the Sales_Reps and Sales_Totals tables 
Column name 
Data type 
rep_id 
rep_first_name 
rep_last_name 
INT 
VARCHAR(50) 
rep_1d 
sales_year 
sales_total 
YEAR 
DECIMAL(9,2) 
A query that uses the FIRST_VALUE, NTH_VALUE, and 
LAST VALUE functions 
SELECT sales__year, CONCAT(rep_ first_name, ' ', rep_ last_ name) AS rep_name, 
sales_total, 
FIRST_VALUE(CONCAT(rep_ first_ name, 
I 
', rep_ last_ name)) 
OVER (PARTITION BY sales__year ORDER BY sales_total DESC) 
AS highest_ sales, 
NTH_VALUE(CONCAT(rep_ first_namA, ' ', rep_ last_~arne), 2) 
RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) 
AS second_highest_ sales, 
LAST_VALUE(CONCAT(rep_ first_ name, ' ', rep_ last_name)) 
AS lowest sales 
FROM sales totals JOIN sales_ reps ON sales_totals.rep_ id = sales_ reps.rep_ id 
rep_name 
highest_sales 
second _highes t_sales 
lowest_sales 
► 
Jonathon lhomas 
1274856.38 
Jonathon Thomas 
Andrew Markasian 
Sonja Martinez 
1032875.48 
978'165.99 
AndrewMarkasian 
1132744.56 
Lydia Kramer 
974853.81 
Andrew Markaslan 
9237'16.85 
L ydla Kramer 
Phillip Winters 
655786.92 
422847,86 
998337.46 
887695.75 
Lydia Kr-amer 
Phiffip Winters 
n443.37 
45182.44 
Description 
• 
The FIRST_ VALUE, LAST_ VALUE, NTH VALUE, LEAD, LAG, PERCENT_RANK, 
and CUME_DIST functions are sometimes referred to as analytic functions.

They were 
introduced with MySQL 8.0. The FIRST_ VALUE, LAST_VALUE, and NTH_ VALUE functions return the first, 
last, and nth value in a sorted set of values. When you use the PARTITION BY 
clause with LAST_ VALUE or NTH_VALUE, you typically include the ROWS or 
RANGE clause as well to defme a subset of the current partition. How to use the analytic functions (part 1 of 2)

More SQL skills cts you need them 
The LEAD and LAG functions let you refer to values in other rows of the 
result set.

The LAG function is illustrated by the first exa1nple in part 2 of figure 
9-18. Here, the OVER clause is used to group the result set by the rep_id column 
and sort it by the sales_year column. Then, the LAG function in the fourth 
column gets the sales total from one row prior to the current row (the offset). Since the rows are sorted by year for each sales rep, that means that the function 
retrieves the sales rep's sales for the previous year.

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

**Question:** Practice using Creating Tables in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
