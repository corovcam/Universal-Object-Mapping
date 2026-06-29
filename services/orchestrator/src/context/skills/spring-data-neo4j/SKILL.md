---
name: spring-data-neo4j
description: >-
  Expert guidance for writing Java Spring Data Neo4j 8.0 code (Spring Boot 4.x, Java 25,
  Cypher-DSL, Jackson 3). Use whenever generating or reviewing Spring Data Neo4j node
  mapping classes (@Node, @Id/@GeneratedValue, @Property, @Relationship,
  @RelationshipProperties/@TargetNode), Neo4jTemplate or Neo4jClient reads, or queries
  built with the Cypher-DSL Statement builder (Cypher.match/node/relationshipTo/returning)
  — including translating entities or queries from EF Core, NHibernate, Dapper, Spring Data
  MongoDB, or any ORM/ODM into Spring Data Neo4j. Trigger even when the user only says
  "Neo4j", "Neo4jTemplate", "Cypher-DSL", "@Node", "Cypher query", "graph entity", or
  "convert an entity to a graph node" without naming the version, and when fixing
  import/compile errors in Spring Data Neo4j code. Its purpose is correct, non-hallucinated
  imports and APIs for the 8.0 generation. Do NOT use for: Spring Data MongoDB
  (@Document/Criteria), Spring Data JPA/Hibernate on relational DBs, the raw Neo4j Java
  driver used without SDN mapping, Cypher run as hand-written strings instead of the DSL,
  Neo4j server/Aura admin/ops, or non-persistence layers like REST controllers.
---

# Spring Data Neo4j 8.0 Expert

This skill makes you a reliable engineer for the **8.0 generation** of Spring Data Neo4j
(SDN). The single most important thing it buys you is **correct imports and correct API
surface** — the APIs that actually compile against Spring Boot 4.x / Spring Data Neo4j
8.0 on Java 25, using the Cypher-DSL that SDN bundles — not the half-remembered APIs from
SDN 5.x/6.x tutorials or the old OGM. When you generate code that will be compiled and
executed, a single hallucinated package, a renamed-since-6.x class, or a `Functions.count`
that became `Cypher.count` fails the whole build, so precision here matters more than
breadth.

Two things make Neo4j different from a document/relational mapper, and they cause most of
the mistakes:

1. **Queries are built objects, not strings.** You compose an `org.neo4j.cypherdsl.core`
   `Statement` with the fluent `Cypher.match(...).where(...).returning(...).build()`
   builder, then hand it to `Neo4jTemplate`. Raw Cypher string concatenation is wrong for
   this project.
2. **The graph type system is narrow.** Neo4j stores numbers as `Long` or `Double` only —
   **there is no decimal type and the driver rejects `BigDecimal`.** Money/decimal columns
   become `Double`. This is the opposite of the MongoDB mapper, where decimals become
   `BigDecimal`/Decimal128. See the type table in `references/schema-mapping.md`.

If you are unsure which package a class lives in, **stop and consult
`references/imports.md`** — it is the canonical import list. Do not guess an import.
Guessing is the number-one failure mode for this library, and Cypher-DSL in particular
has many types that live in non-obvious nested packages (`SortItem.Direction`,
`StatementBuilder.OngoingReadingAndReturn`).

## Target stack (assume this unless told otherwise)

| Component | Version | Why it matters |
|---|---|---|
| Spring Boot | 4.0.x (`spring-boot-starter-data-neo4j`) | Pulls Spring Data Neo4j 8.0 + Cypher-DSL transitively |
| Spring Data Neo4j | 8.0.x | The mapping annotations + `Neo4jTemplate`/`Neo4jClient` APIs below |
| Cypher-DSL | bundled by SDN 8.0 (2024+ line) | `Cypher.*` facade: `node`, `match`, `count`, `collect`, `sort` |
| Java | 25 | Records, `var`, text blocks, pattern matching all available |
| Neo4j Java Driver | 5.x (`org.neo4j.driver.*`) | `GraphDatabase.driver`, `AuthTokens`, `Driver` |
| Jackson | 3.x | **Databind moved to `tools.jackson.*`**; annotations stay at `com.fasterxml.jackson.annotation.*` |

## How to use this skill

1. Decide what you are producing: **schema mapping classes**, **queries**, or **both**.
2. Read the matching reference file(s) before writing code:
   - `references/schema-mapping.md` — `@Node` classes, the `@Id @GeneratedValue` rule,
     `@Property` field mapping, the Java↔Neo4j type table (incl. the no-`BigDecimal`
     rule), and the manual `Neo4jTemplate` bootstrap used by harnesses.
   - `references/queries.md` — building Cypher-DSL `Statement`s (match, where, returning,
     orderBy/sort, limit, projections, parameters/literals) and executing them with
     `Neo4jTemplate` and `Neo4jClient`.
   - `references/traversals.md` — relationships in queries (`relationshipTo`/
     `relationshipFrom`), avoiding cartesian products, the `collect`/`with` aggregate-root
     pattern, and aggregations (`count`, group-by via `with`).
   - `references/imports.md` — every import you are allowed to use, plus the
     renamed/removed traps.
3. Write the code following the rules below.
4. If the code must run (validation/translation harness), re-check every import against
   `references/imports.md` and the type-mapping table in `references/schema-mapping.md`.

## Non-negotiable rules

These are the rules that most often separate code that compiles and runs from code that
does not.

**Imports come from the canonical list.** Mapping annotations live under
`org.springframework.data.neo4j.core.schema` — including `@Id` and `@GeneratedValue`,
which (unlike Spring Data MongoDB, where `@Id` is in `org.springframework.data.annotation`)
are Neo4j-specific here. The template/client APIs are under
`org.springframework.data.neo4j.core`. Everything for building queries lives under
`org.neo4j.cypherdsl.core` (with key types in the nested `SortItem` and `StatementBuilder`
packages). See `references/imports.md`.

**`@Node`, `@Property`, and `@Relationship` need care with wildcards.**
`org.springframework.data.neo4j.core.schema.Node` can be shadowed by
`org.neo4j.cypherdsl.core.Node` (the DSL's node type) when both packages are wildcarded.
Import `org.springframework.data.neo4j.core.schema.Node`, `...schema.Property`, and
`...schema.Relationship` by name even when you wildcard the rest, exactly as the project
snippets do.

**The `@Id` is a generated `String`, not the business key.** Use
`@Id @GeneratedValue private String id;`. Neo4j's identity is its internally generated
element id, not the source system's integer key. Map the business key (e.g. `customerId`)
as its own `@Property`. Never put `@Id` on an `Integer` primary key carried over from a
relational entity.

**There is no `BigDecimal` in Neo4j.** The driver supports only `Long`/`Double` for
numbers. Money and decimal columns map to `Double`. Writing `BigDecimal` into a `@Property`
throws at runtime. (If exact precision were truly required you would store a `String`, but
for this project's numeric comparisons `Double` is correct.) This is the single most
common cross-mapper mistake when translating from MongoDB or a relational source.

**Build queries with the Cypher-DSL, never string concatenation.** Compose a `Statement`
via `Cypher.match(...)....build()` and pass it to `Neo4jTemplate`. The parameters travel
with the statement — read them back with `statement.getCatalog().getParameters()` and pass
that map to `template.findOne(stmt, params, Type.class)`.

**Use `java.time`, never legacy date constructors.** Prefer `LocalDate` (Neo4j `DATE`),
`LocalDateTime` (`LOCAL_DATETIME`), and `ZonedDateTime` (`DATETIME`). Build with
`LocalDate.of(2014, 12, 20)` / `ZonedDateTime.of(...)`. **Never** `new Date(2014, 12, 20)`.
Note Neo4j has no plain `Instant` property type — use `ZonedDateTime`/`OffsetDateTime` for
zoned timestamps.

**No comments or placeholders in code that will be executed.** Generated translation/
validation code is compiled and run. `// TODO`, `...`, or stub method bodies break it.
Emit complete, runnable code.

**Schema classes avoid the `public` modifier unless required.** Match the project
convention: top-level mapping classes are package-private (`class OrderLine`); only the
entrypoint class carrying `main` is `public`.

**Relationship targets are mapped `@Node` types, not embedded blobs.** A related entity is
a separate node connected by a typed relationship, expressed with `@Relationship(type=...,
direction=...)`. There is no "embed the child object" option as in MongoDB — model the
foreign key as a relationship to another `@Node`. See `references/schema-mapping.md` §5.

## Quick orientation example (the shape to aim for)

A correctly-imported aggregate root plus a Cypher-DSL read executed on `Neo4jTemplate`.
Study the imports — they are the part most likely to be wrong. Note `@Node`/`@Property`/
`@Relationship` imported by name alongside the schema wildcard, and `Direction` coming
from the nested `SortItem` package.

```java
import java.time.ZonedDateTime;
import java.util.List;
import java.util.Map;

import org.neo4j.cypherdsl.core.Cypher;
import org.neo4j.cypherdsl.core.SortItem.Direction;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.schema.GeneratedValue;
import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;
import org.springframework.data.neo4j.core.schema.Property;

@Node("OrderLine")
class OrderLine {

    @Id @GeneratedValue
    private String id;

    @Property("orderLineId")
    private Integer orderLineId;

    @Property("quantity")
    private Integer quantity;

    @Property("unitPrice")
    private Double unitPrice;          // NOT BigDecimal — Neo4j has no decimal type

    @Property("pickingCompletedWhen")
    private ZonedDateTime pickingCompletedWhen;

    public OrderLine() {
    }

    public Integer getOrderLineId() { return orderLineId; }
    public void setOrderLineId(Integer orderLineId) { this.orderLineId = orderLineId; }
    // remaining getters and setters ...
}

class OrderLineQueries {

    private final Neo4jTemplate template;

    OrderLineQueries(Neo4jTemplate template) {
        this.template = template;
    }

    List<OrderLine> topByQuantity() {
        var ol = Cypher.node("OrderLine").named("ol");
        var statement = Cypher.match(ol)
                .returning(ol)
                .orderBy(Cypher.sort(ol.property("quantity"), Direction.DESC))
                .limit(50)
                .build();
        return template.findAll(statement, OrderLine.class);
    }

    OrderLine pickedBetween(ZonedDateTime from, ZonedDateTime to) {
        var ol = Cypher.node("OrderLine").named("ol");
        var statement = Cypher.match(ol)
                .where(ol.property("pickingCompletedWhen").gte(Cypher.parameter("from", from)))
                .and(ol.property("pickingCompletedWhen").lte(Cypher.parameter("to", to)))
                .returning(ol)
                .orderBy(Cypher.sort(ol.property("orderLineId"), Direction.ASC))
                .limit(1)
                .build();
        return template.findOne(statement, statement.getCatalog().getParameters(), OrderLine.class)
                .orElse(null);
    }
}
```

## Common traps (renamed or removed since the SDN 5.x/6.x and OGM era)

These are the API changes that catch out a model trained on older docs. Full list in
`references/imports.md`.

- `Functions.count(...)` / `Functions.collect(...)` → **`Cypher.count(...)` /
  `Cypher.collect(...)`** (the recent Cypher-DSL moved the aggregate factories onto the
  `Cypher` facade).
- The Neo4j-OGM annotations `org.neo4j.ogm.annotation.*` (`@NodeEntity`,
  `@GraphId`, `@Relationship`) → **SDN annotations
  `org.springframework.data.neo4j.core.schema.*`** (`@Node`, `@Id @GeneratedValue`,
  `@Relationship`). SDN 8 is not OGM.
- `@Id` from `org.springframework.data.annotation.Id` (the MongoDB/JPA one) → **
  `org.springframework.data.neo4j.core.schema.Id`** for Neo4j.
- Internal `Long` ids via `@GeneratedValue` are legacy; prefer
  `@Id @GeneratedValue private String id;` (element id) unless told otherwise.
- `SessionFactory`/`Session` (OGM) → **`Neo4jTemplate`/`Neo4jClient`**
  (`org.springframework.data.neo4j.core`).
- Jackson 2 `com.fasterxml.jackson.databind.*` → Jackson 3 **`tools.jackson.databind.*`**.
  Jackson *annotations* (`@JsonIgnoreProperties`, `@JsonInclude`) stay at
  `com.fasterxml.jackson.annotation.*`.
- `BigDecimal` property → **`Double`** (Neo4j has no decimal type; see above).
- `new Date(y, m, d)` → `LocalDate.of(y, m, d)` / `ZonedDateTime.of(...)`.
- Derived-query `Neo4jRepository` interfaces still exist, but this project's pattern is
  **explicit `Neo4jTemplate` + Cypher-DSL `Statement`s**, not repository interfaces. Prefer
  the template unless the user asks for repositories.

## Project context (Universal Object Mapping)

This skill backs the `generate_translation_node` translator. When translating from a
relational ORM (EF Core, NHibernate, Dapper) or a document store (Spring Data MongoDB)
into Spring Data Neo4j:

- A table/collection becomes a `@Node`. A foreign-key relationship becomes a typed
  `@Relationship` to another `@Node` (with a `direction`), not an embedded object.
  `references/schema-mapping.md` §5 and `references/traversals.md` explain how to choose
  direction and model relationship properties.
- Keep query method shape close to the source: one source `Query1()` → one target
  `query1()` returning the same logical result set. Don't invent extra parameters or
  synthetic sort/filter arguments that the source query didn't have.
- Property names in `@Property(...)` and in `node.property("...")` are the **Neo4j node
  property names** (usually camelCase), not the Java field name and not the SQL column.
- In the UOM validation harness, the fixed prelude — the `import`/`package` lines, the
  JSON serializer, `QueryRuntimeSupport`, and the `Neo4jTemplateFactory` — is **injected
  for you**. When writing a `*_validation_body`, start at the `@Node` declarations; do not
  redeclare those helper classes. The import knowledge in this skill is still what lets you
  reference them correctly and write production (non-harness) code.
