# of CPUs, # transactions per second

## Definition

A relational query execution plan is a graph of relational algebra operators, and the operators in a graph can be executed in parallel.

## Explanation

Figure 22.2 Speed-up and Scale-up execution of rnultiple queries, it is hard to identify in advance which queries will run concurrently. So the ernphasis has been on parallel execution of a single query. A relational query execution plan is a graph of relational algebra operators, and the operators in a graph can be executed in parallel. If one operator consurnes the output of a second operator, we have pipelined parallelism (the output of the second operator is worked on by the first operator as soon as it is generated); if not, the two operators can proceed esseptially independently.

An operator is said to block if it produces no output until 'it has conSUllled all its inputs. Pipelined parallelisrn is lirnited by the presence of operators (e.g., sorting or aggregation) that block. In addition to evaluating different operators in parallel, we can evaluate each individual operator in a query plan in a parallel fashion. rrhe key to evaluating an operator in pa,rallel is to partition the input data; \ve can then work on each partition in parallel and cornbine the results.

This approach is called data-partitioned parallel evaluation. By exercising sorne care, existing code for sequentially evaluating relational operators can be ported easily for data-partitioned parallel evaluation. All inlportant observation, '\vhich explains vvhy shaxed-nothing parallel databa",;c systelns have been very successful, is that database query evaluation is very axncll<tble to data-partitioned parallel evaluation.

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

**Question:** Practice using of CPUs, # transactions per second in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
