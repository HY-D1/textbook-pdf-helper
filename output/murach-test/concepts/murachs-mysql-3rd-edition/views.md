# SQL Views

## Definition

How to use functions 
The EXTRACT function 
Function 
Description 
EXTRACT{unit FROM date) 
Returns an integer that corresponds with the 
specified unit for the specified date/time.

## Explanation

How to use functions 
The EXTRACT function 
Function 
Description 
EXTRACT{unit FROM date) 
Returns an integer that corresponds with the 
specified unit for the specified date/time. Date/time units 
Unit 
Description 
SECOND 
MINUTE 
HOUR 
DAY 
MONTH 
YEAR 
MINUTE_ SECOND 
HOUR_ Ml:NUTE 
DAY_ HOUR 
YEAR_ MONTH 
HOUR_ SECOND 
DAY_ MINUTE 
DAY_ SECOND 
Seconds 
Minutes 
Hours 
Day 
Month 
Year 
Minutes and seconds 
Hour and minutes 
Day and hours 
Year and mo11th 
Hours, min·utes, and seconds 
Day, hours, and minutes 
Day, hours, minutes, and seconds 
Examples that use the EXTRACT function 
Function 
Result 
EXTRACT{SECOND FROM '2018-12-03 11:35:00') 
EXTRACT(MINUTE FROM '2018-12-03 11:35:00') 
EXTRACT(HOUR FROM '2018-12-03 11:35:00') 
EXTRACT(DAY FROM '2018-12-03 11:35:00') 
EXTRACT(MONTH FROM ' 2018-12-03 11:35:00') 
EXTRACT(YEAR FROM '2018-12-03 11:35:00') 
EXTRACT(MINUTE_ SECOND FROM '2018-12-03 11:35:00') 
EXTRACT(HOUR_ Ml:NUTE FROM '2018-12-03 11:35:00' ) 
EXTRACT(DAY_ HOUR FROM '2018-12-03 11:35:00') 
EXTRACT(YEAR_ MONTH FROM '2018-12-03 11:35:00' ) 
EXTRACT(HOUR_ SECOND FROM '2018-12-03 11:35:00') 
EXTRACT(DAY_ MINUTE FROM '2018-12-03 11:35:00') 
EXTRACT(DAY_ SECOND FROM '2018-12-03 11:35:00') 
How to parse dates and times with the EXTRACT function

More SQL skills cts you need them 
How to format dates and times 
and times.

This function accepts two parameters. The first parameter speci-
fies the DATE or DATETIME value that you want to format. Then, the second 
parameter specifies a format string that includes special codes for formatting 
the various parts of the date or time. To use one of these codes within the format 
string, you code the percent sign (%) followed by a single case-sensitive letter. In this figure, for instance, the frrst example uses the %m code to get the 
numeric month, the %d code to get the nume1ic day, and the %y code to get the 
two-digit year.

This example also uses front slashes (/) to separate the month, 
day, and year. The next three examples use other formatting codes, but they work similarly 
to the frrst example. Namely, the for1nat string contains some date/time format-
ting codes to display the different parts of the date. In addition, it contains other 
characters such as spaces, commas, or dashes to separate the different parts of 
the date.

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

**Question:** Practice using SQL Views in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
