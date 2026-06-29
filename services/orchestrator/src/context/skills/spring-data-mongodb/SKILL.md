---
name: spring-data-mongodb
description: >-
  Expert guidance for writing Java Spring Data MongoDB 5.0 code (Spring Boot 4.x, Java 25,
  Jackson 3). Use whenever generating or reviewing Spring Data MongoDB document mapping
  classes (@Document, @Field, @Id, @DocumentReference, embedded value objects),
  MongoTemplate queries with the Query/Criteria API, or Aggregation/TypedAggregation
  pipelines — including translating entities or queries from EF Core, NHibernate, Dapper,
  or any ORM into Spring Data MongoDB. Trigger even when the user only says "MongoDB",
  "MongoTemplate", "Criteria", "@Document", "mongo entity/query", or "convert a C# entity
  to a mongo document" without naming the version, and when fixing import/compile errors
  in Spring Data MongoDB code. Its purpose is correct, non-hallucinated imports and APIs
  for the 5.0 generation. Do NOT use for: Spring Data Neo4j (@Node/Cypher), Spring Data
  JPA/Hibernate on relational DBs, raw MongoDB via mongosh/native driver/pymongo, MongoDB
  server or Atlas admin/ops, or non-persistence layers like REST controllers.
---

# Spring Data MongoDB 5.0 Expert

This skill makes you a reliable engineer for the **5.0 generation** of Spring Data
MongoDB. The single most important thing it buys you is **correct imports and correct
API surface** — the APIs that actually compile against Spring Boot 4.x / Spring Data
MongoDB 5.0 on Java 25, not the half-remembered APIs from older tutorials. When you
generate code that will be compiled and executed, a single hallucinated package or a
renamed-since-3.x class fails the whole build, so precision here matters more than
breadth.

## Target stack (assume this unless told otherwise)

| Component | Version | Why it matters |
|---|---|---|
| Spring Boot | 4.0.x (`spring-boot-starter-data-mongodb`) | Pulls Spring Data MongoDB 5.0 transitively |
| Spring Data MongoDB | 5.0.x | The mapping + `MongoTemplate` + aggregation APIs below |
| Java | 25 | Records, `var`, text blocks, pattern matching all available |
| Jackson | 3.x | **Databind moved to `tools.jackson.*`**; annotations stay at `com.fasterxml.jackson.annotation.*` |
| MongoDB Java Driver | 5.x (`com.mongodb.client.*`) | `MongoClients`, `MongoClient` |

If you are unsure which package a class lives in, **stop and consult
`references/imports.md`** — it is the canonical import list. Do not guess an import.
Guessing is the number-one failure mode for this library.

## How to use this skill

1. Decide what you are producing: **schema mapping classes**, **queries**, or **both**.
2. Read the matching reference file(s) before writing code:
   - `references/schema-mapping.md` — `@Document` classes, field/type mapping, embedding vs references, the `@Id`/`_id` rule, manual `MongoTemplate` bootstrap.
   - `references/queries.md` — `MongoTemplate` read operations, the `Query`/`Criteria` API, operators, sorting, paging, field projection, fluent/typed queries.
   - `references/aggregation.md` — `Aggregation`/`TypedAggregation` pipelines (`group`, `project`, `match`, `sort`, `unwind`, `lookup`, counting).
   - `references/imports.md` — every import you are allowed to use, plus the renamed/removed traps.
3. Write the code following the rules below. Prefer explicit imports over wildcards in
   production code so a reviewer can see exactly what resolves.
4. If the code must run (validation/translation harness), re-check every import against
   `references/imports.md` and the type-mapping table in `references/schema-mapping.md`.

## Non-negotiable rules

These are the rules that most often separate code that compiles from code that does not.

**Imports come from the canonical list.** Mapping annotations live under
`org.springframework.data.mongodb.core.mapping`, *except* `@Id`, `@Transient`,
`@ReadOnlyProperty`, and `@PersistenceCreator`, which come from
`org.springframework.data.annotation`. The query API (`Query`, `Criteria`, `Update`)
lives under `org.springframework.data.mongodb.core.query`. `Sort`, `Pageable`, and
`PageRequest` come from `org.springframework.data.domain`. See `references/imports.md`.

**`@Field` needs an explicit import.** `org.springframework.data.mongodb.core.mapping.Field`
collides with `java.lang.reflect.Field` (and any wildcard that pulls the latter in).
Import it by name even when you wildcard the rest of the package, exactly as the project
snippets do.

**The `@Id` is a `String` mapped to `_id`.** Mongo's `_id` is an `ObjectId`/string, not
the source system's integer key. Map the business key (e.g. `customerId`) as its own
`@Field`, and keep `@Id private String id;`. Never map an `int`/`Integer` primary key
straight onto `@Id` when translating from a relational entity.

**Use `java.time` and `BigDecimal`, never legacy date constructors.** Prefer `LocalDate`,
`LocalDateTime`, `Instant`, and `BigDecimal`. Build dates with `LocalDate.of(2014, 12, 20)`.
**Never** write `new Date(2014, 12, 20)` — that constructor is deprecated and interprets
the year as 1900-relative, so it is both wrong and a smell that the code came from an old
model. Money/decimal columns map to `BigDecimal` (stored as `Decimal128`).

**No comments or placeholders in code that will be executed.** Generated translation/
validation code is compiled and run. `// TODO`, `...`, or stub method bodies break it.
Emit complete, runnable code.

**Schema classes avoid the `public` modifier unless required.** Match the project
convention: top-level mapping classes are package-private (`class OrderLine`), only the
entrypoint class carrying `main`/`build` is `public`.

**Embedded objects have no `@Document`.** Only aggregate roots that map to their own
collection get `@Document`. Value objects embedded inside another document (e.g. a
`Customer` embedded in `Order`) are plain classes — annotating them with `@Document` is
wrong and signals they should be a separate collection.

## Quick orientation example (the shape to aim for)

A correctly-imported aggregate root plus a `Query`/`Criteria` read. Study the imports —
they are the part most likely to be wrong.

```java
import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;

import org.springframework.data.annotation.Id;
import org.springframework.data.domain.Sort;
import org.springframework.data.mongodb.core.MongoTemplate;
import org.springframework.data.mongodb.core.mapping.Document;
import org.springframework.data.mongodb.core.mapping.Field;
import org.springframework.data.mongodb.core.query.Criteria;
import org.springframework.data.mongodb.core.query.Query;

@Document(collection = "orderLines")
class OrderLine {

    @Id
    private String id;

    @Field("orderLineId")
    private Integer orderLineId;

    @Field("pickingCompletedWhen")
    private LocalDateTime pickingCompletedWhen;

    private BigDecimal unitPrice;

    OrderLine() {
    }

    // getters and setters ...
}

class OrderLineQueries {

    private final MongoTemplate mongoTemplate;

    OrderLineQueries(MongoTemplate mongoTemplate) {
        this.mongoTemplate = mongoTemplate;
    }

    List<OrderLine> recentlyPicked() {
        LocalDateTime from = LocalDateTime.of(2014, 12, 20, 0, 0);
        LocalDateTime to = LocalDateTime.of(2014, 12, 31, 23, 59, 59);
        Query query = new Query(Criteria.where("pickingCompletedWhen").gte(from).lte(to))
                .with(Sort.by(Sort.Direction.ASC, "orderLineId"));
        return mongoTemplate.find(query, OrderLine.class);
    }
}
```

## Common traps (renamed or removed since the 3.x era)

These are the API changes that catch out a model trained on older docs. Full list in
`references/imports.md`.

- `MongoDbFactory` → **`MongoDatabaseFactory`** (`org.springframework.data.mongodb`).
- `SimpleMongoClientDbFactory` → **`SimpleMongoClientDatabaseFactory`**
  (`org.springframework.data.mongodb.core`).
- Jackson 2 `com.fasterxml.jackson.databind.*` → Jackson 3 **`tools.jackson.databind.*`**.
  Jackson *annotations* (`@JsonIgnoreProperties`, `@JsonInclude`) stay at
  `com.fasterxml.jackson.annotation.*`.
- `new Date(y, m, d)` → `LocalDate.of(y, m, d)` / `LocalDateTime.of(...)`.
- Repository `MongoRepository` still exists, but this project's pattern is **explicit
  `MongoTemplate` + `Query`/`Criteria`**, not derived-query repository interfaces. Prefer
  `MongoTemplate` unless the user asks for repositories.

## Project context (Universal Object Mapping)

This skill backs the `generate_translation_node` translator. When translating from a
relational ORM (EF Core, NHibernate, Dapper) into Spring Data MongoDB:

- A table usually becomes a `@Document` collection; a foreign-key child can become either
  an **embedded** array (denormalized into the parent) or a **`@DocumentReference`**
  (kept as a separate collection). `references/schema-mapping.md` explains when to pick
  which and how to express both.
- Keep query method shape close to the source: one source `Query1()` → one target
  `query1()` returning the same logical result set. Don't invent extra parameters.
- Field names in `@Field(...)` and in `Criteria.where(...)` are the **MongoDB document
  field names** (usually camelCase), not the Java property name and not the SQL column.
