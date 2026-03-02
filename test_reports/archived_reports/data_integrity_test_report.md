# Data Integrity and Validation Test Report

Generated: 2026-03-01 09:56:44

## Executive Summary

- **Total Test Runs**: 13
- **Total Tests**: 160
- **Passed**: 141 (88.1%)
- **Failed**: 19
- **Warnings**: 203

## Detailed Results by Directory

### murach-test

- **Tests**: 12
- **Passed**: 11
- **Failed**: 1
- **Warnings**: 71

#### JSON Schema Validation

- ✓ `concept-manifest.json`
- ✓ `murachs-mysql-3rd-edition-extraction.json`
- ✓ `murachs-mysql-3rd-edition-educational-notes.json`
- ✓ `murachs-mysql-3rd-edition-sqladapt.json`
- ✓ `concept-map.json`

#### Cross-Reference Validation: ✗

- **ERROR**: Concepts in manifest but not in map: {'select-statement-murach', 'having-murach', 'backup-restore', 'constraints', 'isolation-levels', 'inner-join-murach', 'data-types', 'string-functions', 'views-murach', 'stored-procedures', 'events', 'joins-murach', 'isolation-levels-murach', 'data-independence', 'cardinality', 'er-model', 'er-diagrams', 'delete', 'sql-intro', 'insert-murach', 'foreign-key', 'authorization', 'inner-join', 'mysql-intro', 'relational-databases-murach', 'selection-projection', 'delete-murach', 'relational-model-intro', 'date-functions', 'aggregate-functions', 'transactions-murach', 'select-basic', 'joins', 'set-operations', 'correlated-subquery', 'having', 'order-by-murach', 'relational-algebra', 'subqueries', 'data-types-murach', '3nf', 'acid', 'views', 'where-clause-murach', 'group-by-murach', '1nf', 'subqueries-murach', 'unions', 'create-table', 'alter-table-murach', 'primary-key', 'triggers', 'update', 'user-management', 'where-clause', 'constraints-murach', 'outer-join-murach', 'transactions', 'mysql-functions', 'indexes', 'aggregate-functions-murach', 'insert', 'outer-join', '2nf', 'group-by', 'create-table-murach', 'update-murach', 'normalization', 'functions-murach', 'correlated-subquery-murach'}
- **WARNING**: Concepts in map but not in manifest: {'murachs-mysql-3rd-edition/mysql-functions', 'murachs-mysql-3rd-edition/3nf', 'murachs-mysql-3rd-edition/stored-procedures', 'murachs-mysql-3rd-edition/data-types-murach', 'murachs-mysql-3rd-edition/correlated-subquery', 'murachs-mysql-3rd-edition/where-clause', 'murachs-mysql-3rd-edition/date-functions', 'murachs-mysql-3rd-edition/create-table-murach', 'murachs-mysql-3rd-edition/inner-join', 'murachs-mysql-3rd-edition/aggregate-functions-murach', 'murachs-mysql-3rd-edition/group-by', 'murachs-mysql-3rd-edition/insert-murach', 'murachs-mysql-3rd-edition/correlated-subquery-murach', 'murachs-mysql-3rd-edition/er-diagrams', 'murachs-mysql-3rd-edition/select-basic', 'murachs-mysql-3rd-edition/where-clause-murach', 'murachs-mysql-3rd-edition/set-operations', 'murachs-mysql-3rd-edition/relational-databases-murach', 'murachs-mysql-3rd-edition/having', 'murachs-mysql-3rd-edition/outer-join', 'murachs-mysql-3rd-edition/er-model', 'murachs-mysql-3rd-edition/data-independence', 'murachs-mysql-3rd-edition/joins', 'murachs-mysql-3rd-edition/aggregate-functions', 'murachs-mysql-3rd-edition/1nf', 'murachs-mysql-3rd-edition/string-functions', 'murachs-mysql-3rd-edition/views-murach', 'murachs-mysql-3rd-edition/foreign-key', 'murachs-mysql-3rd-edition/primary-key', 'murachs-mysql-3rd-edition/indexes', 'murachs-mysql-3rd-edition/select-statement-murach', 'murachs-mysql-3rd-edition/alter-table-murach', 'murachs-mysql-3rd-edition/group-by-murach', 'murachs-mysql-3rd-edition/functions-murach', 'murachs-mysql-3rd-edition/unions', 'murachs-mysql-3rd-edition/relational-model-intro', 'murachs-mysql-3rd-edition/views', 'murachs-mysql-3rd-edition/update-murach', 'murachs-mysql-3rd-edition/cardinality', 'murachs-mysql-3rd-edition/backup-restore', 'murachs-mysql-3rd-edition/triggers', 'murachs-mysql-3rd-edition/user-management', 'murachs-mysql-3rd-edition/delete-murach', 'murachs-mysql-3rd-edition/sql-intro', 'murachs-mysql-3rd-edition/update', 'murachs-mysql-3rd-edition/acid', 'murachs-mysql-3rd-edition/constraints-murach', 'murachs-mysql-3rd-edition/insert', 'murachs-mysql-3rd-edition/order-by-murach', 'murachs-mysql-3rd-edition/data-types', 'murachs-mysql-3rd-edition/subqueries-murach', 'murachs-mysql-3rd-edition/selection-projection', 'murachs-mysql-3rd-edition/relational-algebra', 'murachs-mysql-3rd-edition/outer-join-murach', 'murachs-mysql-3rd-edition/inner-join-murach', 'murachs-mysql-3rd-edition/events', 'murachs-mysql-3rd-edition/normalization', 'murachs-mysql-3rd-edition/isolation-levels', 'murachs-mysql-3rd-edition/subqueries', 'murachs-mysql-3rd-edition/transactions', 'murachs-mysql-3rd-edition/2nf', 'murachs-mysql-3rd-edition/delete', 'murachs-mysql-3rd-edition/mysql-intro', 'murachs-mysql-3rd-edition/authorization', 'murachs-mysql-3rd-edition/constraints', 'murachs-mysql-3rd-edition/joins-murach', 'murachs-mysql-3rd-edition/isolation-levels-murach', 'murachs-mysql-3rd-edition/create-table', 'murachs-mysql-3rd-edition/having-murach', 'murachs-mysql-3rd-edition/transactions-murach'}

#### Content Validation: ✓


#### Asset Validation: ✓

- **WARNING**: Markdown file README.md references non-existent link: aggregate-functions.md
- **WARNING**: Markdown file README.md references non-existent link: aggregate-functions-murach.md
- **WARNING**: Markdown file README.md references non-existent link: create-table.md
- **WARNING**: Markdown file README.md references non-existent link: create-table-murach.md
- **WARNING**: Markdown file README.md references non-existent link: delete.md
- **WARNING**: Markdown file README.md references non-existent link: delete-murach.md
- **WARNING**: Markdown file README.md references non-existent link: data-independence.md
- **WARNING**: Markdown file README.md references non-existent link: 1nf.md
- **WARNING**: Markdown file README.md references non-existent link: inner-join.md
- **WARNING**: Markdown file README.md references non-existent link: insert.md
- **WARNING**: Markdown file README.md references non-existent link: insert-murach.md
- **WARNING**: Markdown file README.md references non-existent link: inner-join-murach.md
- **WARNING**: Markdown file README.md references non-existent link: mysql-intro.md
- **WARNING**: Markdown file README.md references non-existent link: relational-model-intro.md
- **WARNING**: Markdown file README.md references non-existent link: sql-intro.md
- **WARNING**: Markdown file README.md references non-existent link: data-types-murach.md
- **WARNING**: Markdown file README.md references non-existent link: order-by-murach.md
- **WARNING**: Markdown file README.md references non-existent link: primary-key.md
- **WARNING**: Markdown file README.md references non-existent link: relational-databases-murach.md
- **WARNING**: Markdown file README.md references non-existent link: select-statement-murach.md
- **WARNING**: Markdown file README.md references non-existent link: select-basic.md
- **WARNING**: Markdown file README.md references non-existent link: data-types.md
- **WARNING**: Markdown file README.md references non-existent link: selection-projection.md
- **WARNING**: Markdown file README.md references non-existent link: string-functions.md
- **WARNING**: Markdown file README.md references non-existent link: update.md
- **WARNING**: Markdown file README.md references non-existent link: update-murach.md
- **WARNING**: Markdown file README.md references non-existent link: where-clause-murach.md
- **WARNING**: Markdown file README.md references non-existent link: where-clause.md
- **WARNING**: Markdown file README.md references non-existent link: acid.md
- **WARNING**: Markdown file README.md references non-existent link: alter-table-murach.md
- **WARNING**: Markdown file README.md references non-existent link: backup-restore.md
- **WARNING**: Markdown file README.md references non-existent link: cardinality.md
- **WARNING**: Markdown file README.md references non-existent link: constraints-murach.md
- **WARNING**: Markdown file README.md references non-existent link: indexes.md
- **WARNING**: Markdown file README.md references non-existent link: normalization.md
- **WARNING**: Markdown file README.md references non-existent link: transactions.md
- **WARNING**: Markdown file README.md references non-existent link: date-functions.md
- **WARNING**: Markdown file README.md references non-existent link: er-diagrams.md
- **WARNING**: Markdown file README.md references non-existent link: er-model.md
- **WARNING**: Markdown file README.md references non-existent link: foreign-key.md
- **WARNING**: Markdown file README.md references non-existent link: group-by.md
- **WARNING**: Markdown file README.md references non-existent link: group-by-murach.md
- **WARNING**: Markdown file README.md references non-existent link: having.md
- **WARNING**: Markdown file README.md references non-existent link: having-murach.md
- **WARNING**: Markdown file README.md references non-existent link: constraints.md
- **WARNING**: Markdown file README.md references non-existent link: joins-murach.md
- **WARNING**: Markdown file README.md references non-existent link: mysql-functions.md
- **WARNING**: Markdown file README.md references non-existent link: outer-join.md
- **WARNING**: Markdown file README.md references non-existent link: outer-join-murach.md
- **WARNING**: Markdown file README.md references non-existent link: relational-algebra.md
- **WARNING**: Markdown file README.md references non-existent link: authorization.md
- **WARNING**: Markdown file README.md references non-existent link: joins.md
- **WARNING**: Markdown file README.md references non-existent link: views.md
- **WARNING**: Markdown file README.md references non-existent link: 2nf.md
- **WARNING**: Markdown file README.md references non-existent link: set-operations.md
- **WARNING**: Markdown file README.md references non-existent link: functions-murach.md
- **WARNING**: Markdown file README.md references non-existent link: stored-procedures.md
- **WARNING**: Markdown file README.md references non-existent link: subqueries.md
- **WARNING**: Markdown file README.md references non-existent link: subqueries-murach.md
- **WARNING**: Markdown file README.md references non-existent link: 3nf.md
- **WARNING**: Markdown file README.md references non-existent link: transactions-murach.md
- **WARNING**: Markdown file README.md references non-existent link: unions.md
- **WARNING**: Markdown file README.md references non-existent link: user-management.md
- **WARNING**: Markdown file README.md references non-existent link: views-murach.md
- **WARNING**: Markdown file README.md references non-existent link: correlated-subquery.md
- **WARNING**: Markdown file README.md references non-existent link: correlated-subquery-murach.md
- **WARNING**: Markdown file README.md references non-existent link: events.md
- **WARNING**: Markdown file README.md references non-existent link: isolation-levels.md
- **WARNING**: Markdown file README.md references non-existent link: isolation-levels-murach.md
- **WARNING**: Markdown file README.md references non-existent link: triggers.md

#### Provenance Validation: ✓


#### Corruption Detection: ✓


#### Round-Trip Testing: ✓


### murach-fixed

- **Tests**: 12
- **Passed**: 10
- **Failed**: 2
- **Warnings**: 6

#### JSON Schema Validation

- ✓ `concept-manifest.json`
- ✓ `murachs-mysql-3rd-edition-extraction.json`
- ✓ `murachs-mysql-3rd-edition-educational-notes.json`
- ✓ `murachs-mysql-3rd-edition-sqladapt.json`
- ✓ `concept-map.json`

#### Cross-Reference Validation: ✗

- **ERROR**: Concepts in manifest but not in map: {'logs-errors-warnings-and-informational-messages', 'deletes-binary-log-files-that-are-more-than-7-days-old', 'sets-the-maximum-binary-log-file-size-to-1mb', 'content', 'stores-the-output-of-the-general-and-slow-query-logs-in-a-table'}
- **ERROR**: Concept content references page 622 but extraction only has 621 pages
- **ERROR**: Concept content references page 623 but extraction only has 621 pages
- **ERROR**: Concept content references page 624 but extraction only has 621 pages
- **ERROR**: Concept content references page 625 but extraction only has 621 pages
- **ERROR**: Concept content references page 626 but extraction only has 621 pages
- **ERROR**: Concept content references page 627 but extraction only has 621 pages
- **ERROR**: Concept content references page 628 but extraction only has 621 pages
- **ERROR**: Concept content references page 629 but extraction only has 621 pages
- **ERROR**: Concept content references page 631 but extraction only has 621 pages
- **ERROR**: Concept content references page 632 but extraction only has 621 pages
- **ERROR**: Concept content references page 633 but extraction only has 621 pages
- **ERROR**: Concept content references page 634 but extraction only has 621 pages
- **ERROR**: Concept content references page 635 but extraction only has 621 pages
- **ERROR**: Concept content references page 636 but extraction only has 621 pages
- **ERROR**: Concept content references page 637 but extraction only has 621 pages
- **ERROR**: Concept content references page 638 but extraction only has 621 pages
- **ERROR**: Concept content references page 639 but extraction only has 621 pages
- **ERROR**: Concept content references page 640 but extraction only has 621 pages
- **ERROR**: Concept content references page 641 but extraction only has 621 pages
- **ERROR**: Concept content references page 642 but extraction only has 621 pages
- **ERROR**: Concept content references page 643 but extraction only has 621 pages
- **ERROR**: Concept content references page 644 but extraction only has 621 pages
- **ERROR**: Concept content references page 646 but extraction only has 621 pages
- **WARNING**: Concepts in map but not in manifest: {'murachs-mysql-3rd-edition/deletes-binary-log-files-that-are-more-than-7-days-old', 'murachs-mysql-3rd-edition/logs-errors-warnings-and-informational-messages', 'murachs-mysql-3rd-edition/content', 'murachs-mysql-3rd-edition/stores-the-output-of-the-general-and-slow-query-logs-in-a-table', 'murachs-mysql-3rd-edition/sets-the-maximum-binary-log-file-size-to-1mb'}

#### Content Validation: ✓


#### Asset Validation: ✓

- **WARNING**: Markdown file README.md references non-existent link: content.md
- **WARNING**: Markdown file README.md references non-existent link: deletes-binary-log-files-that-are-more-than-7-days-old.md
- **WARNING**: Markdown file README.md references non-existent link: logs-errors-warnings-and-informational-messages.md
- **WARNING**: Markdown file README.md references non-existent link: sets-the-maximum-binary-log-file-size-to-1mb.md
- **WARNING**: Markdown file README.md references non-existent link: stores-the-output-of-the-general-and-slow-query-logs-in-a-table.md

#### Provenance Validation: ✗

- **ERROR**: Concept content references page 622 but PDF only has 621 pages
- **ERROR**: Concept content references page 623 but PDF only has 621 pages
- **ERROR**: Concept content references page 624 but PDF only has 621 pages
- **ERROR**: Concept content references page 625 but PDF only has 621 pages
- **ERROR**: Concept content references page 626 but PDF only has 621 pages
- **ERROR**: Concept content references page 627 but PDF only has 621 pages
- **ERROR**: Concept content references page 628 but PDF only has 621 pages
- **ERROR**: Concept content references page 629 but PDF only has 621 pages
- **ERROR**: Concept content references page 631 but PDF only has 621 pages
- **ERROR**: Concept content references page 632 but PDF only has 621 pages
- **ERROR**: Concept content references page 633 but PDF only has 621 pages
- **ERROR**: Concept content references page 634 but PDF only has 621 pages
- **ERROR**: Concept content references page 635 but PDF only has 621 pages
- **ERROR**: Concept content references page 636 but PDF only has 621 pages
- **ERROR**: Concept content references page 637 but PDF only has 621 pages
- **ERROR**: Concept content references page 638 but PDF only has 621 pages
- **ERROR**: Concept content references page 639 but PDF only has 621 pages
- **ERROR**: Concept content references page 640 but PDF only has 621 pages
- **ERROR**: Concept content references page 641 but PDF only has 621 pages
- **ERROR**: Concept content references page 642 but PDF only has 621 pages
- **ERROR**: Concept content references page 643 but PDF only has 621 pages
- **ERROR**: Concept content references page 644 but PDF only has 621 pages
- **ERROR**: Concept content references page 646 but PDF only has 621 pages

#### Corruption Detection: ✓


#### Round-Trip Testing: ✓


### test-explicit

- **Tests**: 12
- **Passed**: 11
- **Failed**: 1
- **Warnings**: 3

#### JSON Schema Validation

- ✓ `concept-manifest.json`
- ✓ `murachs-mysql-3rd-edition-extraction.json`
- ✓ `murachs-mysql-3rd-edition-educational-notes.json`
- ✓ `murachs-mysql-3rd-edition-sqladapt.json`
- ✓ `concept-map.json`

#### Cross-Reference Validation: ✗

- **ERROR**: Concepts in manifest but not in map: {'mysql-intro', 'relational-databases-murach'}
- **WARNING**: Concepts in map but not in manifest: {'murachs-mysql-3rd-edition/mysql-intro', 'murachs-mysql-3rd-edition/relational-databases-murach'}

#### Content Validation: ✓


#### Asset Validation: ✓

- **WARNING**: Markdown file README.md references non-existent link: mysql-intro.md
- **WARNING**: Markdown file README.md references non-existent link: relational-databases-murach.md

#### Provenance Validation: ✓


#### Corruption Detection: ✓


#### Round-Trip Testing: ✓


### final-test

- **Tests**: 12
- **Passed**: 11
- **Failed**: 1
- **Warnings**: 3

#### JSON Schema Validation

- ✓ `concept-manifest.json`
- ✓ `murachs-mysql-3rd-edition-extraction.json`
- ✓ `murachs-mysql-3rd-edition-educational-notes.json`
- ✓ `murachs-mysql-3rd-edition-sqladapt.json`
- ✓ `concept-map.json`

#### Cross-Reference Validation: ✗

- **ERROR**: Concepts in manifest but not in map: {'mysql-intro', 'relational-databases-murach'}
- **WARNING**: Concepts in map but not in manifest: {'murachs-mysql-3rd-edition/mysql-intro', 'murachs-mysql-3rd-edition/relational-databases-murach'}

#### Content Validation: ✓


#### Asset Validation: ✓

- **WARNING**: Markdown file README.md references non-existent link: mysql-intro.md
- **WARNING**: Markdown file README.md references non-existent link: relational-databases-murach.md

#### Provenance Validation: ✓


#### Corruption Detection: ✓


#### Round-Trip Testing: ✓


### test-quality

- **Tests**: 12
- **Passed**: 11
- **Failed**: 1
- **Warnings**: 4

#### JSON Schema Validation

- ✓ `concept-manifest.json`
- ✓ `murachs-mysql-3rd-edition-extraction.json`
- ✓ `murachs-mysql-3rd-edition-educational-notes.json`
- ✓ `murachs-mysql-3rd-edition-sqladapt.json`
- ✓ `concept-map.json`

#### Cross-Reference Validation: ✗

- **ERROR**: Concepts in manifest but not in map: {'select-statement-murach', 'mysql-intro', 'relational-databases-murach'}
- **WARNING**: Concepts in map but not in manifest: {'murachs-mysql-3rd-edition/select-statement-murach', 'murachs-mysql-3rd-edition/mysql-intro', 'murachs-mysql-3rd-edition/relational-databases-murach'}

#### Content Validation: ✓


#### Asset Validation: ✓

- **WARNING**: Markdown file README.md references non-existent link: mysql-intro.md
- **WARNING**: Markdown file README.md references non-existent link: relational-databases-murach.md
- **WARNING**: Markdown file README.md references non-existent link: select-statement-murach.md

#### Provenance Validation: ✓


#### Corruption Detection: ✓


#### Round-Trip Testing: ✓


### both-pdfs

- **Tests**: 16
- **Passed**: 14
- **Failed**: 2
- **Warnings**: 75

#### JSON Schema Validation

- ✓ `dbms-ramakrishnan-3rd-edition-extraction.json`
- ✓ `concept-manifest.json`
- ✓ `dbms-ramakrishnan-3rd-edition-educational-notes.json`
- ✓ `murachs-mysql-3rd-edition-extraction.json`
- ✓ `murachs-mysql-3rd-edition-educational-notes.json`
- ✓ `murachs-mysql-3rd-edition-result.json`
- ✓ `murachs-mysql-3rd-edition-sqladapt.json`
- ✓ `dbms-ramakrishnan-3rd-edition-sqladapt.json`
- ✓ `concept-map.json`

#### Cross-Reference Validation: ✗

- **ERROR**: Concepts in manifest but not in map: {'select-statement-murach', 'having-murach', 'backup-restore', 'inner-join-murach', 'stored-procedures', 'string-functions', 'views-murach', 'events', 'isolation-levels-murach', 'joins-murach', 'insert-murach', 'relational-databases-murach', 'mysql-intro', 'delete-murach', 'date-functions', 'transactions-murach', 'order-by-murach', 'data-types-murach', 'where-clause-murach', 'group-by-murach', 'subqueries-murach', 'unions', 'alter-table-murach', 'triggers', 'user-management', 'constraints-murach', 'outer-join-murach', 'mysql-functions', 'aggregate-functions-murach', 'create-table-murach', 'update-murach', 'functions-murach', 'correlated-subquery-murach'}
- **ERROR**: Inconsistent docIds across files: {'murachs-mysql-3rd-edition', 'dbms-ramakrishnan-3rd-edition'}
- **WARNING**: Concepts in map but not in manifest: {'murachs-mysql-3rd-edition/stores-the-output-of-the-general-and-slow-query-lo', 'dbms-ramakrishnan-3rd-edition/set-operations', 'dbms-ramakrishnan-3rd-edition/order-by', 'murachs-mysql-3rd-edition/create-table-murach', 'murachs-mysql-3rd-edition/select-basics', 'dbms-ramakrishnan-3rd-edition/database-design', 'murachs-mysql-3rd-edition/group-by', 'dbms-ramakrishnan-3rd-edition/part-3', 'dbms-ramakrishnan-3rd-edition/data-types', 'dbms-ramakrishnan-3rd-edition/insert', 'dbms-ramakrishnan-3rd-edition/ofcpus', 'dbms-ramakrishnan-3rd-edition/active-transactions', 'dbms-ramakrishnan-3rd-edition/having', 'dbms-ramakrishnan-3rd-edition/having-clause', 'dbms-ramakrishnan-3rd-edition/1nf', 'murachs-mysql-3rd-edition/unions', 'dbms-ramakrishnan-3rd-edition/insert-statement', 'dbms-ramakrishnan-3rd-edition/content', 'murachs-mysql-3rd-edition/outer-join-murach', 'murachs-mysql-3rd-edition/inner-join-murach', 'murachs-mysql-3rd-edition/database-design', 'dbms-ramakrishnan-3rd-edition/relational-algebra', 'murachs-mysql-3rd-edition/joins-murach', 'murachs-mysql-3rd-edition/isolation-levels-murach', 'murachs-mysql-3rd-edition/constraints-murach', 'murachs-mysql-3rd-edition/where-clause', 'dbms-ramakrishnan-3rd-edition/update', 'murachs-mysql-3rd-edition/aggregate-functions-murach', 'dbms-ramakrishnan-3rd-edition/delete-statement', 'dbms-ramakrishnan-3rd-edition/subqueries', 'dbms-ramakrishnan-3rd-edition/selection-projection', 'dbms-ramakrishnan-3rd-edition/relational-databases', 'murachs-mysql-3rd-edition/insert-statement', 'murachs-mysql-3rd-edition/deletes-binary-log-files-that-are-more-than-7-days-old', 'murachs-mysql-3rd-edition/aggregate-functions', 'dbms-ramakrishnan-3rd-edition/joins', 'murachs-mysql-3rd-edition/functions-murach', 'dbms-ramakrishnan-3rd-edition/the-enhanced-functionality-of-oildbivlss-raises-se', 'dbms-ramakrishnan-3rd-edition/stored-procedures', 'murachs-mysql-3rd-edition/views', 'dbms-ramakrishnan-3rd-edition/sql-intro', 'dbms-ramakrishnan-3rd-edition/3nf', 'murachs-mysql-3rd-edition/sql-intro', 'murachs-mysql-3rd-edition/content', 'murachs-mysql-3rd-edition/order-by-murach', 'dbms-ramakrishnan-3rd-edition/correlated-subquery', 'murachs-mysql-3rd-edition/logical-operators', 'dbms-ramakrishnan-3rd-edition/foreign-key', 'murachs-mysql-3rd-edition/update-statement', 'dbms-ramakrishnan-3rd-edition/group-by', 'dbms-ramakrishnan-3rd-edition/cardinality', 'murachs-mysql-3rd-edition/mysql-intro', 'dbms-ramakrishnan-3rd-edition/views', 'dbms-ramakrishnan-3rd-edition/transactions', 'dbms-ramakrishnan-3rd-edition/of-cpus-database-size', 'murachs-mysql-3rd-edition/data-types-murach', 'dbms-ramakrishnan-3rd-edition/triggers', 'murachs-mysql-3rd-edition/date-functions', 'murachs-mysql-3rd-edition/relational-databases', 'dbms-ramakrishnan-3rd-edition/normalization', 'dbms-ramakrishnan-3rd-edition/select-basic', 'dbms-ramakrishnan-3rd-edition/acid', 'dbms-ramakrishnan-3rd-edition/indexes', 'murachs-mysql-3rd-edition/database-security', 'murachs-mysql-3rd-edition/insert-murach', 'murachs-mysql-3rd-edition/where-clause-murach', 'dbms-ramakrishnan-3rd-edition/the-enhanced-functionality-of-oildbivlss-raises-several-irnp1ernentation-chal', 'murachs-mysql-3rd-edition/string-functions', 'murachs-mysql-3rd-edition/views-murach', 'dbms-ramakrishnan-3rd-edition/mysql-functions', 'murachs-mysql-3rd-edition/group-by-murach', 'dbms-ramakrishnan-3rd-edition/isolation-levels', 'murachs-mysql-3rd-edition/sets-the-maximum-binary-log-file-size-to-1mb', 'dbms-ramakrishnan-3rd-edition/relational-model-intro', 'murachs-mysql-3rd-edition/triggers', 'murachs-mysql-3rd-edition/user-management', 'dbms-ramakrishnan-3rd-edition/aggregate-functions', 'murachs-mysql-3rd-edition/data-types', 'murachs-mysql-3rd-edition/subqueries-murach', 'dbms-ramakrishnan-3rd-edition/mysql-workbench', 'murachs-mysql-3rd-edition/events', 'murachs-mysql-3rd-edition/writes-queries-to-the-slow-query-log-if-they-take-', 'dbms-ramakrishnan-3rd-edition/er-model', 'dbms-ramakrishnan-3rd-edition/select-basics', 'dbms-ramakrishnan-3rd-edition/part-1', 'murachs-mysql-3rd-edition/create-table', 'murachs-mysql-3rd-edition/having-murach', 'dbms-ramakrishnan-3rd-edition/2nf', 'murachs-mysql-3rd-edition/mysql-functions', 'murachs-mysql-3rd-edition/stored-procedures', 'dbms-ramakrishnan-3rd-edition/er-diagrams', 'dbms-ramakrishnan-3rd-edition/constraints', 'murachs-mysql-3rd-edition/inner-join', 'dbms-ramakrishnan-3rd-edition/inner-join', 'dbms-ramakrishnan-3rd-edition/backup-restore', 'murachs-mysql-3rd-edition/delete-statement', 'murachs-mysql-3rd-edition/correlated-subquery-murach', 'dbms-ramakrishnan-3rd-edition/joins-intro', 'murachs-mysql-3rd-edition/relational-databases-murach', 'murachs-mysql-3rd-edition/outer-join', 'murachs-mysql-3rd-edition/logs-errors-warnings-and-informational-messages', 'murachs-mysql-3rd-edition/mysql-workbench', 'dbms-ramakrishnan-3rd-edition/part-2', 'murachs-mysql-3rd-edition/order-by', 'murachs-mysql-3rd-edition/select-statement-murach', 'murachs-mysql-3rd-edition/alter-table-murach', 'murachs-mysql-3rd-edition/writes-queries-to-the-slow-query-log-if-they-take-longer-than-5-seconds', 'murachs-mysql-3rd-edition/backup-restore', 'murachs-mysql-3rd-edition/update-murach', 'murachs-mysql-3rd-edition/delete-murach', 'murachs-mysql-3rd-edition/having-clause', 'dbms-ramakrishnan-3rd-edition/delete', 'dbms-ramakrishnan-3rd-edition/outer-join', 'murachs-mysql-3rd-edition/stores-the-output-of-the-general-and-slow-query-logs-in-a-table', 'dbms-ramakrishnan-3rd-edition/of-cpus-transactions-per-second', 'dbms-ramakrishnan-3rd-edition/where-clause', 'dbms-ramakrishnan-3rd-edition/logical-operators', 'dbms-ramakrishnan-3rd-edition/primary-key', 'dbms-ramakrishnan-3rd-edition/data-independence', 'murachs-mysql-3rd-edition/normalization', 'murachs-mysql-3rd-edition/subqueries', 'murachs-mysql-3rd-edition/transactions', 'dbms-ramakrishnan-3rd-edition/update-statement', 'murachs-mysql-3rd-edition/joins-intro', 'dbms-ramakrishnan-3rd-edition/database-security', 'murachs-mysql-3rd-edition/deletes-binary-log-files-that-are-more-than-7-days', 'murachs-mysql-3rd-edition/correlated-subquery', 'dbms-ramakrishnan-3rd-edition/create-table', 'dbms-ramakrishnan-3rd-edition/authorization', 'murachs-mysql-3rd-edition/transactions-murach'}

#### Content Validation: ✗

- **ERROR**: Page 9 has empty text
- **ERROR**: Page 217 has empty text
- **ERROR**: Page 307 has empty text
- **ERROR**: Page 553 has empty text
- **WARNING**: Page 9 has very short text (0 chars)
- **WARNING**: Page 217 has very short text (0 chars)
- **WARNING**: Page 307 has very short text (0 chars)
- **WARNING**: Page 553 has very short text (0 chars)

#### Asset Validation: ✓

- **WARNING**: Markdown file README.md references non-existent link: aggregate-functions-murach.md
- **WARNING**: Markdown file README.md references non-existent link: create-table-murach.md
- **WARNING**: Markdown file README.md references non-existent link: delete-murach.md
- **WARNING**: Markdown file README.md references non-existent link: insert-murach.md
- **WARNING**: Markdown file README.md references non-existent link: inner-join-murach.md
- **WARNING**: Markdown file README.md references non-existent link: mysql-intro.md
- **WARNING**: Markdown file README.md references non-existent link: data-types-murach.md
- **WARNING**: Markdown file README.md references non-existent link: order-by-murach.md
- **WARNING**: Markdown file README.md references non-existent link: relational-databases-murach.md
- **WARNING**: Markdown file README.md references non-existent link: select-statement-murach.md
- **WARNING**: Markdown file README.md references non-existent link: string-functions.md
- **WARNING**: Markdown file README.md references non-existent link: update-murach.md
- **WARNING**: Markdown file README.md references non-existent link: where-clause-murach.md
- **WARNING**: Markdown file README.md references non-existent link: alter-table-murach.md
- **WARNING**: Markdown file README.md references non-existent link: backup-restore.md
- **WARNING**: Markdown file README.md references non-existent link: constraints-murach.md
- **WARNING**: Markdown file README.md references non-existent link: date-functions.md
- **WARNING**: Markdown file README.md references non-existent link: group-by-murach.md
- **WARNING**: Markdown file README.md references non-existent link: having-murach.md
- **WARNING**: Markdown file README.md references non-existent link: joins-murach.md
- **WARNING**: Markdown file README.md references non-existent link: mysql-functions.md
- **WARNING**: Markdown file README.md references non-existent link: outer-join-murach.md
- **WARNING**: Markdown file README.md references non-existent link: functions-murach.md
- **WARNING**: Markdown file README.md references non-existent link: stored-procedures.md
- **WARNING**: Markdown file README.md references non-existent link: subqueries-murach.md
- **WARNING**: Markdown file README.md references non-existent link: transactions-murach.md
- **WARNING**: Markdown file README.md references non-existent link: unions.md
- **WARNING**: Markdown file README.md references non-existent link: user-management.md
- **WARNING**: Markdown file README.md references non-existent link: views-murach.md
- **WARNING**: Markdown file README.md references non-existent link: correlated-subquery-murach.md
- **WARNING**: Markdown file README.md references non-existent link: events.md
- **WARNING**: Markdown file README.md references non-existent link: isolation-levels-murach.md
- **WARNING**: Markdown file README.md references non-existent link: triggers.md
- **WARNING**: Markdown file README.md references non-existent link: aggregate-functions.md
- **WARNING**: Markdown file README.md references non-existent link: create-table.md
- **WARNING**: Markdown file README.md references non-existent link: delete.md
- **WARNING**: Markdown file README.md references non-existent link: data-independence.md
- **WARNING**: Markdown file README.md references non-existent link: 1nf.md
- **WARNING**: Markdown file README.md references non-existent link: inner-join.md
- **WARNING**: Markdown file README.md references non-existent link: insert.md
- **WARNING**: Markdown file README.md references non-existent link: relational-model-intro.md
- **WARNING**: Markdown file README.md references non-existent link: sql-intro.md
- **WARNING**: Markdown file README.md references non-existent link: primary-key.md
- **WARNING**: Markdown file README.md references non-existent link: select-basic.md
- **WARNING**: Markdown file README.md references non-existent link: data-types.md
- **WARNING**: Markdown file README.md references non-existent link: selection-projection.md
- **WARNING**: Markdown file README.md references non-existent link: update.md
- **WARNING**: Markdown file README.md references non-existent link: where-clause.md
- **WARNING**: Markdown file README.md references non-existent link: acid.md
- **WARNING**: Markdown file README.md references non-existent link: cardinality.md
- **WARNING**: Markdown file README.md references non-existent link: indexes.md
- **WARNING**: Markdown file README.md references non-existent link: normalization.md
- **WARNING**: Markdown file README.md references non-existent link: transactions.md
- **WARNING**: Markdown file README.md references non-existent link: er-diagrams.md
- **WARNING**: Markdown file README.md references non-existent link: er-model.md
- **WARNING**: Markdown file README.md references non-existent link: foreign-key.md
- **WARNING**: Markdown file README.md references non-existent link: group-by.md
- **WARNING**: Markdown file README.md references non-existent link: having.md
- **WARNING**: Markdown file README.md references non-existent link: constraints.md
- **WARNING**: Markdown file README.md references non-existent link: outer-join.md
- **WARNING**: Markdown file README.md references non-existent link: relational-algebra.md
- **WARNING**: Markdown file README.md references non-existent link: authorization.md
- **WARNING**: Markdown file README.md references non-existent link: joins.md
- **WARNING**: Markdown file README.md references non-existent link: views.md
- **WARNING**: Markdown file README.md references non-existent link: 2nf.md
- **WARNING**: Markdown file README.md references non-existent link: set-operations.md
- **WARNING**: Markdown file README.md references non-existent link: subqueries.md
- **WARNING**: Markdown file README.md references non-existent link: 3nf.md
- **WARNING**: Markdown file README.md references non-existent link: correlated-subquery.md
- **WARNING**: Markdown file README.md references non-existent link: isolation-levels.md

#### Provenance Validation: ✓


#### Corruption Detection: ✓


#### Round-Trip Testing: ✓


### test-3-concepts

- **Tests**: 12
- **Passed**: 11
- **Failed**: 1
- **Warnings**: 4

#### JSON Schema Validation

- ✓ `concept-manifest.json`
- ✓ `murachs-mysql-3rd-edition-extraction.json`
- ✓ `murachs-mysql-3rd-edition-educational-notes.json`
- ✓ `murachs-mysql-3rd-edition-sqladapt.json`
- ✓ `concept-map.json`

#### Cross-Reference Validation: ✗

- **ERROR**: Concepts in manifest but not in map: {'relational-model-intro', 'er-model', 'data-independence'}
- **WARNING**: Concepts in map but not in manifest: {'murachs-mysql-3rd-edition/data-independence', 'murachs-mysql-3rd-edition/relational-model-intro', 'murachs-mysql-3rd-edition/er-model'}

#### Content Validation: ✓


#### Asset Validation: ✓

- **WARNING**: Markdown file README.md references non-existent link: data-independence.md
- **WARNING**: Markdown file README.md references non-existent link: relational-model-intro.md
- **WARNING**: Markdown file README.md references non-existent link: er-model.md

#### Provenance Validation: ✓


#### Corruption Detection: ✓


#### Round-Trip Testing: ✓


### dbms-ramakrishnan-3rd-edition-v2

- **Tests**: 12
- **Passed**: 10
- **Failed**: 2
- **Warnings**: 10

#### JSON Schema Validation

- ✓ `dbms-ramakrishnan-3rd-edition-extraction.json`
- ✓ `concept-manifest.json`
- ✓ `dbms-ramakrishnan-3rd-edition-educational-notes.json`
- ✓ `dbms-ramakrishnan-3rd-edition-sqladapt.json`
- ✓ `concept-map.json`

#### Cross-Reference Validation: ✗

- **ERROR**: Concepts in manifest but not in map: {'the-enhanced-functionality-of-oildbivlss-raises-se', 'part-1', 'of-cpus-database-size', 'content', 'part-3', 'of-cpus-transactions-per-second', 'ofcpus', 'part-2', 'active-transactions'}
- **ERROR**: Concept content references page 1090 but extraction only has 1089 pages
- **ERROR**: Concept content references page 1091 but extraction only has 1089 pages
- **ERROR**: Concept content references page 1092 but extraction only has 1089 pages
- **ERROR**: Concept content references page 1093 but extraction only has 1089 pages
- **ERROR**: Concept content references page 1094 but extraction only has 1089 pages
- **ERROR**: Concept content references page 1095 but extraction only has 1089 pages
- **ERROR**: Concept content references page 1096 but extraction only has 1089 pages
- **WARNING**: Concepts in map but not in manifest: {'dbms-ramakrishnan-3rd-edition/of-cpus-database-size', 'dbms-ramakrishnan-3rd-edition/part-1', 'dbms-ramakrishnan-3rd-edition/active-transactions', 'dbms-ramakrishnan-3rd-edition/part-2', 'dbms-ramakrishnan-3rd-edition/part-3', 'dbms-ramakrishnan-3rd-edition/content', 'dbms-ramakrishnan-3rd-edition/the-enhanced-functionality-of-oildbivlss-raises-se', 'dbms-ramakrishnan-3rd-edition/of-cpus-transactions-per-second', 'dbms-ramakrishnan-3rd-edition/ofcpus'}

#### Content Validation: ✓


#### Asset Validation: ✓

- **WARNING**: Markdown file README.md references non-existent link: the-enhanced-functionality-of-oildbivlss-raises-se.md
- **WARNING**: Markdown file README.md references non-existent link: active-transactions.md
- **WARNING**: Markdown file README.md references non-existent link: content.md
- **WARNING**: Markdown file README.md references non-existent link: of-cpus-transactions-per-second.md
- **WARNING**: Markdown file README.md references non-existent link: of-cpus-database-size.md
- **WARNING**: Markdown file README.md references non-existent link: ofcpus.md
- **WARNING**: Markdown file README.md references non-existent link: part-1.md
- **WARNING**: Markdown file README.md references non-existent link: part-2.md
- **WARNING**: Markdown file README.md references non-existent link: part-3.md

#### Provenance Validation: ✗

- **ERROR**: Concept content references page 1090 but PDF only has 1089 pages
- **ERROR**: Concept content references page 1091 but PDF only has 1089 pages
- **ERROR**: Concept content references page 1092 but PDF only has 1089 pages
- **ERROR**: Concept content references page 1093 but PDF only has 1089 pages
- **ERROR**: Concept content references page 1094 but PDF only has 1089 pages
- **ERROR**: Concept content references page 1095 but PDF only has 1089 pages
- **ERROR**: Concept content references page 1096 but PDF only has 1089 pages

#### Corruption Detection: ✓


#### Round-Trip Testing: ✓


### test-now

- **Tests**: 12
- **Passed**: 11
- **Failed**: 1
- **Warnings**: 2

#### JSON Schema Validation

- ✓ `concept-manifest.json`
- ✓ `murachs-mysql-3rd-edition-extraction.json`
- ✓ `murachs-mysql-3rd-edition-educational-notes.json`
- ✓ `murachs-mysql-3rd-edition-sqladapt.json`
- ✓ `concept-map.json`

#### Cross-Reference Validation: ✗

- **ERROR**: Concepts in manifest but not in map: {'mysql-intro'}
- **WARNING**: Concepts in map but not in manifest: {'murachs-mysql-3rd-edition/mysql-intro'}

#### Content Validation: ✓


#### Asset Validation: ✓

- **WARNING**: Markdown file README.md references non-existent link: mysql-intro.md

#### Provenance Validation: ✓


#### Corruption Detection: ✓


#### Round-Trip Testing: ✓


### murachs-mysql-3rd-edition-v2

- **Tests**: 12
- **Passed**: 10
- **Failed**: 2
- **Warnings**: 7

#### JSON Schema Validation

- ✓ `concept-manifest.json`
- ✓ `murachs-mysql-3rd-edition-extraction.json`
- ✓ `murachs-mysql-3rd-edition-educational-notes.json`
- ✓ `murachs-mysql-3rd-edition-sqladapt.json`
- ✓ `concept-map.json`

#### Cross-Reference Validation: ✗

- **ERROR**: Concepts in manifest but not in map: {'logs-errors-warnings-and-informational-messages', 'sets-the-maximum-binary-log-file-size-to-1mb', 'stores-the-output-of-the-general-and-slow-query-lo', 'writes-queries-to-the-slow-query-log-if-they-take-', 'content', 'deletes-binary-log-files-that-are-more-than-7-days'}
- **ERROR**: Concept content references page 622 but extraction only has 621 pages
- **ERROR**: Concept content references page 623 but extraction only has 621 pages
- **ERROR**: Concept content references page 624 but extraction only has 621 pages
- **ERROR**: Concept content references page 625 but extraction only has 621 pages
- **ERROR**: Concept content references page 626 but extraction only has 621 pages
- **ERROR**: Concept content references page 627 but extraction only has 621 pages
- **ERROR**: Concept content references page 628 but extraction only has 621 pages
- **ERROR**: Concept content references page 629 but extraction only has 621 pages
- **ERROR**: Concept content references page 631 but extraction only has 621 pages
- **ERROR**: Concept content references page 632 but extraction only has 621 pages
- **ERROR**: Concept content references page 633 but extraction only has 621 pages
- **ERROR**: Concept content references page 634 but extraction only has 621 pages
- **ERROR**: Concept content references page 635 but extraction only has 621 pages
- **ERROR**: Concept content references page 636 but extraction only has 621 pages
- **ERROR**: Concept content references page 637 but extraction only has 621 pages
- **ERROR**: Concept content references page 638 but extraction only has 621 pages
- **ERROR**: Concept content references page 639 but extraction only has 621 pages
- **ERROR**: Concept content references page 640 but extraction only has 621 pages
- **ERROR**: Concept content references page 641 but extraction only has 621 pages
- **ERROR**: Concept content references page 642 but extraction only has 621 pages
- **ERROR**: Concept content references page 643 but extraction only has 621 pages
- **ERROR**: Concept content references page 644 but extraction only has 621 pages
- **ERROR**: Concept content references page 646 but extraction only has 621 pages
- **WARNING**: Concepts in map but not in manifest: {'murachs-mysql-3rd-edition/stores-the-output-of-the-general-and-slow-query-lo', 'murachs-mysql-3rd-edition/logs-errors-warnings-and-informational-messages', 'murachs-mysql-3rd-edition/content', 'murachs-mysql-3rd-edition/sets-the-maximum-binary-log-file-size-to-1mb', 'murachs-mysql-3rd-edition/deletes-binary-log-files-that-are-more-than-7-days', 'murachs-mysql-3rd-edition/writes-queries-to-the-slow-query-log-if-they-take-'}

#### Content Validation: ✓


#### Asset Validation: ✓

- **WARNING**: Markdown file README.md references non-existent link: content.md
- **WARNING**: Markdown file README.md references non-existent link: deletes-binary-log-files-that-are-more-than-7-days.md
- **WARNING**: Markdown file README.md references non-existent link: logs-errors-warnings-and-informational-messages.md
- **WARNING**: Markdown file README.md references non-existent link: sets-the-maximum-binary-log-file-size-to-1mb.md
- **WARNING**: Markdown file README.md references non-existent link: stores-the-output-of-the-general-and-slow-query-lo.md
- **WARNING**: Markdown file README.md references non-existent link: writes-queries-to-the-slow-query-log-if-they-take-.md

#### Provenance Validation: ✗

- **ERROR**: Concept content references page 622 but PDF only has 621 pages
- **ERROR**: Concept content references page 623 but PDF only has 621 pages
- **ERROR**: Concept content references page 624 but PDF only has 621 pages
- **ERROR**: Concept content references page 625 but PDF only has 621 pages
- **ERROR**: Concept content references page 626 but PDF only has 621 pages
- **ERROR**: Concept content references page 627 but PDF only has 621 pages
- **ERROR**: Concept content references page 628 but PDF only has 621 pages
- **ERROR**: Concept content references page 629 but PDF only has 621 pages
- **ERROR**: Concept content references page 631 but PDF only has 621 pages
- **ERROR**: Concept content references page 632 but PDF only has 621 pages
- **ERROR**: Concept content references page 633 but PDF only has 621 pages
- **ERROR**: Concept content references page 634 but PDF only has 621 pages
- **ERROR**: Concept content references page 635 but PDF only has 621 pages
- **ERROR**: Concept content references page 636 but PDF only has 621 pages
- **ERROR**: Concept content references page 637 but PDF only has 621 pages
- **ERROR**: Concept content references page 638 but PDF only has 621 pages
- **ERROR**: Concept content references page 639 but PDF only has 621 pages
- **ERROR**: Concept content references page 640 but PDF only has 621 pages
- **ERROR**: Concept content references page 641 but PDF only has 621 pages
- **ERROR**: Concept content references page 642 but PDF only has 621 pages
- **ERROR**: Concept content references page 643 but PDF only has 621 pages
- **ERROR**: Concept content references page 644 but PDF only has 621 pages
- **ERROR**: Concept content references page 646 but PDF only has 621 pages

#### Corruption Detection: ✓


#### Round-Trip Testing: ✓


### murach-mysql-ollama

- **Tests**: 12
- **Passed**: 10
- **Failed**: 2
- **Warnings**: 7

#### JSON Schema Validation

- ✓ `concept-manifest.json`
- ✓ `murachs-mysql-3rd-edition-extraction.json`
- ✓ `murachs-mysql-3rd-edition-educational-notes.json`
- ✓ `murachs-mysql-3rd-edition-sqladapt.json`
- ✓ `concept-map.json`

#### Cross-Reference Validation: ✗

- **ERROR**: Concepts in manifest but not in map: {'logs-errors-warnings-and-informational-messages', 'sets-the-maximum-binary-log-file-size-to-1mb', 'stores-the-output-of-the-general-and-slow-query-lo', 'writes-queries-to-the-slow-query-log-if-they-take-', 'content', 'deletes-binary-log-files-that-are-more-than-7-days'}
- **ERROR**: Concept content references page 622 but extraction only has 621 pages
- **ERROR**: Concept content references page 623 but extraction only has 621 pages
- **ERROR**: Concept content references page 624 but extraction only has 621 pages
- **ERROR**: Concept content references page 625 but extraction only has 621 pages
- **ERROR**: Concept content references page 626 but extraction only has 621 pages
- **ERROR**: Concept content references page 627 but extraction only has 621 pages
- **ERROR**: Concept content references page 628 but extraction only has 621 pages
- **ERROR**: Concept content references page 629 but extraction only has 621 pages
- **ERROR**: Concept content references page 631 but extraction only has 621 pages
- **ERROR**: Concept content references page 632 but extraction only has 621 pages
- **ERROR**: Concept content references page 633 but extraction only has 621 pages
- **ERROR**: Concept content references page 634 but extraction only has 621 pages
- **ERROR**: Concept content references page 635 but extraction only has 621 pages
- **ERROR**: Concept content references page 636 but extraction only has 621 pages
- **ERROR**: Concept content references page 637 but extraction only has 621 pages
- **ERROR**: Concept content references page 638 but extraction only has 621 pages
- **ERROR**: Concept content references page 639 but extraction only has 621 pages
- **ERROR**: Concept content references page 640 but extraction only has 621 pages
- **ERROR**: Concept content references page 641 but extraction only has 621 pages
- **ERROR**: Concept content references page 642 but extraction only has 621 pages
- **ERROR**: Concept content references page 643 but extraction only has 621 pages
- **ERROR**: Concept content references page 644 but extraction only has 621 pages
- **ERROR**: Concept content references page 646 but extraction only has 621 pages
- **WARNING**: Concepts in map but not in manifest: {'murachs-mysql-3rd-edition/stores-the-output-of-the-general-and-slow-query-lo', 'murachs-mysql-3rd-edition/logs-errors-warnings-and-informational-messages', 'murachs-mysql-3rd-edition/content', 'murachs-mysql-3rd-edition/sets-the-maximum-binary-log-file-size-to-1mb', 'murachs-mysql-3rd-edition/deletes-binary-log-files-that-are-more-than-7-days', 'murachs-mysql-3rd-edition/writes-queries-to-the-slow-query-log-if-they-take-'}

#### Content Validation: ✓


#### Asset Validation: ✓

- **WARNING**: Markdown file README.md references non-existent link: content.md
- **WARNING**: Markdown file README.md references non-existent link: deletes-binary-log-files-that-are-more-than-7-days.md
- **WARNING**: Markdown file README.md references non-existent link: logs-errors-warnings-and-informational-messages.md
- **WARNING**: Markdown file README.md references non-existent link: sets-the-maximum-binary-log-file-size-to-1mb.md
- **WARNING**: Markdown file README.md references non-existent link: stores-the-output-of-the-general-and-slow-query-lo.md
- **WARNING**: Markdown file README.md references non-existent link: writes-queries-to-the-slow-query-log-if-they-take-.md

#### Provenance Validation: ✗

- **ERROR**: Concept content references page 622 but PDF only has 621 pages
- **ERROR**: Concept content references page 623 but PDF only has 621 pages
- **ERROR**: Concept content references page 624 but PDF only has 621 pages
- **ERROR**: Concept content references page 625 but PDF only has 621 pages
- **ERROR**: Concept content references page 626 but PDF only has 621 pages
- **ERROR**: Concept content references page 627 but PDF only has 621 pages
- **ERROR**: Concept content references page 628 but PDF only has 621 pages
- **ERROR**: Concept content references page 629 but PDF only has 621 pages
- **ERROR**: Concept content references page 631 but PDF only has 621 pages
- **ERROR**: Concept content references page 632 but PDF only has 621 pages
- **ERROR**: Concept content references page 633 but PDF only has 621 pages
- **ERROR**: Concept content references page 634 but PDF only has 621 pages
- **ERROR**: Concept content references page 635 but PDF only has 621 pages
- **ERROR**: Concept content references page 636 but PDF only has 621 pages
- **ERROR**: Concept content references page 637 but PDF only has 621 pages
- **ERROR**: Concept content references page 638 but PDF only has 621 pages
- **ERROR**: Concept content references page 639 but PDF only has 621 pages
- **ERROR**: Concept content references page 640 but PDF only has 621 pages
- **ERROR**: Concept content references page 641 but PDF only has 621 pages
- **ERROR**: Concept content references page 642 but PDF only has 621 pages
- **ERROR**: Concept content references page 643 but PDF only has 621 pages
- **ERROR**: Concept content references page 644 but PDF only has 621 pages
- **ERROR**: Concept content references page 646 but PDF only has 621 pages

#### Corruption Detection: ✓


#### Round-Trip Testing: ✓


### murach-v3

- **Tests**: 12
- **Passed**: 10
- **Failed**: 2
- **Warnings**: 7

#### JSON Schema Validation

- ✓ `concept-manifest.json`
- ✓ `murachs-mysql-3rd-edition-extraction.json`
- ✓ `murachs-mysql-3rd-edition-educational-notes.json`
- ✓ `murachs-mysql-3rd-edition-sqladapt.json`
- ✓ `concept-map.json`

#### Cross-Reference Validation: ✗

- **ERROR**: Concepts in manifest but not in map: {'logs-errors-warnings-and-informational-messages', 'sets-the-maximum-binary-log-file-size-to-1mb', 'stores-the-output-of-the-general-and-slow-query-lo', 'writes-queries-to-the-slow-query-log-if-they-take-', 'content', 'deletes-binary-log-files-that-are-more-than-7-days'}
- **ERROR**: Concept content references page 622 but extraction only has 621 pages
- **ERROR**: Concept content references page 623 but extraction only has 621 pages
- **ERROR**: Concept content references page 624 but extraction only has 621 pages
- **ERROR**: Concept content references page 625 but extraction only has 621 pages
- **ERROR**: Concept content references page 626 but extraction only has 621 pages
- **ERROR**: Concept content references page 627 but extraction only has 621 pages
- **ERROR**: Concept content references page 628 but extraction only has 621 pages
- **ERROR**: Concept content references page 629 but extraction only has 621 pages
- **ERROR**: Concept content references page 631 but extraction only has 621 pages
- **ERROR**: Concept content references page 632 but extraction only has 621 pages
- **ERROR**: Concept content references page 633 but extraction only has 621 pages
- **ERROR**: Concept content references page 634 but extraction only has 621 pages
- **ERROR**: Concept content references page 635 but extraction only has 621 pages
- **ERROR**: Concept content references page 636 but extraction only has 621 pages
- **ERROR**: Concept content references page 637 but extraction only has 621 pages
- **ERROR**: Concept content references page 638 but extraction only has 621 pages
- **ERROR**: Concept content references page 639 but extraction only has 621 pages
- **ERROR**: Concept content references page 640 but extraction only has 621 pages
- **ERROR**: Concept content references page 641 but extraction only has 621 pages
- **ERROR**: Concept content references page 642 but extraction only has 621 pages
- **ERROR**: Concept content references page 643 but extraction only has 621 pages
- **ERROR**: Concept content references page 644 but extraction only has 621 pages
- **ERROR**: Concept content references page 646 but extraction only has 621 pages
- **WARNING**: Concepts in map but not in manifest: {'murachs-mysql-3rd-edition/stores-the-output-of-the-general-and-slow-query-lo', 'murachs-mysql-3rd-edition/logs-errors-warnings-and-informational-messages', 'murachs-mysql-3rd-edition/content', 'murachs-mysql-3rd-edition/sets-the-maximum-binary-log-file-size-to-1mb', 'murachs-mysql-3rd-edition/deletes-binary-log-files-that-are-more-than-7-days', 'murachs-mysql-3rd-edition/writes-queries-to-the-slow-query-log-if-they-take-'}

#### Content Validation: ✓


#### Asset Validation: ✓

- **WARNING**: Markdown file README.md references non-existent link: content.md
- **WARNING**: Markdown file README.md references non-existent link: deletes-binary-log-files-that-are-more-than-7-days.md
- **WARNING**: Markdown file README.md references non-existent link: logs-errors-warnings-and-informational-messages.md
- **WARNING**: Markdown file README.md references non-existent link: sets-the-maximum-binary-log-file-size-to-1mb.md
- **WARNING**: Markdown file README.md references non-existent link: stores-the-output-of-the-general-and-slow-query-lo.md
- **WARNING**: Markdown file README.md references non-existent link: writes-queries-to-the-slow-query-log-if-they-take-.md

#### Provenance Validation: ✗

- **ERROR**: Concept content references page 622 but PDF only has 621 pages
- **ERROR**: Concept content references page 623 but PDF only has 621 pages
- **ERROR**: Concept content references page 624 but PDF only has 621 pages
- **ERROR**: Concept content references page 625 but PDF only has 621 pages
- **ERROR**: Concept content references page 626 but PDF only has 621 pages
- **ERROR**: Concept content references page 627 but PDF only has 621 pages
- **ERROR**: Concept content references page 628 but PDF only has 621 pages
- **ERROR**: Concept content references page 629 but PDF only has 621 pages
- **ERROR**: Concept content references page 631 but PDF only has 621 pages
- **ERROR**: Concept content references page 632 but PDF only has 621 pages
- **ERROR**: Concept content references page 633 but PDF only has 621 pages
- **ERROR**: Concept content references page 634 but PDF only has 621 pages
- **ERROR**: Concept content references page 635 but PDF only has 621 pages
- **ERROR**: Concept content references page 636 but PDF only has 621 pages
- **ERROR**: Concept content references page 637 but PDF only has 621 pages
- **ERROR**: Concept content references page 638 but PDF only has 621 pages
- **ERROR**: Concept content references page 639 but PDF only has 621 pages
- **ERROR**: Concept content references page 640 but PDF only has 621 pages
- **ERROR**: Concept content references page 641 but PDF only has 621 pages
- **ERROR**: Concept content references page 642 but PDF only has 621 pages
- **ERROR**: Concept content references page 643 but PDF only has 621 pages
- **ERROR**: Concept content references page 644 but PDF only has 621 pages
- **ERROR**: Concept content references page 646 but PDF only has 621 pages

#### Corruption Detection: ✓


#### Round-Trip Testing: ✓


### quality-test

- **Tests**: 12
- **Passed**: 11
- **Failed**: 1
- **Warnings**: 4

#### JSON Schema Validation

- ✓ `concept-manifest.json`
- ✓ `murachs-mysql-3rd-edition-extraction.json`
- ✓ `murachs-mysql-3rd-edition-educational-notes.json`
- ✓ `murachs-mysql-3rd-edition-sqladapt.json`
- ✓ `concept-map.json`

#### Cross-Reference Validation: ✗

- **ERROR**: Concepts in manifest but not in map: {'select-statement-murach', 'mysql-intro', 'relational-databases-murach'}
- **WARNING**: Concepts in map but not in manifest: {'murachs-mysql-3rd-edition/select-statement-murach', 'murachs-mysql-3rd-edition/mysql-intro', 'murachs-mysql-3rd-edition/relational-databases-murach'}

#### Content Validation: ✓


#### Asset Validation: ✓

- **WARNING**: Markdown file README.md references non-existent link: mysql-intro.md
- **WARNING**: Markdown file README.md references non-existent link: relational-databases-murach.md
- **WARNING**: Markdown file README.md references non-existent link: select-statement-murach.md

#### Provenance Validation: ✓


#### Corruption Detection: ✓


#### Round-Trip Testing: ✓


## Integrity Guarantees

Based on the validation tests performed, the following integrity guarantees are in place:

### JSON Schema Validation

- All JSON files are well-formed and parseable
- Required fields are present in all output files
- Schema versions are consistent

### Cross-Reference Validation

- Concept IDs are consistent between concept-manifest.json and concept-map.json
- Page references are within valid bounds
- Document IDs are consistent across files

### Content Validation

- Text content is not empty
- No null bytes in text content
- Valid UTF-8 encoding
- Markdown files have proper frontmatter

### Provenance Validation

- All chunk references follow the correct format: `{docId}:p{page}:c{index}`
- Page numbers are positive integers
- Timestamps are valid ISO 8601 format

### Corruption Detection

- JSON files are complete (no truncation)
- No corrupted chunk data
- Type consistency across fields

### Round-Trip Preservation

- Data can be serialized and deserialized without loss
- Key fields are preserved through round-trip

## Recommendations

1. **Fix Critical Errors**: Address all ERROR-level issues before deployment
2. **Review Warnings**: Evaluate WARNING-level issues for potential problems
3. **Regular Testing**: Run these integrity tests after each PDF processing run
4. **Schema Evolution**: Update schema validation when output format changes

