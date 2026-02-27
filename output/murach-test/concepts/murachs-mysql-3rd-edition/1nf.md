# First Normal Form (1NF)

## Definition

Database design and impleme11,tation, 
How to identify the data elements 
The first step for designing a data structure is to identify the data elements 
required by the system.

## Explanation

Database design and impleme11,tation, 
How to identify the data elements 
The first step for designing a data structure is to identify the data elements 
required by the system. You can use several techniques to do that, including 
analyzing the existing system if there is one, evaluating comparable systems, and 
interviewing anyone who will be using the system. One particularly good source 
of information is the documents used by an existing system.

In figure 10-2, for example, you can see an invoice that's used by an 
accounts payable system. We'll use this document as the main source of infor-
mation for the database design presented in this chapte1·. Keep in mind, though, 
that you'll want to use all available resources when you design your own 
database. If you study this document, you' 11 notice that it contains information about 
three different entities: vendors, invoices, and line items.

First, the form itself 
has preprinted info1mation about the vendor who issued the invoice, such as the 
vendor's name and address. If this vendor were to issue another invoice, this 
information wouldn't change. This document also contains specific information about the invoice. Some 
of this information, such as the invoice number, invoice date, and invoice total, 
is general in nature. Although the actL1al information will vary from one invoice 
to the next, each invoice will include this information.

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

**Question:** Practice using First Normal Form (1NF) in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
