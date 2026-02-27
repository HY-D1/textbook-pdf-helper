# Second Normal Form (2NF)

## Definition

If possible, 
you should use an existing column for the primary key.

## Explanation

Hovv to design a database 
The relationships between the tables in the accounts payable system 
vendors 
• 
• 
1nvo1ces 
invoice line items 
vendor id 
invoice id 
••----
◄ invoice id 
vendor name 
vendor address 
vendor_ city 
vendor state 
vendor_zip_code 
vendor_phone 
vendor contact first name 
vendor contact last name 
terms 
account no 
i.-..a vendor id 
invoice number 
invoice date 
invoice total 
payment_total 
credit total 
terms 
invoice due date 
payment_date 
account no 
Two tables with a many-to-many relationship 
employees 
memberships 
committees 
.

. 1nvo1ce_sequence 
account no 
line _item_ description 
item_quantity 
item_ unit_price 
line item amount 
employee_id ••----
◄ employee_id 
first name 
committee id 
committee id 
committee name 
last name 
Linking table 
Two tables with a one-to-one relationship 
employees 
employee _photos 
employee_id ••--• employee_id 
first_name 
employee_photo 
last name 
Description 
• 
Each table should have a primary key that uniquely identifies each row.

If possible, 
you should use an existing column for the primary key. • 
The values of the primary keys should seldom, if ever, change. The values should 
also be short and easy to enter correctly. • If a suitable column doesn't exist for a p1imary key, you can create an ID column 
that is incremented by one for each new row as the primary key. • If two tables have a one-to-many relationship, you may need to add a foreign key 
column to the table on the ''many'' side.

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

**Question:** Practice using Second Normal Form (2NF) in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
