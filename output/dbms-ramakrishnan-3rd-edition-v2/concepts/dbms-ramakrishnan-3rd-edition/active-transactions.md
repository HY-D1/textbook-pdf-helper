# Active transactions

## Definition

Empirically, thrashing is seen to occur when 30% of active transactions are blocked, and a DBA should monitor the fraction of blocked transactions to see if the system is at risk of thrashing.

## Explanation

Figure 16.9 Lock Thrashing If a database system begins to thrash, the database administrator should reduce the number of transactions allowed to run concurrently. Empirically, thrashing is seen to occur when 30% of active transactions are blocked, and a DBA should monitor the fraction of blocked transactions to see if the system is at risk of thrashing. Throughput can be increa..c;ed in three ways (other than buying a fa..'3ter system): IIll By locking the smallest sized objects possible (reducing the likelihood that two transactions need the same lock).

.. By reducing the time that transaction hold locks (so that other transactions are blocked for a shorter time). 3Ivlany common deadlocks can be avoided using a technique called lock downgrade8, implemented in most cOlnmercial systems (Section 17.3).

## Examples

### Example

```sql
-- See textbook for examples
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

**Question:** Practice using Active transactions in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
