# WHERE Clause and Filtering

## Definition

An introduction to MySQL 
How to use the LIKE and REGEXP operators 
To retrieve rows that match a specific string pattern, or mask, you can use 
the LIKE or REGEXP operators as shown in figure 3-14.

## Explanation

An introduction to MySQL 
How to use the LIKE and REGEXP operators 
To retrieve rows that match a specific string pattern, or mask, you can use 
the LIKE or REGEXP operators as shown in figure 3-14. The LIKE operator is 
an older operator that lets you search for simple string patterns. When you use 
this operator, the mask can contain one or both of the wildcard symbols shown 
in the first table in this figure.

In contrast to the LIKE operator, the REGEXP operator allows you to create 
complex string patterns known as regular expressions. To do that, you can use 
the special characters and constructs shown in the second table in this figure. Although creating regular expressions can be tricky at frrst, they allow you to 
search for virtually any string pattern. In the first example in this figure, the LIKE phrase specifies that all vendors 
in cities that start with the letters SAN should be included in the query results.

Here, the percent sign (%) indicates that any character or characters can follow 
these three letters. So San Diego and Santa Ana are both included in the results. The second example selects all vendors whose vendor name starts with the 
letters COMPU, followed by any one character, the letters ER, and any charac-
ters after that. The vendor names Compuserve and Computerworld both match 
that pattern.

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

**Question:** Practice using WHERE Clause and Filtering in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
