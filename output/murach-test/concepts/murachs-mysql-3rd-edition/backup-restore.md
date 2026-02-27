# Backup and Restore

## Definition

How to view or drop triggers 
>

Stored prvgram development 
How to work with events 
An event, or scheduled event, is a named database object that executes, or 
fires, according to the event scheduler.

## Explanation

How to create triggers and events 
A statement that lists all triggers in the current database 
SHOW TRIGGERS 
A statement that lists all triggers in the specified database 
SHOW TRIGGERS IN ap 
J Tr19ger 
Event 
Table 
Statement 
Ttming 
Created 
► j involces_after _insert 
INSERT 
invoices 
BEGIN 
INSERT INTO invoices_audit VALUES ... BEGIN DEa.ARE sum_line_jtem_amou,t DEO ... BEGIN 
INSERT INTO invoices_audlt VALUES •.• 
BEGIN SET NEW.

vendor _state = UPPER{NEW •... AFTER 
2018-12-28 ll: 
invoices _befure_upda te 
UPDATE 
Invoices 
BEFORE 
2018-12-28 11: 
involces_after _delete 
DaETE 
Invoices 
AFTER 
2018-12-28 11: 
vendors _before _update 
UPDATE 
vendors 
BEFORE 
2018-12-28 11: 
< 
> 
A statement that lists all triggers in a database that begin with ''ven'' 
SHOW TRIGGERS IN ap LIKE 'ven%' 
Trigger 
Event 
Table 
Statement 
Tuning 
Created 
► 
vendors_before_update 
UPDATE 
vendors 
BEGIN SET NE¥J.vendor_state = UPPER{NEW ....

BEFORE 
2018-12-28 11: 
A statement that drops a trigger 
DROP TRIGGER vendors_before_update 
A statement that drops a trigger only if it exists 
DROP TRIGGER IF EXISTS vendors_before_update 
Description 
• 
To view triggers, use the SHOW TRIGGERS statement. To filter the result set 
that's returned, include an IN clause or a LIKE clat1se. • 
To drop a trigger, use the DROP TRIGGER statement. To be sure a trigger exists 
before it's dropped, include the IF EXISTS keywords.

## Examples

### SQL Example 1

```sql
DELETE statement deletes all rows from the Invoices_Audit table that are more than one month old. Like the code for a trigger, the code for an event doesn't have to be coded within a block if it consists of a single statement. In this case, then, the event could have been coded like this: CREATE EVENT one_time_delete_audit_rows ON SCHEDULE AT NOW () + INTERVAL 1 MONTH DO DELETE FROM invoices_audit WHERE action_date < NOW{) - INTERVAL 1 MONTH;
```

Example SQL query

### SQL Example 2

```sql
CREATE EVENT statement CREATE EVENT event_name ON SCHEDULE {AT timestamp I EVERY interval [STARTS timestamp] [ENDS timestamp]} DO event_body A CREATE EVENT statement that executes only once DELIMITER// CREATE EVENT one time_delete_audit_rows ON SC.HEDULE AT NOW ( ) + INTERVAL 1 MONTH DO BEGIN DELETE FROM invoices_audit WHERE action_date < NOW() - INTERVAL 1 MONTH;
```

Example SQL query

### SQL Example 3

```sql
CREATE EVENT statement that executes every month CREATE EVENT monthly_delete_audit_ rows ON SCHEDULE EVERY 1 MONTH STARTS '2018-06-01' DO BEGIN INTERVAL 1 MONTH;
```

Example SQL query

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

**Question:** Practice using Backup and Restore in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
