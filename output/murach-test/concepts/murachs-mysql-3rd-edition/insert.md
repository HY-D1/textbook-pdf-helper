# INSERT Statement

## Definition

More SQL skills cts you need them 
The date and time types 
Part 1 of figure 8-5 presents the five date and time types supported by 
MySQL.

## Explanation

More SQL skills cts you need them 
The date and time types 
Part 1 of figure 8-5 presents the five date and time types supported by 
MySQL. You can use the DATE type to store a date without a time. You can 
use the TIME type to store a time without a date. And you can use either the 
DATETIME or TIMESTAMP types to store both a date and a time. You typically use the TIMESTAMP type to keep track of when a row was 
inserted or last updated.

For example, you might use this type to keep track 
of the entries on a blog. MySQL makes that easy by automatically setting the 
TIMESTAMP column to the current date and time whenever a row is inserted or 
updated. If that's not what you want, you can use the DATETIME type instead. The problem with the TIMESTAMP type is that it can only store dates up 
to the year 2038. This is known as the yea,-2038 problem, the Y2K38 probleni, 
and the Unix Millennium bug.

As a result, if you want your database to be able 
to store dates that go beyond 2038, you should use the DATETIME type instead 
of the TIMESTAMP type. Otherwise, you can use the TIMESTAMP type since 
it only reqtrires 4 bytes to store a TIMESTAMP value, compared to 8 bytes for a 
DATETIME value. If you need to store a year without any other temporal data, you can use the 
YEAR type. With MySQL 5.7.5 and later, the YEAR type stores 4-digit years 
from 1901 to 2155.

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

**Question:** Practice using INSERT Statement in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
