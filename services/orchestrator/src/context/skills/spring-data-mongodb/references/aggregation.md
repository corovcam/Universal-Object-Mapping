# Aggregation framework — Spring Data MongoDB 5.0

Use the aggregation framework when a query needs grouping, multi-stage transformation,
joins (`$lookup`), or computed fields — anything a single `Query`/`Criteria` find cannot
express. The builder lives in `org.springframework.data.mongodb.core.aggregation`.

## Table of contents

1. Pipeline basics: `newAggregation` vs `TypedAggregation`
2. The stage operators
3. Executing and reading results
4. `previousOperation()` and stage references
5. Output types (records, interfaces) and counting a pipeline
6. Worked examples

---

## 1. Pipeline basics

Static-import the factory so stages read like the Mongo pipeline (this matches the
official docs):

```java
import static org.springframework.data.mongodb.core.aggregation.Aggregation.*;
import static org.springframework.data.domain.Sort.Direction.DESC;

import org.springframework.data.mongodb.core.aggregation.Aggregation;
import org.springframework.data.mongodb.core.aggregation.AggregationResults;
import org.springframework.data.mongodb.core.aggregation.TypedAggregation;
```

`newAggregation(...)` builds an untyped pipeline; `newAggregation(Entity.class, ...)`
builds a `TypedAggregation<Entity>` that knows the input collection and maps field names
through the entity. Prefer the typed form when you have the entity class.

```java
TypedAggregation<OrderLine> agg = Aggregation.newAggregation(
        OrderLine.class,
        group("taxRate").count().as("count"),
        project("count").and("taxRate").previousOperation(),
        sort(DESC, "count"));
```

## 2. The stage operators

All produced by static methods on `Aggregation`:

| Stage | Mongo | Notes |
|---|---|---|
| `match(Criteria)` | `$match` | filter; reuse the same `Criteria.where(...)` API |
| `group("f")` / `group("a","b")` | `$group` | then `.count().as(..)`, `.sum("x").as(..)`, `.avg`, `.min`, `.max`, `.first`, `.last`, `.addToSet`, `.push` |
| `project("f"...)` | `$project` | include fields; `.and("x").as("y")`, `.andExpression(...)`, `.nested(bind(...))` |
| `sort(Direction, "f"...)` | `$sort` | or `sort(Sort)` |
| `unwind("arrayField")` | `$unwind` | flatten an array |
| `limit(n)` / `skip(n)` | `$limit` / `$skip` | |
| `count().as("name")` | `$count` | terminal count stage |
| `lookup("from","localF","foreignF","as")` | `$lookup` | join another collection |
| `addFields()` / `set(...)` | `$addFields`/`$set` | computed fields |
| `replaceRoot(...)` | `$replaceRoot` | promote a sub-document |

## 3. Executing and reading results

```java
AggregationResults<TagCount> results =
        mongoTemplate.aggregate(agg, OrderLine.class, TagCount.class);

List<TagCount> mapped = results.getMappedResults();   // all rows
TagCount unique       = results.getUniqueMappedResult(); // exactly one row, else null
```

`mongoTemplate.aggregate(...)` overloads:

- `aggregate(TypedAggregation<I>, Class<O> out)` — input collection from the typed agg.
- `aggregate(Aggregation, Class<I> in, Class<O> out)` — input collection from `in`.
- `aggregate(Aggregation, String collectionName, Class<O> out)` — explicit collection.

## 4. `previousOperation()` and stage references

Inside a `project` (or `sort`), `previousOperation()` refers to the `_id` produced by the
preceding `group`. This is how you rename the group key:

```java
group("taxRate").count().as("count"),     // _id = taxRate, count = n
project("count").and("taxRate").previousOperation()  // expose group _id as "taxRate"
```

`sort(DESC, previousOperation(), "totalPop")` sorts by the previous group key plus a field.

## 5. Output types and counting a pipeline

A record or a plain class both work as the output type; field names must match the
projected names.

```java
record TagCount(String taxRate, Long count) {}
record CountProjection(Long count) {}
```

To count how many rows a pipeline yields, append a `$count` stage to a copy of the
pipeline and read the unique result (pattern used in the project harness):

```java
var baseOps = new java.util.ArrayList<>(agg.getPipeline().getOperations());
baseOps.add(Aggregation.count().as("count"));
var countAgg = Aggregation.newAggregation(OrderLine.class, baseOps);
CountProjection cp = mongoTemplate.aggregate(countAgg, OrderLine.class, CountProjection.class)
        .getUniqueMappedResult();
long total = cp != null ? cp.count() : 0L;
```

Inspect the compiled pipeline for debugging with `agg.toString()`.

## 6. Worked examples

Count documents per `taxRate`, highest first:

```java
import static org.springframework.data.mongodb.core.aggregation.Aggregation.*;
import static org.springframework.data.domain.Sort.Direction.DESC;

TypedAggregation<OrderLine> agg = newAggregation(
        OrderLine.class,
        group("taxRate").count().as("count"),
        project("count").and("taxRate").previousOperation(),
        sort(DESC, "count"));

record TaxRateCount(java.math.BigDecimal taxRate, Long count) {}

List<TaxRateCount> rows =
        mongoTemplate.aggregate(agg, OrderLine.class, TaxRateCount.class).getMappedResults();
```

Filter then group (sum quantity per order, only completed lines):

```java
TypedAggregation<OrderLine> agg = newAggregation(
        OrderLine.class,
        match(org.springframework.data.mongodb.core.query.Criteria
                .where("pickedQuantity").gt(0)),
        group("orderId").sum("quantity").as("totalQty"),
        sort(DESC, "totalQty"));

record OrderQty(Integer orderId, Long totalQty) {}
List<OrderQty> rows =
        mongoTemplate.aggregate(agg, OrderLine.class, OrderQty.class).getMappedResults();
```

Join with `$lookup` (order lines for each order):

```java
TypedAggregation<Order> agg = newAggregation(
        Order.class,
        match(org.springframework.data.mongodb.core.query.Criteria.where("customerId").is(1)),
        lookup("orderLines", "orderId", "orderId", "lines"));
```

When the source query was a simple filter/sort/projection, do **not** reach for
aggregation — translate it to a `Query`/`Criteria` find (see `queries.md`). Use
aggregation only for grouping/joining/computed transformations.
