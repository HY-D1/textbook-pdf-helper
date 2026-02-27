# HAVING Clause

## Definition

Otherwise, the 
column is assigned an empty string.

## Explanation

Clzapter 8 
How to work with data types 
The ENUM and SET types 
Type 
Bytes 
Description 
ENUM 
SET 
1-2 
1-8 
Stores one value selected from a list of acceptable values. Stores zero or more values selected from a list of acceptable values. How values are stored in ENUM columns 
Stored in column 
Value 
ENUM ('Yes', 'No', 'Maybe') 
'Yes' 
'No' 
'Maybe' 
'Possibly' 
'Yes' 
'No' 
'Maybe' 
I 
I 
How values are stored in SET columns 
Value 
'Pepperoni• 
'Mushrooms' 
'Pepperoni, Bacon• 
'Olives, Pepperoni' 
Description 
Stored in column 
SET ('Pepperoni', 'Mushrooms', 'Olives') 
'Pepperoni' 
'Mushrooms' 
'Pepperoni' 
'Pepperoni, Olives' 
• 
The ENUM and SET types can be used to restrict the values that you store to a 
li1nited set of values.

Tl1e ENUM column can take on exactly one value, but a SET 
colt1mn can take on zero, one, or up to 64 different values. • 
You can defme the set of acceptable values for an ENUM or SET column when you 
create a table. An ENUM column can have up to 65,535 acceptable values, but a 
SET column is limited to 64 acceptable values. • 
To specify a value for· an ENUM column, you code a single text string.

If the string 
contains an acceptable value, that value is stored in the column. Otherwise, the 
column is assigned an empty string. • If you don't specify a value for an ENUM column when you insert a row, MySQL 
assigns a default value that depends on whether the column allows null values. If 
the column allows null values, MySQL assigns a null value to the column. If it 
doesn't allow null values, MySQL assigns the first value in the set of acceptable 
values to the column.

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

**Question:** Practice using HAVING Clause in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
