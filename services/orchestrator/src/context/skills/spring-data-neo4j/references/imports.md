# Canonical imports — Spring Data Neo4j 8.0 / Cypher-DSL / Spring Boot 4 / Jackson 3

This is the source of truth for imports. If a class is not here, look it up before using
it — do not guess the package. Every entry below is valid for Spring Data Neo4j 8.0.x
(Spring Boot 4.0.x) with the Cypher-DSL that SDN bundles, on Java 25.

Two packages dominate and are easy to confuse:

- `org.springframework.data.neo4j.core.schema.*` — **mapping annotations** (`@Node`,
  `@Id`, `@GeneratedValue`, `@Property`, `@Relationship`, `@RelationshipProperties`,
  `@TargetNode`).
- `org.neo4j.cypherdsl.core.*` — **query building** (`Cypher`, `Node`, `Relationship`,
  `Statement`, `SortItem.Direction`, `StatementBuilder.*`).

`Node` and `Relationship` exist in *both* worlds: SDN's annotations
(`org.springframework.data.neo4j.core.schema.Node`/`Relationship`) and the Cypher-DSL's
query types (`org.neo4j.cypherdsl.core.Node`/`Relationship`). Import the SDN annotation
ones by name to avoid the wildcard clash (see note in §1).

## Table of contents

1. Mapping annotations (`@Node`, `@Property`, `@Relationship`, …)
2. Identity (`@Id` / `@GeneratedValue`) — Neo4j-specific, not `data.annotation`
3. Relationship properties (`@RelationshipProperties`, `@TargetNode`, `@RelationshipId`)
4. Template & client — `org.springframework.data.neo4j.core`
5. Manual bootstrap (standalone `Neo4jTemplate`, no Spring context)
6. Cypher-DSL — `org.neo4j.cypherdsl.core` (query building)
7. Cypher-DSL nested types — `SortItem`, `StatementBuilder`
8. Neo4j Java driver — `org.neo4j.driver`
9. Jackson 3 (serialization for harnesses)
10. Renamed / removed — do NOT use the left column

---

## 1. Mapping annotations — `org.springframework.data.neo4j.core.schema`

```java
import org.springframework.data.neo4j.core.schema.Node;         // class -> node label
import org.springframework.data.neo4j.core.schema.Property;      // field -> node property key
import org.springframework.data.neo4j.core.schema.Relationship;  // field -> typed relationship
import org.springframework.data.neo4j.core.schema.CompositeProperty; // map -> several prefixed properties
import org.springframework.data.neo4j.core.schema.DynamicLabels;     // Collection<String> of extra labels
```

> **Wildcard-clash note.** `org.springframework.data.neo4j.core.schema.Node`,
> `...schema.Property`, and `...schema.Relationship` collide with
> `org.neo4j.cypherdsl.core.Node`/`Relationship` and `java.lang.reflect`/bean `Property`
> types when both packages are wildcarded. Always import these three by name even if you
> wildcard the rest of `core.schema`. The project snippets do exactly this:
> `import org.springframework.data.neo4j.core.schema.*;` followed by the three explicit
> `import ...schema.Node;`, `...schema.Property;`, `...schema.Relationship;` lines.

`@Relationship.Direction` is a nested enum used inline as
`Relationship.Direction.OUTGOING` / `INCOMING` — no separate import needed once
`Relationship` is imported.

## 2. Identity & generation — `org.springframework.data.neo4j.core.schema`

These are **NOT** in `org.springframework.data.annotation` (that's the MongoDB/JPA `@Id`).
This is the most common Neo4j import mistake when coming from another mapper.

```java
import org.springframework.data.neo4j.core.schema.Id;             // marks the identifier property
import org.springframework.data.neo4j.core.schema.GeneratedValue; // store generates the id
```

Idiomatic identity for SDN 8 / Neo4j 5:

```java
@Id @GeneratedValue
private String id;   // internally generated element id
```

Use a generated `Long` only for legacy databases that still rely on the deprecated
internal numeric id. For a business/natural key, use
`@Id @GeneratedValue(GeneratedValue.UUIDGenerator.class)` on a `String`, or assign your
own `@Id` without `@GeneratedValue`.

## 3. Relationship properties — `org.springframework.data.neo4j.core.schema`

For relationships that carry their own properties (an association class):

```java
import org.springframework.data.neo4j.core.schema.RelationshipProperties; // class holds rel properties
import org.springframework.data.neo4j.core.schema.TargetNode;             // the node at the other end
import org.springframework.data.neo4j.core.schema.RelationshipId;         // generated id of the relationship
```

See `references/traversals.md` §5 for the full pattern.

## 4. Template & client — `org.springframework.data.neo4j.core`

```java
import org.springframework.data.neo4j.core.Neo4jTemplate;            // primary mapped entry point
import org.springframework.data.neo4j.core.Neo4jOperations;          // interface Neo4jTemplate implements
import org.springframework.data.neo4j.core.Neo4jClient;              // low-level: run Cypher, map rows to maps/types
import org.springframework.data.neo4j.core.FluentFindOperation;      // template.find(Type).as(View).matching(stmt)...
import org.springframework.data.neo4j.core.mapping.Neo4jMappingContext; // entity metadata for manual bootstrap
import org.springframework.data.neo4j.core.transaction.Neo4jTransactionManager; // tx manager for manual bootstrap
```

## 5. Manual bootstrap (standalone `Neo4jTemplate`)

Use this when wiring a `Neo4jTemplate` by hand (validation/translation harnesses) rather
than relying on Spring Boot autoconfiguration. This exact wiring is what the project
snippets use:

```java
import java.util.Set;

import org.neo4j.driver.Driver;
import org.springframework.data.neo4j.core.Neo4jClient;
import org.springframework.data.neo4j.core.Neo4jTemplate;
import org.springframework.data.neo4j.core.mapping.Neo4jMappingContext;
import org.springframework.data.neo4j.core.transaction.Neo4jTransactionManager;

final class Neo4jTemplateFactory {
    private Neo4jTemplateFactory() {
    }

    static Neo4jTemplate create(Driver driver) {
        Neo4jClient client = Neo4jClient.create(driver);
        var mappingContext = new Neo4jMappingContext();
        // No setInitialEntitySet: @Node classes are registered lazily on first use.
        mappingContext.afterPropertiesSet();

        Neo4jTransactionManager transactionManager = new Neo4jTransactionManager(driver);
        return new Neo4jTemplate(client, mappingContext, transactionManager);
    }
}
```

## 6. Cypher-DSL — `org.neo4j.cypherdsl.core` (query building)

```java
import org.neo4j.cypherdsl.core.Cypher;     // the facade: node, match, count, collect, sort, parameter, literalOf, name, call, asterisk, property
import org.neo4j.cypherdsl.core.Node;        // a node pattern (Cypher.node(...) returns this) — DSL type, not the @Node annotation
import org.neo4j.cypherdsl.core.Relationship;// a relationship pattern (node.relationshipTo(...)) — DSL type
import org.neo4j.cypherdsl.core.Statement;   // the built query (Cypher.match(...).returning(...).build())
import org.neo4j.cypherdsl.core.ResultStatement;       // a Statement that returns rows
import org.neo4j.cypherdsl.core.SymbolicName;           // Cypher.name("alias")
import org.neo4j.cypherdsl.core.Property;               // node.property("x") — DSL property expression
import org.neo4j.cypherdsl.core.Condition;              // a WHERE condition
import org.neo4j.cypherdsl.core.Expression;             // a returnable/orderable expression
import org.neo4j.cypherdsl.core.SortItem;               // Cypher.sort(...) returns this
```

The most common static entry points on `Cypher` (no import beyond `Cypher` needed):
`Cypher.node`, `Cypher.match`, `Cypher.parameter`, `Cypher.literalOf`, `Cypher.name`,
`Cypher.property`, `Cypher.count`, `Cypher.collect`, `Cypher.sort`, `Cypher.asterisk`,
`Cypher.call`.

A wildcard `import org.neo4j.cypherdsl.core.*;` is acceptable in harness bodies (the
project snippets use it), but it pulls in `Node`/`Relationship`/`Property` which is exactly
why the SDN `@Node`/`@Relationship`/`@Property` annotations must be imported by name.

## 7. Cypher-DSL nested types — `SortItem`, `StatementBuilder`

These live in nested packages and are a frequent "cannot find symbol" cause:

```java
import org.neo4j.cypherdsl.core.SortItem.Direction;                  // Direction.ASC / Direction.DESC
import org.neo4j.cypherdsl.core.StatementBuilder.OngoingReadingAndReturn; // the type after .returning(...), before terminal ops
import org.neo4j.cypherdsl.core.StatementBuilder.BuildableStatement;  // anything with .build()
```

Wildcard equivalents the snippets use: `import org.neo4j.cypherdsl.core.SortItem.*;` and
`import org.neo4j.cypherdsl.core.StatementBuilder.*;`.

`Direction` is `SortItem.Direction` — **not** `org.springframework.data.domain.Sort.Direction`
(that's the Spring Data sort enum used by MongoDB/JPA). For Cypher-DSL ordering always use
`SortItem.Direction`.

## 8. Neo4j Java driver — `org.neo4j.driver`

Only needed in harnesses that open a connection or use `Neo4jClient` directly:

```java
import org.neo4j.driver.Driver;
import org.neo4j.driver.GraphDatabase; // GraphDatabase.driver(uri, authToken)
import org.neo4j.driver.AuthTokens;    // AuthTokens.basic(user, pass)
```

## 9. Jackson 3 (only when a harness serializes results to JSON)

Jackson 3 moved **databind and core** to the `tools.jackson` namespace. Annotations did
**not** move — they remain under `com.fasterxml.jackson.annotation`.

```java
// databind / core — tools.jackson.*
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.databind.SerializationFeature;
import tools.jackson.databind.MapperFeature;
import tools.jackson.databind.module.SimpleModule;
import tools.jackson.databind.ser.std.StdSerializer;
import tools.jackson.databind.SerializationContext;
import tools.jackson.core.JsonGenerator;
import tools.jackson.core.StreamWriteFeature;
import tools.jackson.databind.cfg.DateTimeFeature;

// annotations — still com.fasterxml.jackson.annotation
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonInclude.Include;
```

## 10. Renamed / removed — do NOT use the left column

| Wrong (old / hallucinated) | Correct (SDN 8.0) |
|---|---|
| `org.springframework.data.annotation.Id` (Mongo/JPA `@Id`) | `org.springframework.data.neo4j.core.schema.Id` |
| `org.neo4j.ogm.annotation.NodeEntity` | `org.springframework.data.neo4j.core.schema.Node` |
| `org.neo4j.ogm.annotation.GraphId` | `org.springframework.data.neo4j.core.schema.Id` + `GeneratedValue` |
| `org.neo4j.ogm.annotation.Relationship` | `org.springframework.data.neo4j.core.schema.Relationship` |
| `org.neo4j.ogm.session.Session` / `SessionFactory` | `org.springframework.data.neo4j.core.Neo4jTemplate` / `Neo4jClient` |
| `org.neo4j.cypherdsl.core.Functions.count(...)` | `org.neo4j.cypherdsl.core.Cypher.count(...)` |
| `org.neo4j.cypherdsl.core.Functions.collect(...)` | `org.neo4j.cypherdsl.core.Cypher.collect(...)` |
| `Functions.<anything>` — the `Functions` class NO LONGER EXISTS in this Cypher-DSL | the same-named static on `Cypher` (e.g. `Functions.call("apoc.x", …)` → `Cypher.call("apoc.x").withArgs(…).asFunction()`) |
| `org.springframework.data.domain.Sort.Direction` (for Cypher-DSL) | `org.neo4j.cypherdsl.core.SortItem.Direction` |
| `java.math.BigDecimal` for a `@Property` | `Double` (Neo4j has no decimal type) |
| `java.util.Date` for date properties | `java.time.LocalDate` / `LocalDateTime` / `ZonedDateTime` |
| `new Date(2014, 12, 20)` | `LocalDate.of(2014, 12, 20)` |
| `java.time.Instant` as a node property | `ZonedDateTime` / `OffsetDateTime` (Neo4j `DATETIME`) |
| `com.fasterxml.jackson.databind.ObjectMapper` | `tools.jackson.databind.json.JsonMapper` (Jackson 3) |
| Raw Cypher `String` + `template.findAll(String, ...)` | Cypher-DSL `Statement` + `template.findAll(Statement, Type.class)` |
