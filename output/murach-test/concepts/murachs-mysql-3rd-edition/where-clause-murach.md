# WHERE Clause

## Definition

MYSQL.COM 
OOWNLO.-\DS 
DOCUMENTATION 
DEVELO?ER ZOl~E 
Q.

## Explanation

Cliapter 2 
How to use MySQL Workbench and other develop,nent tools 
The web address for the MySQL 8.0 Reference Manual 
https://dev.rrwsgl.com/doc/refman/8.0/en/ 
A web page from the MySQL Reference Manual 
B MySQL MySQL 8.0 'le!erence 
)( 
+ 
D 
C 
i 
hnps dev.mysql.com oc/refman/8.0/en/manual-1nfo.html 
* e 
= 
The v10rld s most popula Of)"'JI source database 0. Contact MySQL I Login I Register 
MyS~ .

MYSQL.COM 
OOWNLO.-\DS 
DOCUMENTATION 
DEVELO?ER ZOl~E 
Q. A Documentation Home 
MySQL 8.0 Reference Manual 
Preface and Legal Notices 
., General Information 
About This Manual 
Typographical and Syntax Convenoons 
> overview of the MY5QL Database 
Management System 
• What Is New In MySQL 8.0 
• Server and Status vanables and 
opoons Added, Deprecated, or 
Rem011ed jr) MY5QL 8.0 
Description 
MySQL 8.0 Reference Manual I General lnformaOOl'I I About Ths Manua 
version 8.0 
¥ 
1.1 About This Manual 
This 1s the Reference Manual for the MySQL Database System, version 8.0, 
through release 8.0.15.

Differences between minor versions of MySQL 8.0 are 
noted In the present text with reference to release numbers (8.0. x). For license 
1nformatlon, see the Legal Notices . This manual Is not intended for use with older versions of the MySQL software 
due to the many functional and other differences between MY5QL 8.0 and 
previous versions. If you are using an earlier release of the MySQL software, 
please refer to the appropnate manual.

## Examples

### SQL Example 1

```sql
SELECT statement, the MySQL Command Line Client displays a message giving the nu1nber of rows that are included in the result set and the amount of time it took to run the query. In this case, it took less than 1/100 of a second to run the query. Cliapter 2 How to list the names of all databases managed by the server mysql> show databases;
```

Example SQL query

### SQL Example 2

```sql
select a database for use mysql> use ap;
```

Example SQL query

### SQL Example 3

```sql
select data from a database mysql> select vendor_name from vendors limit 5;
```

Example SQL query

### SQL Example 4

```sql
SELECT statement that retrieves three columns from each row, sorted in descending sequence by invoice total SELECT invoice_number, invoice_date, invoice_ total FROM invoices ORDER BY invoice_total DESC invoice number invoice date invoice total -;
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

**Question:** Practice using WHERE Clause in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
