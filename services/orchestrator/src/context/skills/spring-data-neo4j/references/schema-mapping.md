# Schema mapping — Spring Data Neo4j 8.0 node classes

How to turn a domain model (or a relational/document entity being migrated) into Spring
Data Neo4j mapping classes that map cleanly and round-trip through `Neo4jTemplate`.

## Table of contents

1. Anatomy of a node entity
2. The `@Id @GeneratedValue` rule (most common mistake)
3. Property mapping and `@Property`
4. Type mapping table (Java ↔ Neo4j) — and the no-`BigDecimal` rule
5. Relationships instead of embedding (the graph mindset)
6. Relationship direction
7. Constructors, access modifiers, getters/setters
8. Standalone `Neo4jTemplate` bootstrap (for harnesses)
9. Validating a mapping

---

## 1. Anatomy of a node entity

A node entity maps to one label and carries `@Node`. Keep top-level mapping classes
package-private (no `public`), matching project convention. Import `@Node`/`@Property`/
`@Relationship` by name (see `imports.md` §1).

```java
import java.time.LocalDate;
import java.util.List;

import org.springframework.data.neo4j.core.schema.GeneratedValue;
import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;
import org.springframework.data.neo4j.core.schema.Property;
import org.springframework.data.neo4j.core.schema.Relationship;

@Node("Customer")
class Customer {

    @Id @GeneratedValue
    private String id;

    @Property("customerId")
    private Integer customerId;

    @Property("customerName")
    private String customerName;

    @Property("accountOpenedDate")
    private LocalDate accountOpenedDate;

    @Property("creditLimit")
    private Double creditLimit;        // money -> Double, never BigDecimal

    @Relationship(type = "CUSTOMERS", direction = Relationship.Direction.INCOMING)
    private List<CustomerTransaction> customerTransactions;

    public Customer() {
    }

    // getters and setters ...
}
```

`@Node("Customer")` pins the node label. Without the value the label defaults to the
class name — usually fine, but set it explicitly when matching an existing graph whose
labels differ from your Java class names. `@Node` also accepts multiple labels:
`@Node({"Customer", "Person"})`.

## 2. The `@Id @GeneratedValue` rule (most common mistake)

Neo4j's identity is its internally generated element id, not a column value.

- Use `@Id @GeneratedValue private String id;`. The store assigns it; you never set it.
- When migrating a relational entity whose key is `int CustomerID`, **do not** put `@Id`
  on `Integer customerId`. Keep a separate generated `@Id private String id;` and map the
  business key as `@Property("customerId") private Integer customerId;`.
- Import `@Id` from `org.springframework.data.neo4j.core.schema.Id` — **not**
  `org.springframework.data.annotation.Id` (that is the MongoDB/JPA one and silently fails
  to register as the Neo4j identifier).

Wrong (collapses the natural key onto the identity, and uses the wrong `@Id`):

```java
import org.springframework.data.annotation.Id; // ❌ wrong package for Neo4j

@Id
private Integer customerId; // ❌ business key is not the node identity
```

Right:

```java
import org.springframework.data.neo4j.core.schema.GeneratedValue;
import org.springframework.data.neo4j.core.schema.Id;

@Id @GeneratedValue
private String id;          // generated element id

@Property("customerId")
private Integer customerId; // business key preserved as its own property
```

If you genuinely need a stable assigned key (e.g. you want the business key to *be* the
id), use `@Id` alone (no `@GeneratedValue`) and set it yourself, or
`@Id @GeneratedValue(GeneratedValue.UUIDGenerator.class) private String id;` for a
generated UUID.

## 3. Property mapping and `@Property`

- A field with no annotation is stored under its Java name.
- Use `@Property("nodeKey")` when the stored property key differs from the Java field name
  (e.g. the existing graph uses a particular casing, or you want to be explicit).
- The string in `@Property(...)` and in `node.property("...")` in queries is the **Neo4j
  node property name** — not the Java field and not the SQL column.
- Import `Property` by name (clashes with the Cypher-DSL `Property` and bean `Property`;
  see `imports.md`).
- A `Map<String, X>` can be spread across prefixed properties with `@CompositeProperty`;
  extra runtime labels can be bound to a `Collection<String>` with `@DynamicLabels`. Use
  these only when the source model calls for them.

## 4. Type mapping table (Java ↔ Neo4j)

Neo4j's property type system is **narrow**: numbers are only `Long` or `Double`, and there
is no decimal type. Choose Java types deliberately when translating from SQL/.NET/Mongo.

| Source intent | Java type | Neo4j type | Notes |
|---|---|---|---|
| identity | `String` (`@Id @GeneratedValue`) | element id | never the business key |
| 32-bit int | `Integer` | Integer (stored as Long) | |
| 64-bit int / bigint | `Long` | Integer (Long) | |
| `decimal` / money | **`Double`** | Float | **No `BigDecimal`** — the driver rejects it; Neo4j has no decimal type |
| `float`/`double` | `Double` | Float | |
| `bit`/`bool` | `Boolean` | Boolean | |
| `date` (no time) | `LocalDate` | Date | build via `LocalDate.of(y, m, d)` |
| `datetime` (no zone) | `LocalDateTime` | LocalDateTime | `LocalDateTime.of(...)` |
| `datetimeoffset` / zoned | `ZonedDateTime` | DateTime | `ZonedDateTime.of(...)`; also `OffsetDateTime` |
| time of day | `LocalTime` / `OffsetTime` | LocalTime / Time | |
| duration | `java.time.Duration` / `Period` | Duration | |
| `nvarchar`/text | `String` | String | |
| `uniqueidentifier`/UUID | `java.util.UUID` | String | stored as string |
| array / collection | `List<T>` of a primitive | List | homogeneous arrays of primitives |
| related entity | another `@Node` via `@Relationship` | relationship | NOT an embedded object — see §5 |

**Never** use `java.math.BigDecimal` for a `@Property`, `java.util.Date`, `new Date(...)`,
or `java.time.Instant` (no Neo4j property type) — see `imports.md` §10. The single most
common cross-mapper bug is carrying a `BigDecimal` over from a MongoDB/relational mapping;
in Neo4j it must be `Double`.

## 5. Relationships instead of embedding (the graph mindset)

In a document store you embed a child object inside its parent. In a graph there is **no
embedding** — a related entity is its own `@Node`, connected by a typed relationship. When
a relational parent/child (one-to-many via FK) becomes Neo4j:

- The child table becomes its own `@Node`.
- The FK becomes a `@Relationship` field on one (or both) sides, with a `type` (the
  relationship name, conventionally UPPER_SNAKE_CASE) and a `direction`.

```java
@Node("Order")
class Order {

    @Id @GeneratedValue
    private String id;

    @Property("orderId")
    private Integer orderId;

    // one Order -> one Customer, traversed outbound
    @Relationship(type = "CUSTOMERS", direction = Relationship.Direction.OUTGOING)
    private Customer customer;

    // one Order -> many OrderLines, modelled as inbound ORDERS edges
    @Relationship(type = "ORDERS", direction = Relationship.Direction.INCOMING)
    private List<OrderLine> orderLines;

    public Order() {
    }
    // getters and setters ...
}
```

A single related entity is a field of that type; a to-many is a `List<T>`. The target
type must itself be an `@Node`. Do not annotate the target with anything document-like —
there is no `@Node` "embedded" variant.

For relationships that carry their own properties (an association/junction table with
extra columns), use a `@RelationshipProperties` class — see `references/traversals.md` §5.

## 6. Relationship direction

`@Relationship(direction = ...)` takes `Relationship.Direction.OUTGOING` (default) or
`Relationship.Direction.INCOMING`. Direction is about how the edge is stored and traversed
in the graph, independent of which side declares the field — two entities can both declare
a field for the same relationship with opposite directions, and SDN links them.

Pick the direction that matches the source graph or the natural reading of the
relationship type. For a migration where you control the graph shape, keep it consistent
with how queries will traverse it (`relationshipTo` ↔ OUTGOING, `relationshipFrom` ↔
INCOMING; see `traversals.md`).

## 7. Constructors, access modifiers, getters/setters

- Provide a no-arg constructor (SDN instantiates via it unless a persistence constructor
  is present). A record or an all-args constructor also works as the persistence creator.
- Keep classes package-private; only the harness/entrypoint class with `main` is `public`.
- Provide getters/setters for mapped fields. If serializing results with Jackson in a
  harness, getters are what Jackson reads.
- Do not put `public` on every field/class reflexively — it diverges from the project
  snippets and is unnecessary.

## 8. Standalone `Neo4jTemplate` bootstrap (for harnesses)

When code must run outside a Spring context (validation/translation harness), build the
`Neo4jTemplate` by hand from a `Driver`. This exact wiring is what the project snippets
use (in the UOM harness it is injected for you — do not redeclare it there):

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
        mappingContext.setInitialEntitySet(Set.of(Order.class, Customer.class, OrderLine.class));
        mappingContext.afterPropertiesSet();

        Neo4jTransactionManager transactionManager = new Neo4jTransactionManager(driver);
        return new Neo4jTemplate(client, mappingContext, transactionManager);
    }
}
```

`setInitialEntitySet(...)` registers every `@Node` class with the mapping context so the
template can map them; `afterPropertiesSet()` finalizes it. List all node classes you
intend to query.

## 9. Validating a mapping

A mapping is correct if a one-node fetch round-trips without a `MappingException`. Build a
trivial MATCH for the label and ask the template to map it:

```java
import java.util.Map;
import org.neo4j.cypherdsl.core.Cypher;

static void validate(Class<?> entityClass, Neo4jTemplate template) {
    var node = Cypher.node(entityClass.getSimpleName());
    template.findOne(Cypher.match(node).returning(node).limit(1).build(), Map.of(), entityClass);
}
```

If the entity has a property whose Java type the driver cannot store (e.g. `BigDecimal`),
or an `@Id`/`@Property` import from the wrong package, this is where it surfaces.
