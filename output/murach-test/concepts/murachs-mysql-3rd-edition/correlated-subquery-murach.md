# Correlated Subqueries

## Definition

00000000000000 l 
Description 
• 
Becat1se floating-point values are approximate, you'll want to search for approximate 
values when working with floating-point data types such as the DOUBLE and FLOAT 
types.

## Explanation

How to use functions 
The Float_ Sample table 
float_id 
Roat_value 
► 
o. 999999999999999 
1.000000000000001 
1234.56789012345 
999.0'l'l,qQ209348 
I 
24.04849 
.I 
... A search for an exact value that doesn't include two approximate values 
SELECT* 
FROM float_sample 
WHERE float_value = 1 
I float_id 
float_value 
► r 2 
How to search for approximate values 
Search for a range of values 
SELECT* 
FROM float_ sample 
WHERE float_value BETWEEN 0.99 AND 1.01 
float id -
float_value 
► 
0.999999999999999 
LOOOOOOOOOOOOOO 1 
Search for rounded values 
SELECT* 
FROM float_ sample 
WHERE ROUND(float_value, 2) = 1.00 
float_id 
float_value 
► 
0.

999999999999999 
1. 00000000000000 l 
Description 
• 
Becat1se floating-point values are approximate, you'll want to search for approximate 
values when working with floating-point data types such as the DOUBLE and FLOAT 
types. How to search for floating-point numbers

More SQL skills cts you need them 
How to work with date/time data 
In the topics that follow, you'll learn how to use some of the functions that 
MySQL provides for working with dates and times.

As you'll see, these include 
functions for extracting different parts of a date/time value and for performing 
operations on dates and times. In addition, you '11 learn how to perfor1n different 
types of searches on date/time values. How to get the current date and time 
work. The NOW, CURDATE, and CURTIME functions return the local dates 
and/or times based on your system's clock. However, if a session time zone 
has been set, the value returned by the CURDATE and CURTIME functions is 
adjusted to accommodate that time zone.

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
