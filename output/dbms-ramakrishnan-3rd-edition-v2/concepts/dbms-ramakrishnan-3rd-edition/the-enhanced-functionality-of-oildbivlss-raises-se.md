# 
The enhanced functionality of OIlDBIvlSs raises several irnp1ernentation chal-

## Definition

SOlne of these are 'well understood and solutions have been irnp1enlented in products; others are subjects of current research.

## Explanation

lenges. SOlne of these are 'well understood and solutions have been irnp1enlented in products; others are subjects of current research. In this section \ve exarnine a few of the key challenges that arise in irnplernenting an efficient, fully func- tional OIlDBlvfS. l\:lany rnore issues are involved than those discussed here; the I.- , interested reader is encouraged to revisit the previous chapters in this book and consider whether the irnplernentation techniques described there apply natu- rally to ORDBJ\JISs or not.

23.8.1 Storage and Access Methods Since object-relational databases store new types of data, ORDBMS imple- rnentors need to revisit some of the storage and indexing issues discussed in earlier chapters. In particular, the system lllust efficiently store ADT objects and structured objects and provide efficient indexed access to both. Storing Large ADT and Structured Type Objects Large ADT objects and structured objects cornplicate the layout of data on disk.

This problern is well understood and has been solved in essentially all ORDBMSs and OODBMSs. We present Sallie of the main issues here. User-defined ADTs can be quite la,rge. In particular, they can be bigger than a single disk page. Large ADTs, like BLOBs, require special storage, typically in a different location on disk frorn the tuples that contain them. Disk-based pointers are rnaintained frorn the tuples to the objects they contain.

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

**Question:** Practice using 
The enhanced functionality of OIlDBIvlSs raises several irnp1ernentation chal- in your own SQL queries

**Solution:** Try writing queries and compare with textbook examples
