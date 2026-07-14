# Queries — `MongoTemplate` + Query/Criteria API (Spring Data MongoDB 5.0)

This project queries with explicit `MongoTemplate` calls and the `Query`/`Criteria`
builder, not derived-query repository interfaces. Keep query method shape close to the
source: one source query method → one target method returning the same logical result.

## Table of contents

1. Building a `Query` with `Criteria`
2. Criteria operators (the ones you actually need)
3. Executing reads on `MongoTemplate`
4. Sorting, `limit`, `skip`, paging
5. Field projection (include/exclude) and typed projections
6. Counting and existence
7. The fluent / typed `template.query(...)` API
8. Dates, decimals, and literals in queries
9. Worked examples (mirroring the project harness)

---

## 1. Building a `Query` with `Criteria`

Two equivalent constructions:

```java
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;

// constructor form
Query q1 = new Query(Criteria.where("customerId").is(1));

// static factory form (with static imports of where / query)
Query q2 = query(where("customerId").is(1));
```

Combine criteria:

```java
Query ranged = new Query(
        Criteria.where("pickingCompletedWhen")
                .gte(LocalDate.of(2014, 12, 20))
                .lte(LocalDate.of(2014, 12, 31)));

// AND across different fields: chain .and(...)
Query andQuery = new Query(
        Criteria.where("orderId").is(42).and("quantity").gt(0));

// explicit boolean operators
Query orQuery = new Query(new Criteria().orOperator(
        Criteria.where("taxRate").is(BigDecimal.ZERO),
        Criteria.where("taxRate").gt(new BigDecimal("15"))));
```

`addCriteria` appends to an existing query: `q.addCriteria(Criteria.where("x").is(1));`.

## 2. Criteria operators (the ones you actually need)

| Method | Mongo operator | Meaning |
|---|---|---|
| `.is(v)` | `$eq` | equals |
| `.ne(v)` | `$ne` | not equals |
| `.gt(v)` / `.gte(v)` | `$gt` / `$gte` | greater (or equal) |
| `.lt(v)` / `.lte(v)` | `$lt` / `$lte` | less (or equal) |
| `.in(a, b, ...)` / `.in(coll)` | `$in` | in set |
| `.nin(...)` | `$nin` | not in set |
| `.exists(true)` | `$exists` | field present |
| `.regex("^H")` | `$regex` | regular expression |
| `.ne(null)` / `.exists(true)` | — | "is not null" patterns |
| `.and("field")` | — | continue building on another field |
| `.orOperator(c...)` | `$or` | logical OR |
| `.andOperator(c...)` | `$and` | logical AND |
| `.norOperator(c...)` | `$nor` | logical NOR |
| `.not()` | `$not` | negate the next operator |
| `.size(n)` | `$size` | array length |
| `.elemMatch(c)` | `$elemMatch` | array element matches sub-criteria |

## 3. Executing reads on `MongoTemplate`

```java
import java.util.List;
import org.springframework.data.mongodb.core.MongoTemplate;

List<OrderLine> all      = mongoTemplate.find(query, OrderLine.class);
OrderLine       one      = mongoTemplate.findOne(query, OrderLine.class); // first match or null
OrderLine       byId     = mongoTemplate.findById("652f...", OrderLine.class);
List<OrderLine> everyDoc = mongoTemplate.findAll(OrderLine.class);
long            n        = mongoTemplate.count(query, OrderLine.class);
boolean         any      = mongoTemplate.exists(query, OrderLine.class);
String          coll     = mongoTemplate.getCollectionName(OrderLine.class);
```

The entity `Class` argument both selects the collection and drives mapping. Pass a second
collection-name string overload only when querying a collection that doesn't match the
entity's `@Document`.

## 4. Sorting, `limit`, `skip`, paging

`Query` is mutable and fluent; `with`, `limit`, `skip` return the same instance.

```java
import org.springframework.data.domain.Sort;
import org.springframework.data.domain.PageRequest;

Query sorted = new Query()
        .with(Sort.by(Sort.Direction.DESC, "quantity"))
        .limit(50);

Query firstByKey = new Query(Criteria.where("customerId").is(1))
        .with(Sort.by(Sort.Direction.ASC, "orderId"))
        .limit(1);

// deterministic "last" element via skip
long count = mongoTemplate.count(base, OrderLine.class);
Query last = new Query()
        .with(Sort.by(Sort.Direction.ASC, "orderLineId"))
        .skip(count - 1)
        .limit(1);

// page-based
Query paged = new Query().with(PageRequest.of(0, 20, Sort.by("orderId")));
```

> Note: `new Query().with(sort)` mutates and returns the same object. When you need an
> independent variant, build a fresh `Query` rather than reusing one you've already
> mutated.

## 5. Field projection and typed projections

Include/exclude document fields:

```java
Query q = new Query();
q.fields().include("orderLineId", "quantity"); // only these (+ _id) come back
// q.fields().exclude("largeBlob");
```

Typed (interface) projection via the fluent API returns only the projected shape:

```java
interface OrderLineView {
    Integer getOrderLineId();
    Integer getQuantity();
}

OrderLineView v = mongoTemplate.query(OrderLine.class)
        .as(OrderLineView.class)
        .matching(new Query().with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1))
        .firstValue();
```

## 6. Counting and existence

```java
long c   = mongoTemplate.count(query, OrderLine.class);
boolean e = mongoTemplate.exists(query, OrderLine.class);

// fluent equivalent
long c2 = mongoTemplate.query(OrderLine.class).matching(query).count();
```

`count(new Query(), X.class)` counts the whole collection. Counting ignores `limit`/`skip`
on the query object, so build a dedicated count query when needed.

## 7. The fluent / typed `template.query(...)` API

`ExecutableFindOperation` reads fluently and is handy for projections and single values:

```java
List<OrderLine> list = mongoTemplate.query(OrderLine.class)
        .matching(query(where("customerId").is(1)))
        .all();

OrderLine first = mongoTemplate.query(OrderLine.class)
        .matching(query(where("customerId").is(1)).with(Sort.by("orderId")))
        .firstValue();

Optional<OrderLine> opt = mongoTemplate.query(OrderLine.class)
        .matching(query(where("orderLineId").is(7)))
        .one();
```

## 8. Dates, decimals, and literals in queries

- Dates: build with `java.time` factories — `LocalDate.of(2014, 12, 20)`,
  `LocalDateTime.of(2014, 12, 20, 0, 0)`, `Instant.parse(...)`. The field type in the
  entity must match what you compare against. **Never** `new Date(2014, 12, 20)`.
- Decimals: compare with `BigDecimal` literals via the string constructor to avoid binary
  float error — `new BigDecimal("15.00")`, not `15.00`.
- Inspecting the generated filter (useful in harnesses):
  `query.getQueryObject()`, `query.getSortObject()`, `query.getFieldsObject()` return the
  `org.bson.Document` Mongo will run.

## 9. Worked examples (mirroring the project harness)

Range filter + deterministic samples:

```java
Query q = new Query(Criteria.where("pickingCompletedWhen")
        .gte(LocalDate.of(2014, 12, 20))
        .lte(LocalDate.of(2014, 12, 31)));
long count = mongoTemplate.count(q, OrderLine.class);
OrderLine firstSample = mongoTemplate.findOne(
        q.with(Sort.by(Sort.Direction.ASC, "orderLineId")).limit(1), OrderLine.class);
```

Equality on a business key against an embedded-bearing root:

```java
Query byCustomer = new Query(Criteria.where("customerId").is(1));
List<Order> orders = mongoTemplate.find(byCustomer, Order.class);
```

Top-N by a field:

```java
Query topByQty = new Query()
        .with(Sort.by(Sort.Direction.DESC, "quantity"))
        .limit(50);
List<OrderLine> top = mongoTemplate.find(topByQty, OrderLine.class);
```

Projection to two fields:

```java
Query proj = new Query();
proj.fields().include("orderLineId", "quantity");
List<OrderLine> slim = mongoTemplate.find(proj, OrderLine.class);
```

For grouping/counting by a field (e.g. "count per taxRate"), that is an aggregation, not a
`Query` — see `aggregation.md`.
