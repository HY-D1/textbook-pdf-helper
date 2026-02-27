# GROUP BY Clause

## Definition

Then, the default value or null value is assigned automatically.

## Explanation

Clzapter 5 
How to insert, update, and delete data 
The column definitions for the Color_Sample table 
color_ id 
color_number 
color_name 
INT 
INT 
VARCHAR { 5 0) 
NOT NULL 
NOT NULL 
AUTO_ INCREMENT, 
DEFAULT O, 
Five INSERT statements for the Color_Sample table 
INSERT INTO color_ sample {color_number) 
VALUES {606) 
INSERT INTO color_ sample {color_ namA) 
VALUES {'Yellow') 
INSERT INTO color_ sample 
VALUES {DEFAULT, DEFAULT, 'Orange') 
INSERT INTO color_ sample 
VALUES (DEFAULT, 808, NULL) 
INSERT INTO color_ sample 
VALUES (DEFAULT, DEFAULT, NULL) 
The Color_Sample table after the rows have been inserted 
color Jd 
color _number 
color_name 
► 
UM!I 
Yellow 
Orange 
.q 
"®'' 
H®!I 
Description 
• If a column is defined so it allows null values, you can use the NULL keyword in 
the list of values to insert a null value into that column.

• 
If a column is defined with a default va]11e, you can use the DEFAULT keyword in 
the list of values to insert the default value for t11at column. • If a column is defined as an auto increment column, you can use the DEFAULT 
keyword in the list of values to have MySQL generate the value for the column. • If you include a column list, you can omit columns with default values and null 
values. Then, the default value or null value is assigned automatically.

You can also 
omit an auto increment column. Then, MySQL generates the value for the column. How to insert default values and null values

An introduction to MySQL 
How to use a subquery in an INSERT statement 
A subquery is just a SELECT statement that's coded within another SQL 
statement. Since you ah·eady know how to code SELECT statements, you 
shouldn't have much trouble coding subqueries as described in this chapter.

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

**Question:** Practice using GROUP BY Clause in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
