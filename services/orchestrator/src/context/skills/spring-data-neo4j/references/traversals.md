# Traversals & aggregations — relationships in Cypher-DSL (SDN 8.0)

This is the graph-specific counterpart to the document mapper's aggregation pipelines.
It covers matching relationships, the cartesian-product trap, the `collect`/`with`
pattern that lets `Neo4jTemplate` rehydrate an aggregate root with its related nodes, and
grouped aggregations. Read `references/queries.md` first for the base builder.

## Table of contents

1. Matching relationships (`relationshipTo` / `relationshipFrom`)
2. Naming relationships and referring to symbolic names
3. The cartesian-product trap (multiple relationships)
4. The `collect` + `with` aggregate-root pattern
5. Relationship properties (`@RelationshipProperties` / `@TargetNode`)
6. Grouped aggregations (count/group-by via `with`)
7. Wrapping a statement in `CALL { ... }`

---

## 1. Matching relationships

A relationship is created from a `Node` toward/from another `Node`. Direction in the DSL
mirrors the `@Relationship` direction on the entity:

```java
import org.neo4j.cypherdsl.core.Cypher;

var order = Cypher.node("Order").named("o");
var customer = Cypher.node("Customer").named("c");

// (o:Order)-[:CUSTOMERS]->(c:Customer)
var rel = order.relationshipTo(customer, "CUSTOMERS").named("r1");

// (o:Order)<-[:ORDERS]-(ol:OrderLine)
var orderLine = Cypher.node("OrderLine").named("ol");
var relIn = order.relationshipFrom(orderLine, "ORDERS").named("r2");
```

- `relationshipTo(target, "TYPE")` → outgoing (`-[:TYPE]->`), matches a
  `@Relationship(direction = OUTGOING)`.
- `relationshipFrom(source, "TYPE")` → incoming (`<-[:TYPE]-`), matches a
  `@Relationship(direction = INCOMING)`.
- Multiple types: `relationshipTo(target, "A", "B")` matches `:A|B`.

You can match a whole path by passing the relationship to `Cypher.match(...)`:

```java
var stmt = Cypher.match(rel)            // matches (o)-[r1:CUSTOMERS]->(c)
        .where(customer.property("customerId").isEqualTo(Cypher.literalOf(1)))
        .returning(order)
        .build();
```

## 2. Naming relationships and referring to symbolic names

`.named("r1")` gives the relationship a variable so you can return or aggregate it. To
reference a node/relationship in a later `with`/`returning` after it has been introduced,
use its symbolic name:

```java
order.getRequiredSymbolicName();  // the SymbolicName for `o`
Cypher.name("orderLines");         // a bare name you assigned with .as("orderLines")
```

`Cypher.name(...)` refers to an alias you created earlier (e.g. with `.as("orderLines")`
in a `with`/`collect`), not a fresh variable.

## 3. The cartesian-product trap (multiple relationships)

When a query matches several independent relationships off the same root, returning them
naively produces a cartesian product (every combination of related rows), which both
explodes the result and breaks aggregate mapping. The fix, recommended by the Spring Data
Neo4j custom-query guidance, is to `collect(...)` related nodes/relationships into lists
in a `with` step before returning, so each root appears once with its collections.

> See the SDN reference on custom queries:
> https://docs.spring.io/spring-data/neo4j/reference/appendix/custom-queries.html

## 4. The `collect` + `with` aggregate-root pattern

This is the canonical shape for "load an `Order` with its `OrderLine`s, its `Customer`,
and the customer's transactions" without a cartesian blow-up. Collect each related
node (and its relationship) into a named list, carrying the root through each `with`:

```java
import org.neo4j.cypherdsl.core.Cypher;

var order = Cypher.node("Order").named("o");
var customer = Cypher.node("Customer").named("c");
var orderLine = Cypher.node("OrderLine").named("ol");
var transaction = Cypher.node("CustomerTransaction").named("ct");

var rel1 = order.relationshipTo(customer, "CUSTOMERS").named("r1");
var rel2 = order.relationshipFrom(orderLine, "ORDERS").named("r2");
var rel3 = customer.relationshipFrom(transaction, "CUSTOMERS").named("r3");

var orderLines = Cypher.name("orderLines");
var rel2List = Cypher.name("rel2List");
var customerTransactions = Cypher.name("customerTransactions");
var rel3List = Cypher.name("rel3List");

var partial = Cypher.match(rel2, rel1, rel3)
        .where(customer.property("customerId").isEqualTo(Cypher.literalOf(1)))
        // fold OrderLines (and their rels) into lists, keep the rest single
        .with(order, Cypher.collect(rel2).as(rel2List), Cypher.collect(orderLine).as(orderLines),
              rel1, customer, rel3, transaction)
        // fold the customer's transactions into lists
        .with(order, rel2List, orderLines, rel1, customer,
              Cypher.collect(rel3).as(rel3List), Cypher.collect(transaction).as(customerTransactions));

var stmt = partial.returning(
        order.getRequiredSymbolicName(), rel2List, orderLines,
        rel1.getRequiredSymbolicName(), customer.getRequiredSymbolicName(),
        rel3List, customerTransactions).build();
```

Notes:

- `Cypher.collect(x).as(name)` aggregates `x` into a list bound to `name`.
- Everything you want to keep past a `with` must be **listed in that `with`** — anything
  omitted is dropped from scope (this is plain Cypher semantics).
- Return nodes via their symbolic name (`getRequiredSymbolicName()`) and the collected
  lists via the `Cypher.name(...)` you assigned, so `Neo4jTemplate` can rehydrate the
  `Order` aggregate with its populated relationship fields.

## 5. Relationship properties (`@RelationshipProperties` / `@TargetNode`)

When the relationship itself carries data (an association/junction table with extra
columns), model it as a `@RelationshipProperties` class. The owning entity holds a list of
these instead of a list of the target node directly.

```java
import java.util.List;

import org.springframework.data.neo4j.core.schema.GeneratedValue;
import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;
import org.springframework.data.neo4j.core.schema.Property;
import org.springframework.data.neo4j.core.schema.Relationship;
import org.springframework.data.neo4j.core.schema.RelationshipId;
import org.springframework.data.neo4j.core.schema.RelationshipProperties;
import org.springframework.data.neo4j.core.schema.TargetNode;

@Node("Order")
class Order {

    @Id @GeneratedValue
    private String id;

    @Relationship(type = "CONTAINS", direction = Relationship.Direction.OUTGOING)
    private List<LineItem> lineItems;   // relationship-with-properties, not List<Product>

    public Order() {
    }
    // getters and setters ...
}

@RelationshipProperties
class LineItem {

    @RelationshipId
    private String id;

    @Property("quantity")
    private Integer quantity;

    @TargetNode
    private Product product;            // the node at the other end of CONTAINS

    public LineItem() {
    }
    // getters and setters ...
}
```

- `@RelationshipProperties` marks the association class.
- `@RelationshipId` is the generated id of the relationship (analogous to `@Id` on a node).
- `@TargetNode` is the entity at the far end — required exactly once.
- The owning side declares `@Relationship` over a `List<LineItem>` (the properties class),
  not over the target node type.

Use this only when the source model has a junction/association table with its own columns;
a plain FK with no extra data is just a `@Relationship` to the target `@Node` (see
`schema-mapping.md` §5).

## 6. Grouped aggregations (count/group-by via `with`)

Cypher has no `GROUP BY`; grouping is implicit in `with`/`return` — the non-aggregated
keys become the grouping key and the aggregate applies per group. "Count of OrderLines per
taxRate":

```java
import org.neo4j.cypherdsl.core.Cypher;
import org.neo4j.cypherdsl.core.SortItem.Direction;

var ol = Cypher.node("OrderLine").named("ol");
var stmt = Cypher.match(ol)
        .with(ol.property("taxRate").as("taxRate"), Cypher.count(ol).as("count"))
        .returning(Cypher.name("taxRate"), Cypher.name("count"))
        .orderBy(Cypher.sort(Cypher.name("count"), Direction.DESC))
        .build();
```

`taxRate` is the implicit grouping key; `Cypher.count(ol)` counts per distinct `taxRate`.
Because the result is scalar rows (not nodes), execute it with `Neo4jClient` and read the
`Map` rows (see `queries.md` §7), narrowing `Long`/`Double` via `Number`.

## 7. Wrapping a statement in `CALL { ... }`

To post-process an existing statement (e.g. order/limit the output of a grouped query),
wrap it as a subquery with `Cypher.call(...)`:

```java
var inner = stmt;  // a built Statement from §6
var wrapped = Cypher.call(inner)
        .returning(Cypher.asterisk())
        .orderBy(Cypher.sort(Cypher.name("taxRate"), Direction.ASC))
        .limit(1)
        .build();
```

`Cypher.call(Statement)` runs the inner statement and lets you add an outer
`RETURN *`/`ORDER BY`/`LIMIT`. This is how the project harness derives a single
first/last sample from a grouped aggregate without rebuilding it.
