# UNION and UNION ALL

## Definition

How to use functions 
The contents of the Date_Sample table 
date_id 
start date 
► 
1986-03-0100:00:00 
2006-02-28 00:00:00 
2010-10-3100:00:00 
2018-02-28 10:00:00 
2019-02-28 13:58:32 
2019-03-0109:02:25 
-...

## Explanation

How to use functions 
The contents of the Date_Sample table 
date_id 
start date 
► 
1986-03-0100:00:00 
2006-02-28 00:00:00 
2010-10-3100:00:00 
2018-02-28 10:00:00 
2019-02-28 13:58:32 
2019-03-0109:02:25 
-... A SELECT statement that fails to return a row 
SELECT* 
FROM date_ sample 
WHERE start_date = '2018-02-28' 
L 
date_id 
start_date 
Three techniques for ignoring time values 
Search for a range of dates 
SELECT* 
FROM date_ sample 
WHERE start date >= '2018-02 -28' AND start date < '2018-03- 01' 
date_id 
start_date 
► 
2018-02-28 10:00:00 
Search for month, day, and year integers 
SELECT* 
FROM date_ sample 
WHERE MONTH(start_date } = 2 AND 
DAYOFMONTH(start_ date) = 2 8 AND 
YEAR {start_date} = 2018 
date id -
start_date 
► 
2018-02-28 10:00:00 
Search for a formatted date 
SELECT* 
FROM date_ sample 
WHERE DATE_ FORMAT (start_date, •~a111-%d -%Y' ) = '02 - 28- 2018' 
f 
date ,d 
start date 
► 
2018~2-28 10:00:00 
Description 
• 
You can search for a date in a DATETIME column by searching for a range of 
dates, by using functions to specify the month, day, and year of the date, or by 
searching for a formatted date.

Of these techniques, searching for a range of dates 
is the most efficient. How to search for a date 
I 
.I

More SQL skills cts you need them 
How to search for a time 
When you search for a time value in a DATETIME column without speci-
fying a date component, MySQL automatically uses the default date of January 
1, 1900. That's why the first SELECT statement in figure 9-13 doesn't return a 
row even though one row matches the specified time.

The second SELECT statement shows one way to solve this problem. Here, 
the WHERE clause uses the DATE_FORMAT function to return a string for the 
start_date column in the hh:mm:ss format. Then, the WHERE clause compares 
this string to a literal string of 10:00:00. The third SELECT statement in this figure shows another way to solve this 
problem. This statement works similarly to the second statement, but it uses 
the EXTRACT function to extract an integer that represents the ho1rrs, minutes, 
and seconds in the start_date column.

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

**Question:** Practice using UNION and UNION ALL in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
