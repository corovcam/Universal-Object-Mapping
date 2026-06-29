# Queries — Cypher-DSL `Statement`s + `Neo4jTemplate` / `Neo4jClient` (SDN 8.0)

This project queries by **building an `org.neo4j.cypherdsl.core.Statement`** with the
fluent `Cypher` builder and executing it on `Neo4jTemplate` (mapped to entities) or
`Neo4jClient` (mapped to generic `Map` rows). It does **not** concatenate Cypher strings
and does **not** use derived-query repository interfaces. Keep query method shape close to
the source: one source query method → one target method returning the same logical result.

## Table of contents

1. The building blocks (`node`, `named`, `property`, parameters, literals)
2. MATCH → WHERE → RETURN, and the `var`/cast you will hit
3. Conditions (the operators you actually need)
4. Ordering, limit, skip
5. Counting
6. Executing on `Neo4jTemplate` (mapped to entities)
7. Executing on `Neo4jClient` (mapped to `Map` rows / projections)
8. Reading back the generated Cypher and parameters
9. Dates, doubles, and literals in queries
10. Worked examples (mirroring the project harness)

---

## 1. The building blocks

```java
import org.neo4j.cypherdsl.core.Cypher;

var ol = Cypher.node("OrderLine").named("ol"); // (ol:OrderLine)
ol.property("quantity");                        // ol.quantity  (a property expression)
Cypher.parameter("from", fromValue);            // $from, value bound into the statement catalog
Cypher.literalOf(1);                            // inline literal 1
Cypher.name("taxRate");                         // a bare symbolic name (refer to a WITH/RETURN alias)
Cypher.property("ol", "orderLineId");           // ol.orderLineId by names (when you don't hold the Node var)
```

Prefer **parameters** (`Cypher.parameter`) over inline literals for values that vary, so
the generated Cypher is reusable and the values travel in the statement catalog. Use
`Cypher.literalOf` when the value is a fixed part of the query.

## 2. MATCH → WHERE → RETURN

```java
import org.neo4j.cypherdsl.core.Cypher;
import org.neo4j.cypherdsl.core.Statement;

var ol = Cypher.node("OrderLine").named("ol");
Statement stmt = Cypher.match(ol)
        .where(ol.property("quantity").gt(Cypher.literalOf(0)))
        .returning(ol)
        .build();
```

`Cypher.match(...)` returns an ongoing builder; `.where(...).and(...)` refine it;
`.returning(...)` produces something buildable; `.build()` yields the `Statement`.

A pattern you will hit when you want to **branch a partially-built query** (e.g. add
`orderBy`/`limit` only sometimes, or build both a count and a row variant): keep the
`.returning(...)` result and cast it to `StatementBuilder.OngoingReadingAndReturn` to keep
chaining terminal operations:

```java
import org.neo4j.cypherdsl.core.SortItem.Direction;
import org.neo4j.cypherdsl.core.StatementBuilder.BuildableStatement;
import org.neo4j.cypherdsl.core.StatementBuilder.OngoingReadingAndReturn;
import org.neo4j.cypherdsl.core.ResultStatement;

BuildableStatement<ResultStatement> q = Cypher.match(ol).returning(ol);
var sorted = ((OngoingReadingAndReturn) q)
        .orderBy(Cypher.sort(ol.property("orderLineId"), Direction.ASC))
        .limit(1)
        .build();
```

This cast is exactly what the project's `Neo4jQueryEntrypoint` snippet does to derive
first/last samples from one base query. `BuildableStatement<ResultStatement>` is the
return type to expose from a reusable `query(...)` method.

## 3. Conditions (the operators you actually need)

Build conditions from property expressions; combine with `.and(...)` / `.or(...)`.

| Method on a property expression | Cypher | Meaning |
|---|---|---|
| `.isEqualTo(expr)` | `=` | equals |
| `.isNotEqualTo(expr)` | `<>` | not equals |
| `.gt(expr)` / `.gte(expr)` | `>` / `>=` | greater (or equal) |
| `.lt(expr)` / `.lte(expr)` | `<` / `<=` | less (or equal) |
| `.in(expr)` | `IN` | membership in a list |
| `.isNull()` / `.isNotNull()` | `IS NULL` / `IS NOT NULL` | null checks |
| `.matches("re")` | `=~` | regex |
| `.startsWith(expr)` / `.endsWith(expr)` / `.contains(expr)` | string ops | substring matching |

Combine: `condA.and(condB)`, `condA.or(condB)`, `cond.not()`. On the builder,
`.where(cond).and(otherCond)` is equivalent to anding into the WHERE.

```java
var stmt = Cypher.match(ol)
        .where(ol.property("pickingCompletedWhen").gte(Cypher.parameter("from", from)))
        .and(ol.property("pickingCompletedWhen").lte(Cypher.parameter("to", to)))
        .returning(ol)
        .build();
```

## 4. Ordering, limit, skip

Ordering uses `Cypher.sort(expression, Direction)` with `SortItem.Direction` (NOT Spring's
`Sort.Direction`):

```java
import org.neo4j.cypherdsl.core.SortItem.Direction;

var stmt = Cypher.match(ol)
        .returning(ol)
        .orderBy(Cypher.sort(ol.property("quantity"), Direction.DESC))
        .limit(50)
        .build();
```

`.skip(n)` and `.limit(n)` are available after `.orderBy(...)` (or directly after
`.returning(...)`). For a deterministic "last" row, order DESC and `.limit(1)` rather than
skipping to the end.

## 5. Counting

Count the whole match with `Cypher.count(...)`:

```java
// count of matched nodes
var countStmt = Cypher.match(ol).returning(Cypher.count(ol)).build();
long n = template.count(countStmt);

// count(*) when there is no single node to count (e.g. after a WITH/group)
var countAll = withClause.returning(Cypher.count(Cypher.asterisk())).build();
```

`template.count(Statement)` returns a `long`. (Note: `Cypher.count` replaced the old
`Functions.count` — see `imports.md` §10.)

## 6. Executing on `Neo4jTemplate` (mapped to entities)

`Neo4jTemplate` maps result nodes back to your `@Node` classes.

```java
import java.util.List;
import java.util.Optional;
import org.springframework.data.neo4j.core.Neo4jTemplate;

List<OrderLine> all = template.findAll(statement, OrderLine.class);
Optional<OrderLine> one = template.findOne(statement, statement.getCatalog().getParameters(), OrderLine.class);
List<OrderLine> everyNode = template.findAll(OrderLine.class);     // whole label, no statement
long count = template.count(countStatement);
```

Key points:

- `findOne(Statement, Map<String,Object> parameters, Class)` takes the parameter map
  **explicitly** — get it from `statement.getCatalog().getParameters()` so the `$from`/
  `$to` parameters you bound actually reach the driver. It returns `Optional`; call
  `.orElse(null)` for a nullable sample.
- `findAll(Statement, Class)` does not take a separate parameter map — the catalog travels
  with the statement.
- The statement must `RETURN` the node (e.g. `.returning(ol)`) for entity mapping to work.
  If you only return scalar properties, map with `Neo4jClient` instead (§7).

## 7. Executing on `Neo4jClient` (mapped to `Map` rows / projections)

When the query returns scalars or aggregates (not whole nodes), use `Neo4jClient`, which
yields generic `Map<String,Object>` rows you adapt yourself:

```java
import java.util.Map;
import org.springframework.data.neo4j.core.Neo4jClient;

var stmt = Cypher.match(ol)
        .returning(
            ol.property("orderLineId").as("orderLineId"),
            ol.property("quantity").as("quantity"))
        .orderBy(Cypher.sort(ol.property("orderLineId"), Direction.ASC))
        .limit(1)
        .build();

Map<String, Object> row = client.query(stmt.getCypher())
        .bindAll(stmt.getCatalog().getParameters())
        .fetch()
        .one()
        .orElse(null);

// Neo4j returns integers as Long and floats as Double — narrow defensively:
Number id = (Number) row.get("orderLineId");
Integer orderLineId = id != null ? id.intValue() : null;
```

`client.query(String)` takes the Cypher text from `stmt.getCypher()`; bind the catalog
parameters with `.bindAll(stmt.getCatalog().getParameters())`. `.fetch().one()` /
`.fetch().all()` return `Optional<Map>` / `Collection<Map>`.

Because Neo4j widens numbers (every integer comes back as `Long`, every float as
`Double`), cast row values to `Number` and narrow (`intValue()`, `doubleValue()`) rather
than casting straight to `Integer`/`Double` — a direct `(Integer) row.get(...)` throws a
`ClassCastException`.

A common pattern is to build a `record` projection and populate it from the map:

```java
record OrderLineProjection(Integer orderLineId, Integer quantity) {}
```

## 8. Reading back the generated Cypher and parameters

Useful in harnesses to report exactly what ran:

```java
String cypher = statement.getCypher();                         // the MATCH ... RETURN text
Map<String, Object> params = statement.getCatalog().getParameters(); // bound $-parameters
```

## 9. Dates, doubles, and literals in queries

- Dates: build with `java.time` factories — `LocalDate.of(2014, 12, 20)`,
  `ZonedDateTime.of(2014, 12, 31, 0, 0, 0, 0, ZoneOffset.UTC)`. The entity property type
  must match what you compare against. **Never** `new Date(2014, 12, 20)`.
- Numbers/decimals: compare against `Double`/`Long` — there is no `BigDecimal` in Neo4j.
  Pass them as `Cypher.parameter("x", value)` or `Cypher.literalOf(value)`.
- Wrap variable values in `Cypher.parameter(name, value)`; the value is captured into the
  statement catalog and surfaces via `getCatalog().getParameters()`.

## 10. Worked examples (mirroring the project harness)

Range filter + deterministic first/last samples from one base query:

```java
import org.neo4j.cypherdsl.core.Cypher;
import org.neo4j.cypherdsl.core.ResultStatement;
import org.neo4j.cypherdsl.core.SortItem.Direction;
import org.neo4j.cypherdsl.core.StatementBuilder.BuildableStatement;
import org.neo4j.cypherdsl.core.StatementBuilder.OngoingReadingAndReturn;

static BuildableStatement<ResultStatement> query(boolean returnCount) {
    var from = java.time.ZonedDateTime.of(2014, 12, 20, 0, 0, 0, 0, java.time.ZoneOffset.UTC);
    var to = java.time.ZonedDateTime.of(2014, 12, 31, 0, 0, 0, 0, java.time.ZoneOffset.UTC);
    var ol = Cypher.node("OrderLine").named("ol");
    var partial = Cypher.match(ol)
            .where(ol.property("pickingCompletedWhen").gte(Cypher.parameter("from", from)))
            .and(ol.property("pickingCompletedWhen").lte(Cypher.parameter("to", to)));
    if (returnCount) return partial.returning(Cypher.count(ol));
    return partial.returning(ol);
}

// in the harness:
long count = template.count(query(true).build());
var q = query(false);
var firstStmt = ((OngoingReadingAndReturn) q)
        .orderBy(Cypher.sort(Cypher.property("ol", "orderLineId"), Direction.ASC))
        .limit(1).build();
OrderLine first = template.findOne(firstStmt, firstStmt.getCatalog().getParameters(), OrderLine.class)
        .orElse(null);
```

Top-N by a field (entity-mapped):

```java
var ol = Cypher.node("OrderLine").named("ol");
var stmt = Cypher.match(ol)
        .returning(ol)
        .orderBy(Cypher.sort(ol.property("quantity"), Direction.DESC))
        .limit(50)
        .build();
List<OrderLine> top = template.findAll(stmt, OrderLine.class);
```

Scalar projection (client-mapped, two fields):

```java
var ol = Cypher.node("OrderLine").named("ol");
var stmt = Cypher.match(ol).returning(
        ol.property("orderLineId").as("orderLineId"),
        ol.property("quantity").as("quantity")).build();
var rows = client.query(stmt.getCypher())
        .bindAll(stmt.getCatalog().getParameters())
        .fetch().all();
```

For grouping/counting by a field (e.g. "count per taxRate") and for relationship
traversals, see `references/traversals.md`.
