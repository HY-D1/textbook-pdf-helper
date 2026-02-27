# Correlated Subqueries

## Definition

How to use the GROUPING function (part 1 of 2)

More SQL skills cts you need them 
Part 2 of figure 6-8 shows another common use for the GROUPING 
function.

## Explanation

How to code sum1ncary queries 
The basic syntax of the GROUPING function 
GROUPING (expression) 
A summary query that uses WITH ROLLUP on a table with null values 
SELECT invoice_date, payment_date, 
SUM(invoice_total) AS invoice_total, 
SUM(invoice_total - credit_total - payment_total) AS balance_due 
FROM invoices 
WHERE invoice_date BETWEEN '2018-07-24' AND 
1 2018-07-31 1 
GROUP BY invoice_date, payment_date WITH ROLLUP 
invoice_date 
payment_date 
Invoice_ total 
balance_ due 
► 
2018-07-24 
0®91 
503.20 
503.20 
2018-07-24 
2018-08-19 
3689.99 
0.00 
2018-07-24 
2018-08-23 
67.00 
0.00 
2018-07-24 
2018-08-27 
23517.58 
0.00 
2018-07-24 
HPJII 
27777.n 
503.20 
2018-07-25 
2018-08-22 
1000.'16 
0,00 
2018-07-25 
l®!I 
1000.-46 
0.00 
2018-07-28 
UQl!I 
90.36 
90.36 
2018-07-28 
HW!I 
90.36 
90.36 
2018-07-30 
2018-09-03 
22.57 
0.00 
2018--0 7-30 
®J!I 
22.57 
o.oo 
2018-07-31 
lllij!i 
10976.06 
10976.06 
~&,;8-07-31 
il®!I 
10976.06 
10976.06 
HW!I 
39867.22 
11569.62 
A query that substitutes literals for nulls in summary rows 
SELECT IF(GROUPI:NG(invoice_ date) = 1 , 'Grand totals', invoice_ date) 
AS invoice_date, 
IF(GROUPI:NG(payment_ date) = 1 , 'Invoice date totals', payment_ date) 
AS payme.nt_date, 
SUM(invoice_total - credit_total - payment_ total) AS balance_ due 
FROM invoices 
1 2018-07-31 1 
J 
invoice_date 
payment_date 
Invoice_ total 
balance _due 
H©il 
► 
2018-07-24 
503.20 
503.20 
2018-07-24 
2018-08-19 
3689.99 
0.00 
2018-07-24 
2018-08-23 
67.00 
o.oo 
2018-07-24 
2018-08-27 
23517.58 
0.00 
2018-07-24 
Invoice date totals 
L777/.77 
503.20 
2018-07-25 
2018-08-22 
1000.-46 
0.00 
2018-07-25 
Invoice date totals 
1000.-46 
0.00 
2018-07-28 
llill!I 
90.36 
90.36 
2018-07-28 
Invoice date totals 
90.36 
90.36 
2018-07-30 
2018-09-03 
22.57 
0.00 
2018-07-30 
Invoice date totals 
22.57 
0.00 
2018-07-31 
Ut!HI 
10976.06 
10976.06 
2018-07-31 
Invoice date totals 
10976.06 
10976.06 
Grand totals 
Invoice date totals 
39867.22 
11569.62 
Description 
• 
The GROUPING function returns 1 if the expression is null because it's in a 
summary row.

Otherwise, it returns 0. How to use the GROUPING function (part 1 of 2)

More SQL skills cts you need them 
Part 2 of figure 6-8 shows another common use for the GROUPING 
function. The query in this example is identical to the second one in part 1 
of this figure, except that it includes a HAVING clause. This clause uses the 
GROUPING function to filter the result set so only the summary rows are 
included.

To do that, it checks if this function returns a value of 1 for the 
invoice_date or payment_date column. How to code sum1n.ary queries 
A query that displays only summary rows 
SELECT IF(GROUPING(invoice_date) = l , 'Grand totals', invoice_date) 
AS invoice_date, 
IF(GROUPING (payment_date) = l , 'Invoice date totals', payment_date) 
AS payment_date, 
SUM(invoice_ total - credit_ total - payment_total) AS balance_due 
FROM invoices 
WHERE invoice_date BETWEEN '2018-07-24' AND '2018-07- 31' 
HAVING GROUPING(invoice date) = 1 OR GROUPING{payment date)
= ~ 
• 
invoice _date 
payment_date 
invoice_total 
balance_due 
► 
2018-07-24 
Invoice date totals 
l.7111.

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

**Question:** Practice using Correlated Subqueries in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
