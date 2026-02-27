# UPDATE Statement

## Definition

More SQL skills cts you need them 
How to convert data 
As you work with the various data types, you'll find that you frequently 
need to convert data from one type to another.

## Explanation

More SQL skills cts you need them 
How to convert data 
As you work with the various data types, you'll find that you frequently 
need to convert data from one type to another. Although MySQL performs many 
conversions automatically, it doesn't always perform the conversion the way you 
want. Because of that, you need to be aware of how data conversion works, and 
you need to know when and how to specify the type of conversion you want.

How implicit data conversion works 
Before MySQL can operate on two values, it must convert those values to 
the same data type. To understand how this works, consider the three expressions 
shown in figu.re 8-8. In the first example, the second column joins a string literal of''$'' to the 
invoice_total column, which is defined with the DECIMAL type. As a result, 
MySQL converts the DECIMAL value to its corresponding characters, appends 
those characters to the $ character, and stores them as a CHAR type.

In the second example, the second column divides the INT literal of 989319 
by the VARCHAR type that's stored in the invoice_number column. As a result, 
MySQL attempts to convert the invoice_number column to an INT type before 
it perfor1ns the division operation. If the invoice_number column contains only 
numbers, this works as you would expect. However, if the invoice_number 
column contains letters or special characters, MySQL converts only the numeric 
characters that precede the letters or special characters.

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

**Question:** Practice using UPDATE Statement in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
